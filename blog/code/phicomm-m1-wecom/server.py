#!/usr/bin/env python3
"""Minimal Phicomm M1 stock-firmware receiver and WeCom notifier.

Configuration is read from environment variables so secrets never need to live
in the source tree. This is a personal interoperability project, not an
official Phicomm service.
"""

import asyncio
import json
import logging
import math
import os
import ssl
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


DATA_DIR = Path(os.getenv("DATA_DIR", "/var/lib/m1-aircat"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
MAC = bytes.fromhex(os.environ["M1_MAC"].replace(":", ""))
WEBHOOK_URL = os.environ["WECOM_WEBHOOK_URL"]
CERT_FILE = os.getenv("TLS_CERT", "/opt/m1-aircat/cloud.crt")
KEY_FILE = os.getenv("TLS_KEY", "/opt/m1-aircat/cloud.key")
END = b"\xff#END#"
BEIJING = ZoneInfo("Asia/Shanghai")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

RULES = {
    "pm25": (50.0, 40.0, "PM2.5", "µg/m³"),
    "hcho": (0.08, 0.06, "甲醛", "mg/m³"),
}
STATE_FILE = DATA_DIR / "state.json"

try:
    saved = json.loads(STATE_FILE.read_text())
except (OSError, ValueError):
    saved = {}

states = {
    key: {
        "active": saved.get(key, {}).get("active", False),
        "last_sent": saved.get(key, {}).get("last_sent", 0),
        "last_attempt": 0,
        "high": None,
        "low": None,
        "last_sample": 0,
    }
    for key in RULES
}


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False))
    temp.replace(path)


def send_wecom(text):
    body = json.dumps(
        {"msgtype": "text", "text": {"content": text}}, ensure_ascii=False
    ).encode()
    request = Request(
        WEBHOOK_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urlopen(request, timeout=10) as response:
        result = json.load(response)
    if result.get("errcode") != 0:
        raise RuntimeError(f"WeCom error: {result.get('errcode')}")


def report_text(latest, now, title):
    stamp = now.strftime("%Y-%m-%d %H:%M")
    if latest is None:
        return (
            f"{title}\n━━━━━━━━━━━━\n🕰️ 北京时间：{stamp}\n"
            "📡 设备暂未上报，暂无当前读数。\n"
            "请检查 M1 电源、Wi-Fi 和 DNS 网关。"
        )

    age = now.timestamp() - datetime.fromisoformat(latest["time"]).timestamp()
    if age > 120:
        return (
            f"{title}\n━━━━━━━━━━━━\n🕰️ 北京时间：{stamp}\n"
            "📡 设备数据已过期，暂不展示为当前读数。\n"
            f"🗓️ 最后采样：{latest['time']}"
        )

    pm25, hcho = latest["pm25"], latest["hcho"]
    quality = (
        "🌿 两项污染物读数均未触发预警"
        if pm25 <= 50 and hcho <= 0.08
        else "⚠️ 有污染物读数超过预警阈值"
    )
    sampled_at = datetime.fromisoformat(latest["time"])
    return (
        f"{title}\n━━━━━━━━━━━━\n🕰️ 北京时间：{stamp}\n\n"
        f"🌫️ PM2.5｜{pm25:g} µg/m³ {'⚠️' if pm25 > 50 else '✅'}\n"
        f"🧪 甲醛｜{hcho:.3f} mg/m³ {'⚠️' if hcho > 0.08 else '✅'}\n"
        f"🌡️ 温度｜{latest['temperature']:.1f} ℃\n"
        f"💧 湿度｜{latest['humidity']:.1f}%\n\n"
        f"{quality}\n━━━━━━━━━━━━\n"
        f"📍 采样时间：{sampled_at:%H:%M:%S}\n"
        "M1 实时读数 · 仅供家庭预警参考"
    )


async def process_sample(data, now=None):
    now = time.time() if now is None else now
    values = {
        "pm25": float(data["value"]),
        "hcho": float(data["hcho"]) / 1000,
        "temperature": float(data["temperature"]),
        "humidity": float(data["humidity"]),
    }
    if not all(math.isfinite(value) for value in values.values()):
        return
    if not (
        0 <= values["pm25"] <= 10000
        and 0 <= values["hcho"] <= 10
        and -50 <= values["temperature"] <= 100
        and 0 <= values["humidity"] <= 100
    ):
        return

    latest = dict(values, time=datetime.fromtimestamp(now, BEIJING).isoformat())
    atomic_json(DATA_DIR / "latest.json", latest)

    for key, (high, low, label, unit) in RULES.items():
        state, value = states[key], values[key]
        if now - state["last_sample"] > 30:
            state["high"] = state["low"] = None
        state["last_sample"] = now
        state["high"] = (
            state["high"] if state["high"] is not None else now
        ) if value > high else None
        state["low"] = (
            state["low"] if state["low"] is not None else now
        ) if value < low else None

        alert = (
            state["high"] is not None
            and now - state["high"] >= 60
            and (not state["active"] or now - state["last_sent"] >= 1800)
        )
        recover = (
            state["active"]
            and state["low"] is not None
            and now - state["low"] >= 300
        )
        if not (alert or recover) or now - state["last_attempt"] < 60:
            continue

        state["last_attempt"] = now
        title = "🚨 家庭空气 · 异常提醒" if alert else "🌿 家庭空气 · 恢复提醒"
        text = report_text(latest, datetime.fromtimestamp(now, BEIJING), title)
        try:
            await asyncio.to_thread(send_wecom, text)
        except Exception as error:
            logging.warning("Webhook delivery failed: %s", type(error).__name__)
            continue

        state["active"] = bool(alert)
        state["last_sent"] = now
        atomic_json(STATE_FILE, states)
        logging.info("Notification sent: %s %s", key, "alert" if alert else "recovered")


sample_lock = asyncio.Lock()


async def handle_aircat(reader, writer):
    """Receive stock-firmware TCP frames on port 9000."""
    try:
        buffer = b""
        while True:
            chunk = await asyncio.wait_for(reader.read(4096), 90)
            if not chunk:
                break
            buffer += chunk
            if len(buffer) > 16384:
                break

            while END in buffer:
                frame, buffer = buffer.split(END, 1)
                if len(frame) < 28 or frame[0] != 0xAA or frame[17:23] != MAC:
                    return
                if frame[25:27] != b"\x00\x00" or len(frame[28:]) + 3 != frame[24]:
                    return

                heartbeat = b'{"type":5,"status":1}'
                writer.write(
                    frame[:24]
                    + bytes([34 + len(heartbeat)])
                    + b"\x00\x00\x02"
                    + heartbeat
                    + END
                )
                await writer.drain()

                if frame[27] == 4 and frame[28:]:
                    data = json.loads(frame[28:])
                    required = ("value", "hcho", "temperature", "humidity")
                    if all(key in data for key in required):
                        async with sample_lock:
                            await process_sample(data)
    except (OSError, ValueError, KeyError, asyncio.TimeoutError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def handle_fake_cloud(reader, writer):
    """Acknowledge activation without advertising firmware updates."""
    try:
        header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
        request_line = header.split(b"\r\n", 1)[0]
        if b" /device/active?" in request_line:
            body = b'{"code":0,"message":"success"}'
        else:
            body = b'{"code":0,"data":{}}'
        writer.write(
            b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nContent-Length: "
            + str(len(body)).encode()
            + b"\r\nConnection: close\r\n\r\n"
            + body
        )
        await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()


async def scheduled_reports():
    reports_file = DATA_DIR / "reports.json"
    try:
        done = json.loads(reports_file.read_text())
    except (OSError, ValueError):
        done = {}

    slots = {
        8: "🌅 家庭空气 · 早安报告",
        12: "☀️ 家庭空气 · 午间报告",
        20: "🌙 家庭空气 · 晚间报告",
    }
    while True:
        now = datetime.now(BEIJING)
        key = f"{now:%Y-%m-%d}-{now.hour}"
        if now.hour in slots and now.minute < 10 and key not in done:
            try:
                try:
                    latest = json.loads((DATA_DIR / "latest.json").read_text())
                except (OSError, ValueError):
                    latest = None
                await asyncio.to_thread(send_wecom, report_text(latest, now, slots[now.hour]))
                done = {item: value for item, value in done.items() if item.startswith(f"{now:%Y-%m-%d}")}
                done[key] = True
                atomic_json(reports_file, done)
                logging.info("Scheduled report sent: %s", key)
            except Exception as error:
                logging.warning("Scheduled report failed: %s", type(error).__name__)
        await asyncio.sleep(60)


async def main():
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # The stock device only supports legacy TLS. Restrict this listener to the
    # fake-cloud endpoint and do not reuse it for normal web traffic.
    tls.set_ciphers("DEFAULT:@SECLEVEL=0")
    tls.minimum_version = ssl.TLSVersion.TLSv1
    tls.load_cert_chain(CERT_FILE, KEY_FILE)

    aircat = await asyncio.start_server(handle_aircat, "0.0.0.0", 9000, limit=16384)
    fake_cloud = await asyncio.start_server(
        handle_fake_cloud, "0.0.0.0", 443, ssl=tls, limit=8192
    )
    logging.info("M1 service ready; awaiting device data")
    async with aircat, fake_cloud:
        await asyncio.gather(
            aircat.serve_forever(),
            fake_cloud.serve_forever(),
            scheduled_reports(),
        )


if __name__ == "__main__":
    asyncio.run(main())
