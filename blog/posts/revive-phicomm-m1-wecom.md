---
title: 把停服的斐讯 M1 接回自己的服务器
date: 2026-11-03
summary: 不刷机，保留原厂固件，用 DNS 映射、Python 假云端和企业微信 Webhook 重新接住 PM2.5、甲醛、温湿度数据。
cover: blog/images/phicomm-m1-revival-cover.jpg
---

# 把停服的斐讯 M1 接回自己的服务器

![让旧空气检测仪重新连接家庭网络、自建服务器和手机通知](blog/images/phicomm-m1-revival-cover.jpg)

斐讯 M1 的传感器和屏幕还好好的，真正消失的是它依赖的云端。原厂固件会寻找固定域名，连不上时 Wi-Fi 图标一直闪，数据也没有地方可去。

这次我没有刷第三方固件，而是保留原厂系统，重新补上它缺失的那一段基础设施：让 M1 连接家里的 2.4 GHz Wi-Fi，把原来的云端域名解析到自己的服务器，在服务器上接收空气数据，再通过企业微信群机器人发送异常提醒和每天三次报告。

最终链路是：

```text
斐讯 M1 原厂固件
→ 家庭 2.4 GHz Wi-Fi
→ DNS 将 aircat.phicomm.com 指向自建服务器
→ TCP 9000 接收空气数据
→ HTTPS 443 应答设备激活请求
→ Python 做校验、阈值与去重
→ 企业微信 Webhook
```

![斐讯 M1 从原厂固件到企业微信的完整数据链路](blog/images/phicomm-m1-flow.png)

> 本文公开的是经过脱敏的可复用代码。真实 Wi-Fi 密码、SSH 密码、服务器地址、设备 MAC 和 Webhook key 都不会进入仓库。

## 先确认设备状态

这台 M1 使用原厂固件，设备信息接口返回的固件标识是 `Phic_BASIC_1_0`。这很重要：原厂固件走自己的 TCP 协议；如果已经刷了 zM1，通常会直接使用 MQTT，后面的做法就不适用了。

原厂固件进入配网模式后会建立类似 `EasyLink_XXXXXX` 的临时热点。操作时有三个容易忽略的条件：

- 家庭 Wi-Fi 必须提供 2.4 GHz；
- 加密方式最好兼容 WPA2/AES，只有 WPA3 时老设备可能无法加入；
- 配网热点存在时间较短，消失后需要重新长按按键约 3—4 秒。

## Windows 和 macOS：不用 App 给 M1 配网

下文只适用于原厂固件。先在电脑联网时下载 [配网脚本 m1-wifi.py](https://raw.githubusercontent.com/tankey33/love/main/blog/code/phicomm-m1-wecom/m1-wifi.py)，放进「下载」目录。脚本需要 Python 3 和 curl，不刷机，也不会把 Wi-Fi 密码写入文件或命令历史。

先确认路由器启用了 DHCP，并准备一个 2.4 GHz、WPA2/AES 的网络。按住 M1 按键约 3–4 秒后松开，电脑连上它发出的 `EasyLink_XXXXXX`。系统提示没有互联网是正常的；不要切回家庭 Wi-Fi，直到提交配置。

### Windows

从任务栏的 Wi-Fi 列表连上设备热点，打开 PowerShell。如果还没有 Python 3，先在能上网时安装；命令找不到 `py` 时可用 `python` 代替 `py -3`，先用 `python --version` 确认是 Python 3。

```powershell
curl.exe --http1.0 --noproxy "*" --max-time 5 http://10.0.0.1:8000/config-read
py -3 "$HOME\Downloads\m1-wifi.py"
```

这里明确写 `curl.exe`，避免 Windows PowerShell 5.1 把 `curl` 当作 `Invoke-WebRequest`。如果「下载」目录被重定向，请使用脚本的实际路径。

### macOS

从菜单栏 Wi-Fi 连上设备热点，再打开「终端」。先在联网时用 `python3 --version` 确认 Python 3 可用。

```bash
curl --http1.0 --noproxy '*' --max-time 5 http://10.0.0.1:8000/config-read
python3 ~/Downloads/m1-wifi.py
```

两种平台都按提示输入**家庭 2.4 GHz Wi-Fi** 的名称和密码，不是临时热点的名称。脚本先探测 `10.0.0.1:8000`，再向 `/config-write-uap` 提交 UTF-8 JSON，密码输入不回显。建议只在自己设备的热点上执行，因为这个原厂配网接口使用 HTTP。手动探测返回的设备配置也不要直接发到公开论坛。

### 确认真的连上了

- **读不到配置**：确认电脑仍连接 EasyLink，WLAN 获得了 `10.0.0.x` 地址。热点过期就重新进入配网；如果 VPN 或代理接管了局域网路由，先暂停它再试。
- **提交后热点消失**：这是设备切回客户端模式的正常表现。电脑重新连回家庭 Wi-Fi，在路由器 DHCP 租约列表中按机身 MAC 找 M1。HTTP 200 只说明配置收到，不代表已经联网；请求中途断开也先查租约再重试。
- **没有新租约**：核对 SSID、密码、2.4 GHz 和 WPA2 设置；排错时可以临时使用一个单独的纯英文 2.4 GHz SSID。已有租约却还不报数据，再查下面的 DNS、激活和 TCP 9000。

配网接口和验证流程可对照 [斐讯社区的原厂 M1 配网说明](https://phicomm-io.github.io/guides/m1-no-disassembly.html)；这里只用配网部分，不执行 OTA。

## 为什么需要“假云端”

M1 加入 Wi-Fi 后仍会寻找 `aircat.phicomm.com`。原厂服务消失后，仅仅让设备联网还不够，还要让这个域名落到我们能控制的服务器。

我在家庭网关的本地 DNS 映射里加入：

```text
aircat.phicomm.com = YOUR_SERVER_IP
```

如果使用 Surge 做网关，可以在“DNS → 本地 DNS 映射”中添加这条记录，并确保 M1 的 DNS 查询确实经过这台网关。只在电脑本机改 hosts 对 M1 没有作用。

设备随后会做两类请求：

| 端口 | 用途 | 服务端行为 |
|---|---|---|
| TCP 9000 | 心跳与空气数据 | 校验帧、回复心跳、解析 JSON |
| HTTPS 443 | `/device/active` 激活 | 返回最小的 `code: 0` 响应 |

激活接口只做一件事：告诉设备“激活成功”。服务不会提供固件地址，也不会冒充更新服务器。

```python
if b" /device/active?" in request_line:
    body = b'{"code":0,"message":"success"}'
else:
    body = b'{"code":0,"data":{}}'
```

原厂设备使用很老的 TLS 能力，所以这个 443 监听器需要单独兼容旧版 TLS。它应当与普通网站完全隔离，只服务这台设备，并在防火墙上尽量限制来源。

## 接住 TCP 9000 上的数据

M1 的数据不是普通 HTTP，而是带固定头和结束标记的 TCP 帧。服务端按 `0xff#END#` 切分帧，检查帧头、设备 MAC 和长度，再解析尾部 JSON。

核心逻辑可以缩成这样：

```python
END = b"\xff#END#"

while END in buffer:
    frame, buffer = buffer.split(END, 1)

    if len(frame) < 28 or frame[0] != 0xAA:
        return
    if frame[17:23] != EXPECTED_MAC:
        return
    if len(frame[28:]) + 3 != frame[24]:
        return

    data = json.loads(frame[28:])
```

空气数据里最关心的是四项：

```json
{
  "value": "12",
  "hcho": "36",
  "temperature": "23.8",
  "humidity": "51.2"
}
```

其中 `value` 是 PM2.5；甲醛原始值需要除以 1000，转换为 `mg/m³`。任何字段在进入告警逻辑前都要转为数值，并检查是否是有限数、是否落在合理物理范围内，避免畸形报文触发错误通知。

每收到一帧后，服务器还要回一条心跳：

```python
heartbeat = b'{"type":5,"status":1}'
writer.write(
    frame[:24]
    + bytes([34 + len(heartbeat)])
    + b"\x00\x00\x02"
    + heartbeat
    + END
)
await writer.drain()
```

这里不要随意改长度字段。老固件的解析器很脆弱，错误报文可能让 TCP 看起来仍然连接，却不再继续上报；遇到这种状态，修正服务端后还需要给 M1 断电重启。

## 阈值不是“超过一次就报警”

传感器会有瞬时波动。如果每个超限样本都发微信，群很快会被提醒淹没。我把规则做成带持续时间、恢复区间和重复抑制的状态机：

| 项目 | 异常触发 | 恢复通知 |
|---|---|---|
| PM2.5 | 高于 50 µg/m³，持续 1 分钟 | 低于 40，持续 5 分钟 |
| 甲醛 | 高于 0.08 mg/m³，持续 1 分钟 | 低于 0.06，持续 5 分钟 |

同一异常持续存在时，最短 30 分钟才再次提醒。服务把告警状态写入本地 JSON，即使进程重启，也不会立刻把同一异常当成新事件。

这两个数值参考《室内空气质量标准》GB/T 18883—2022，但要注意：标准里的 PM2.5 是 24 小时平均限值，甲醛是 1 小时平均限值。这里借用数值做家庭即时预警，不代表一次实时读数就能判定房间是否达标。

状态判断的核心是：

```python
alert = (
    high_started is not None
    and now - high_started >= 60
    and (not active or now - last_sent >= 1800)
)

recover = (
    active
    and low_started is not None
    and now - low_started >= 300
)
```

## 企业微信消息与北京时间

企业微信群机器人接受 JSON POST。Webhook URL 本身就是凭据，所以只从环境变量读取：

```python
body = json.dumps({
    "msgtype": "text",
    "text": {"content": message},
}, ensure_ascii=False).encode()

request = Request(
    os.environ["WECOM_WEBHOOK_URL"],
    data=body,
    headers={"Content-Type": "application/json"},
)
```

所有显示时间都显式使用 `Asia/Shanghai`，不依赖服务器当前位于哪个时区：

```python
from zoneinfo import ZoneInfo

BEIJING = ZoneInfo("Asia/Shanghai")
now = datetime.now(BEIJING)
```

除异常与恢复通知外，服务会在北京时间 08:00、12:00、20:00 发送早安、午间和晚间报告。每次发送前都检查最新样本年龄；如果数据超过两分钟，不把旧值冒充实时数据，而是提示检查设备、电源、Wi-Fi 和 DNS 网关。

独立测试 Webhook 成功，只能证明“服务器 → 企业微信”这半段链路可用。完整验收还需要在日志中看到 M1 的真实帧、`latest.json` 持续更新，并验证异常与恢复的状态变化。

## 用 systemd 长期运行

代码不依赖第三方 Python 包，Debian 11 自带的 Python 3 就能运行。部署目录与状态目录分开：

```text
/opt/m1-aircat/server.py
/opt/m1-aircat/cloud.crt
/opt/m1-aircat/cloud.key
/etc/m1-aircat.env
/var/lib/m1-aircat/latest.json
/var/lib/m1-aircat/state.json
```

真实配置放在 `/etc/m1-aircat.env`，权限设为 `0600`：

```bash
M1_MAC=aabbccddeeff
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=REPLACE_ME
DATA_DIR=/var/lib/m1-aircat
```

启动并看日志：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now m1-aircat
sudo journalctl -u m1-aircat -f
```

服务使用普通系统用户运行，只额外获得绑定 443 低端口所需的能力；文件系统默认只读，仅允许写入状态目录。比起让一个长期联网的 Python 进程直接以 root 身份运行，这个边界清楚得多。

## 排查顺序

这类旧硬件改造很容易同时出现 Wi-Fi、DNS、协议和服务器四层问题。按链路从近到远检查，效率最高：

1. `config-read` 能否读取设备信息；
2. M1 是否在路由器 DHCP 列表中获得地址；
3. M1 使用的 DNS 是否把目标域名解析到自建服务器；
4. 服务器 9000 和 443 是否监听，防火墙是否允许；
5. 日志中是否出现 M1 的 TCP 连接和数据帧；
6. `latest.json` 是否持续刷新；
7. 企业微信测试消息是否成功；
8. 用模拟数据分别测试持续超限、重复抑制和恢复通知。

“HTTP 200”“端口已监听”“测试消息成功”都只代表一段链路正常，不能单独当成整套系统已经完成。

## 完整代码

本文涉及的脱敏代码全部放在站点仓库中：

- [完整 Python 服务](https://github.com/tankey33/love/blob/main/blog/code/phicomm-m1-wecom/server.py)
- [环境变量模板](https://github.com/tankey33/love/blob/main/blog/code/phicomm-m1-wecom/m1-aircat.env.example)
- [systemd 服务文件](https://github.com/tankey33/love/blob/main/blog/code/phicomm-m1-wecom/m1-aircat.service)
- [安装与安全说明](https://github.com/tankey33/love/tree/main/blog/code/phicomm-m1-wecom)

代码刻意没有包含真实设备和服务器凭据。如果 Webhook key 曾出现在截图、聊天记录或 Git 历史中，应当先在企业微信中重新生成，再部署新 key。

## 写在最后

旧设备“失效”，有时并不是传感器坏了，而是它被设计成只能依赖一个已经消失的服务。把域名、协议、时间、状态和通知一层层补回来以后，这台很多年前的空气检测仪又有了新的用途。

这次改造最有价值的部分并不是某一段 Python，而是把一条模糊的“让它重新工作”拆成可验证的小链路：配网成功、DNS 命中、端口可达、帧能解析、状态会持久化、消息能送达。每一步都有证据，旧硬件才真正回到了自己手里。

## 参考

- [原厂 M1 免拆配网说明](https://phicomm-io.github.io/guides/m1-no-disassembly.html)
- [phicomm-m1-aircat-local：原厂协议与本地接入实现](https://github.com/yjzsg/phicomm-m1-aircat-local)
- [phicomm-aircat-srv：多语言协议实现与抓包资料](https://github.com/corbamico/phicomm-aircat-srv)
- [GB/T 18883—2022《室内空气质量标准》](https://www.ndcpa.gov.cn/doc/ucap/1625444428300685312/document/20230607/ZgwODgwF.pdf)
