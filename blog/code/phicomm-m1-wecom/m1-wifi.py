#!/usr/bin/env python3
"""Provision an original-firmware Phicomm M1 over its EasyLink hotspot."""
import getpass
import json
import os
import shutil
import subprocess
import sys
import warnings

BASE = "http://10.0.0.1:8000"


def request(curl, endpoint, payload=None):
    cmd = [curl, "-q", "--http1.0", "--noproxy", "*", "--connect-timeout", "3",
           "--max-time", "10", "--silent", "--show-error", "--output", os.devnull,
           "--write-out", "%{http_code}"]
    if payload is not None:
        cmd += ["--header", "Content-Type: application/json", "--header", "Expect:",
                "--data-binary", "@-"]
    result = subprocess.run(cmd + [BASE + endpoint], input=payload, stdout=subprocess.PIPE)
    return result.returncode == 0 and result.stdout == b"200"


def main():
    curl = shutil.which("curl.exe" if os.name == "nt" else "curl")
    if not curl:
        sys.exit("未找到 curl。请先安装 curl，再连接 M1 的 EasyLink 热点。")
    if not request(curl, "/config-read"):
        sys.exit("读取失败。确认电脑仍连接这台 M1 的 EasyLink 热点，再重试。")
    ssid = input("家庭 2.4 GHz Wi-Fi 名称：")
    if not 1 <= len(ssid.encode("utf-8")) <= 32:
        sys.exit("Wi-Fi 名称应为 1–32 个 UTF-8 字节。")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = getpass.getpass("Wi-Fi 密码（不回显）：")
    if not password:
        sys.exit("此脚本用于有密码的 WPA2 网络，密码不能留空。")
    payload = json.dumps(
        {"SSID": ssid, "PASSWORD": password, "DHCP": True, "IDENTIFIER": 1},
        ensure_ascii=False,
    ).encode("utf-8")
    if request(curl, "/config-write-uap", payload):
        print("设备已收到配置。请连回家庭 Wi-Fi，在路由器 DHCP 列表确认 M1。")
    else:
        sys.exit("未收到 HTTP 200。设备可能已关闭热点；先查 DHCP 租约，再决定是否重试。")


if __name__ == "__main__":
    try:
        main()
    except getpass.GetPassWarning:
        sys.exit("当前终端无法隐藏密码。请在交互式 PowerShell 或终端中运行。")
    except (KeyboardInterrupt, EOFError):
        sys.exit("\n已取消。")
