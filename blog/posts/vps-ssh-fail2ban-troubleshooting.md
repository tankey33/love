---
title: VPS SSH 突然断开？一次 Fail2ban 封禁的排查与恢复实录
date: 2026-10-23
summary: 22 端口可达，SSH 却在握手前断开。按控制台恢复、日志取证、来源 IP 核验和密钥加固四步，排查 Fail2ban 封禁，避免盲目重装。
cover: images/ssh-fail2ban/recovery-flow.svg
---

SSH 连不上，并不意味着服务器坏了，更不意味着必须重装。一次看似“网络断开”的故障，最后定位到了 Fail2ban 的来源 IP 封禁。但恢复连接与解释所有异常，是两件不同的事。

本文整理自 2026-10-22 的排障记录，适用于 Debian／Ubuntu 类 Linux VPS。本次记录确认：**多次 SSH 密码认证失败后，Fail2ban 执行了封禁；通过服务商控制台定向解封后，SSH 恢复。** 至于为什么服务器把自己的公网 IP 记录为客户端来源，仍需要验证，不能直接归因于代理软件。

文中所有地址均为文档示例，不能直接用于真实连接。命令标明了执行位置：Mac 本地终端负责测试，VPS 控制台负责检查与恢复。服务名、端口、用户名、jail 和日志时间必须按实际环境替换。

## 一、先判断：故障卡在哪一层？

本次 Mac 上的调试输出停在：

```text
Connection established.
kex_exchange_identification: Connection closed by remote host
```

端口探测也显示 TCP 连接可以建立：

```bash
# Mac 本地终端：替换 VPS 地址和端口
nc -vz 203.0.113.10 22
```

这只说明测试时 TCP 端口可达，不能证明 SSH 握手、主机身份校验或用户认证能完成。**`kex_exchange_identification` 也不是 Fail2ban 的专属报错。** SSH 并发限制、防火墙、中间代理以及版本相关的来源惩罚机制，都可能造成提前断连。

| 现象 | 优先检查 |
| --- | --- |
| `Connection timed out` | 路由、云安全组、防火墙、端口过滤 |
| `Connection refused` | SSH 是否监听、目标端口是否正确，也可能是明确拒绝规则 |
| TCP 成功，SSH 握手前断开 | 封禁名单、SSH 日志、连接限制、中间转发 |
| `Permission denied (publickey)` | 用户名、匹配私钥、公钥安装位置和认证策略 |

本次之所以判断与 Fail2ban 有关，依据是封禁记录、SSH 原始日志和解封后的恢复结果，而不是单凭客户端的一行错误。

![SSH 故障恢复流程：控制台检查、核对封禁、定向解封、重试与追查](images/ssh-fail2ban/recovery-flow.svg)

## 二、先恢复：从控制台定向解封

### 1. 进入仍可用的管理入口

通过 VPS 服务商的 VNC、串口或网页控制台登录。这类入口通常不依赖目标系统的 SSH 端口；如果服务商所谓“网页终端”实际仍使用 SSH，则需要另找 VNC 或救援入口。

先保留当前会话，暂停客户端自动重连，避免错误密码继续触发规则。不要急着重装，也不要先清空防火墙或长期关闭 Fail2ban。

下列服务器命令使用 `sudo`；若已在 root 控制台，可以省略。本文以 `ssh.service`、`sshd` jail 和 22 端口为例，服务名也可能是 `sshd.service`。

### 2. 确认服务、监听和实际 jail

```bash
# VPS 控制台
sudo systemctl status ssh --no-pager
sudo systemctl status fail2ban --no-pager
sudo ss -lntp 'sport = :22'
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

先从全局状态里的 jail 列表确认名称，再查询对应 jail。重点看 `Banned IP list`，并对照 SSH 日志中的来源地址。**要解封的是服务器实际看到并封禁的来源 IP，不一定是你以为的家庭公网 IP。**

本案例中，封禁地址与 VPS 自身公网地址相同；下文把它统一替换为 `203.0.113.10`。普通场景里，VPS 地址与被封禁的客户端地址通常不同，不能混用。

### 3. 只解除确认相关的那条封禁

```bash
# VPS 控制台：先把值替换成已核对的封禁来源 IP
BANNED_IP='203.0.113.10'
sudo fail2ban-client set sshd unbanip "$BANNED_IP"
sudo fail2ban-client status sshd
```

确认该地址已从当前名单中移除，再从 Mac 发起一次新连接：

```bash
# Mac 本地终端：vpsuser 替换成实际账号
ssh -vvv -p 22 vpsuser@203.0.113.10
```

定向解封命令与状态查询可查阅 [Debian 的 fail2ban-client 手册](https://manpages.debian.org/bookworm/fail2ban/fail2ban-client.1.en.html)。如果同一来源仍被其他 jail 封禁，需要逐一核对相关规则；不要顺手执行“解封全部”。

### 4. 解封之后仍失败，继续看哪儿？

```bash
# VPS 控制台：只读检查
sudo journalctl -u ssh -n 100 --no-pager
sudo fail2ban-client status sshd
sudo journalctl -u fail2ban -n 100 --no-pager
```

按系统实际使用的防火墙后端检查 `sudo nft list ruleset` 或 `sudo iptables -S`，同时核查服务商安全组。若 jail 配置使用单独日志文件，应查该文件，不要把 journal 中“没有记录”当作没有封禁。

还要留意：封禁是否再次出现？是否是另一个 jail？解封操作是否真的针对同一个来源地址？`Restore Ban` 可能表示服务重启后恢复已有封禁，不等于刚刚又输错了一次密码。

## 三、再取证：把 SSH 与 Fail2ban 日志放在一条时间线上

解封是恢复手段，日志才帮助判断为什么发生。原始记录中的关键片段，统一脱敏后如下：

```text
17:50:54  SSH       Failed password for root from 203.0.113.10
17:50:56  SSH       Failed password for root from 203.0.113.10
17:51:19  SSH       Accepted password for root from 203.0.113.10
17:54:45  SSH       Failed password for root from 203.0.113.10
17:54:50  SSH       Failed password for root from 203.0.113.10
17:54:57  SSH       Failed password for root from 203.0.113.10
17:55:22  SSH       Failed password for root from 203.0.113.10
17:55:25  SSH       Failed password for root from 203.0.113.10
17:55:25  Fail2ban  Ban 203.0.113.10
```

这是一份便于阅读的日志摘录，保留了原稿时间和事件关系，不是未经整理的日志全文。时间按服务器日志记录，跨设备对照前应先确认时区和时钟。

![日志时间线：失败认证、一次成功登录、后续失败与最终封禁](images/ssh-fail2ban/evidence-timeline.svg)

### 1. 查指定来源的 Fail2ban 记录

```bash
# VPS 控制台：替换为实际封禁来源，固定字符串匹配避免点号被当作正则
BANNED_IP='203.0.113.10'
sudo zgrep -hF "$BANNED_IP" /var/log/fail2ban.log* | tail -80
```

若部署只记录到 journal，可使用：

```bash
sudo journalctl -u fail2ban --since '2026-10-22 17:45:00' --until '2026-10-22 18:05:00' --no-pager
```

文件不存在时，应确认日志后端与路径，而不是立即判断 Fail2ban 未工作。轮转日志的输出顺序也不一定是时间顺序，最终以每条记录的时间戳为准。

`Found` 表示过滤规则命中，`Ban` 表示执行封禁动作。不能把每条 `Found` 都视为一次独立的人工密码输入，应回到 SSH 原始日志核对。

### 2. 查相同时间段的 SSH 认证日志

```bash
sudo journalctl -u ssh --since '2026-10-22 17:50:00' --until '2026-10-22 17:57:00' --no-pager
```

使用传统认证日志的系统，也可以按来源筛选：

```bash
sudo zgrep -hF '203.0.113.10' /var/log/auth.log* | tail -100
```

关注 `Failed password`、`Accepted password`、`Invalid user`、连接关闭和限流相关记录。原稿中 17:51 的成功登录，与当时本人维护操作相符。**如果成功认证并非本人或授权管理员所为，应按疑似账户失陷调查，而不能只解封了事。**

### 3. 核对生效阈值，不照搬“输错三次”

```bash
sudo fail2ban-client get sshd maxretry
sudo fail2ban-client get sshd findtime
sudo fail2ban-client get sshd bantime
sudo fail2ban-client get sshd ignoreip
```

`maxretry` 是匹配阈值，`findtime` 是统计窗口，`bantime` 是封禁时长。还可能有递增封禁或其他 jail。服务商的简短提示不能代替运行配置，也不能从整理后的几条日志反推出完整阈值。

## 四、最容易误判的地方：为什么来源 IP 是 VPS 自己？

本案最特殊的线索，是 VPS 公网地址也出现在 SSH 的客户端来源字段中。它能说明服务器看到了什么，不能单独说明整条连接路径。

| 假设 | 需要什么证据 |
| --- | --- |
| Mac 的 SSH 经同一 VPS 代理出口回连 | 对照直连与代理路径，并在服务端观察对应测试连接 |
| VPS 内某个程序连接自己的公网 SSH | 检查相关进程、脚本及同一时间段的执行记录 |
| NAT 或转发改变来源 | 对照网络拓扑、转发规则及接收端观察结果 |

![直连与代理回流的路径对比；代理回流只是待验证假设](images/ssh-fail2ban/source-paths.svg)

### 1. 检查 OpenSSH 自己的配置

```bash
# Mac 本地终端
ssh -G -p 22 vpsuser@203.0.113.10 | grep -Ei '^(hostname|proxycommand|proxyjump|port) '
```

这能显示 OpenSSH 的显式跳板或代理配置。**没有 `ProxyCommand` 或 `ProxyJump`，也不能排除 Clash／Surge 的 TUN、透明代理或网络层分流。** `ssh -G` 的用途见 [OpenSSH ssh 手册](https://man.openbsd.org/ssh)。

### 2. 看当前 SSH 会话实际被记录的来源

```bash
# 在刚建立的 VPS SSH 会话里执行，不是在普通 VNC shell 里
printf '%s\n' "$SSH_CONNECTION"
```

四个字段依次为：客户端 IP、客户端端口、服务器 IP、服务器端口。比如普通直连可能显示：

```text
198.51.100.25 54321 203.0.113.10 22
```

这是字段说明用的虚构例子。原稿里的会话两端地址相同，是值得追查的线索，但它只描述那次成功会话，不自动证明此前失败会话走了完全相同的路径。

### 3. 必要时做一次有边界的对照测试

在服务商控制台中短时间观察 SSH 流量：

```bash
# VPS 控制台：需要已安装 tcpdump，替换实际 SSH 端口
sudo timeout 30 tcpdump -nn -i any -c 30 'tcp port 22'
```

同时在 Mac 发起一次连接，记录测试时间，按来源地址、端口和时间对应流量。公网扫描也可能进入输出，不能把看到的第一条数据包当成自己的连接；抓包没看到数据也不是单一结论，需要考虑接口、过滤条件及阻断位置。

若使用 Clash／Surge，可按当前客户端版本为 VPS 目标地址设置直连，再做相同测试。不要仅用浏览器或 `curl` 查出口判断 SSH 路径：HTTPS 与 SSH 可能被不同规则处理，`--noproxy` 也不能保证绕过系统级 TUN。

## 五、天气提醒任务有没有关系？

原稿记录了两个天气任务：一个约每 15 分钟检查，另一个每天 07:00 推送。17:30、17:45、18:00 的检查日志正常结束，而认证失败集中在 17:50—17:55。

**现有记录没有显示天气提醒触发 SSH 失败的直接证据。** 正常的天气 API 请求和 HTTPS 消息推送，本身不会被 SSH 认证失败过滤规则计数；如果脚本另外调用 SSH，则需要单独检查。

对照实际文件和服务名称，查看 service 的启动命令、对应时间段日志，以及脚本是否使用 `ssh`、`paramiko` 或通过子进程发起连接。关键词搜索只能提供线索，未命中不能证明依赖库、包装脚本或动态调用绝不存在。不要因为任务“刚好在同一台 VPS 上”就将它认定为根因。

## 六、防止复发：先验证密钥，再调整认证策略

密码输错会产生认证失败；迁移到密钥能减少这类人为错误，但密钥配置错误和其他扫描仍可能被规则计入。Fail2ban 仍应保留，阈值也应根据日志和实际运维需求评估。

生成密钥、安装公钥和配置 FinalShell 的完整步骤，放在另一篇独立教程中：[SSH 公钥和私钥入门：Mac、Windows 与 FinalShell](note.html?slug=ssh-keys-mac-windows-finalshell)。这里专注于恢复后的验证顺序。

### 1. 保留恢复入口，用新连接验证

```bash
# Mac 本地终端：私钥路径、用户名、地址和端口都要按实际修改
ssh -p 22 -i ~/.ssh/id_ed25519_vps_mac \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  -o PasswordAuthentication=no \
  -o KbdInteractiveAuthentication=no \
  vpsuser@203.0.113.10
```

登录后执行 `whoami`，确认账号。提示输入密钥口令，是解锁本地私钥，不是 VPS 账号密码。如果服务器本来要求额外的多因素认证，不要为了通过这个测试移除原有策略。

### 2. 检查配置，再决定是否关闭密码

```bash
# VPS 控制台：查看当前有效配置
sudo /usr/sbin/sshd -T | grep -Ei 'permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|authenticationmethods'
```

对于已经确认只需公钥登录、且不依赖键盘交互式多因素认证的服务器，可以评估以下设置：

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
```

如果仍需要 root 通过密钥登录，可评估 `PermitRootLogin prohibit-password`；若原本已经禁止 root 登录，不应为照抄示例而重新开放。日常使用具备必要 sudo 权限的普通用户通常更便于权限管理。

修改前备份实际配置文件，并保留控制台。`Include`、文件读取顺序和 `Match` 都会影响结果，新建一个配置片段并不保证覆盖已有值。存在条件规则时，可按实际连接信息使用 `sshd -T -C` 核对。相关选项与取值规则见 [OpenSSH sshd_config 手册](https://man.openbsd.org/sshd_config)。

### 3. 校验、重载，再验证一次

```bash
# VPS 控制台：先通过语法检查，才重载已确认的服务
sudo /usr/sbin/sshd -t && sudo systemctl reload ssh
```

重载后另开新会话，重新验证密钥登录和有效配置，再关闭旧会话。如失败，在仍保持的控制台恢复刚才备份的配置，校验后重新加载。配置阶段不要反复猜密码。

### 4. 不要无条件把服务器自身 IP 加白

把 VPS 自身公网地址加入 `ignoreip`，可能让代理回流或自连接异常绕过防护。应先核实路径与调用来源，再决定是否需要精确、受控的例外；“解封一次”不等于“永久信任这个来源”。

## 七、这次案例最终能确认什么？

| 结论层级 | 本次记录支持的判断 |
| --- | --- |
| 已确认 | 多次 SSH 密码认证失败后出现 Fail2ban `sshd` jail 封禁记录，控制台解封后 SSH 恢复 |
| 已观察 | 认证日志中的来源地址与 VPS 公网地址相同 |
| 尚未证实 | 代理回流、自连接或 NAT，究竟是哪一种造成了该来源地址 |
| 暂无直接证据 | 天气提醒任务触发了这次封禁 |

处理这类故障的顺序是：**保住控制台入口，核对并解除相关封禁，对齐认证日志，验证真实来源路径，最后再做认证加固。** 恢复之后保留必要日志，有助于识别下一次异常是否属于同一个原因。

若发现并非本人或授权管理员操作的成功登录，应保留证据、控制访问、从可信设备轮换凭据并检查持久化机制；必要时从可信镜像重建。那已超出“密码输错导致临时封禁”的范围。
