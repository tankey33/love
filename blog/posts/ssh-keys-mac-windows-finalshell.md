---
title: SSH 公钥和私钥入门：Mac、Windows 配置与 FinalShell 连接 VPS 图文教程
date: 2026-10-22
summary: 从公钥与私钥的区别开始，在 Mac 和 Windows 生成密钥，把公钥放到 Linux VPS，再用 FinalShell 导入私钥登录，并排查常见连接错误。
cover: images/ssh-finalshell/key-flow.svg
---

更新于 2026-10-23。

第一次配置 SSH 密钥，最容易卡住的不是命令，而是三个问题：公钥框里填什么？私钥保存在哪里？为什么 FinalShell 选了“公钥”，却让自己导入“私钥”？这篇教程把它们串成一条可以照着操作的路线。

先记住一句话：**公钥放到服务器，私钥留在自己电脑；FinalShell 选择“公钥”认证，导入的却是私钥。** 本文按 Mac / Windows 电脑连接 Linux VPS 的场景讲解，Windows 是客户端，不是服务器。

## 先看路线：你现在应该做哪一步？

| 阶段 | 在哪里操作 | 完成后应该得到什么 |
| --- | --- | --- |
| 1. 认识密钥 | 阅读第一节 | 分清公钥、私钥与密钥口令 |
| 2. 生成密钥 | 自己的 Mac 或 Windows | 一份私钥和一份 `.pub` 公钥 |
| 3. 登记公钥 | 服务商面板或 VPS 终端 | 目标 Linux 账号已授权这把公钥 |
| 4. 配置连接 | 自己电脑的 FinalShell | “公钥”认证已选中对应私钥 |
| 5. 验证登录 | FinalShell 与本地终端 | 能建立新会话并确认登录用户 |

**Mac 用户看第三节，Windows 用户看第四节，完成后都从第五节继续。** 两台电脑都要连接时，分别生成密钥、分别登记公钥即可。如果已经有密钥对，确认自己持有匹配的私钥后，可以直接进入第五节。

## 一、公钥和私钥，到底有什么区别？

生成一对 SSH 密钥后，通常会得到两个文件：

| 文件示例 | 含义 | 放在哪里 |
| --- | --- | --- |
| `id_ed25519_vps_mac` | 私钥，用来证明你的身份 | 自己的电脑、可信 SSH 客户端 |
| `id_ed25519_vps_mac.pub` | 公钥，用来验证签名 | VPS 对应账号的授权列表 |

可以把公钥理解为服务器上的“验签样本”，私钥则是你独有的“签名工具”。登录时，客户端用私钥对与本次会话相关的数据签名，服务器用已经登记的公钥验证。**正常的 SSH 公钥认证不会把私钥发送给 VPS。** SSH 的传输加密和用户身份认证是不同环节，不要把它理解成“把私钥上传，再用公钥解开密码”。

![SSH 密钥登录流程：本机保管私钥，服务器保存公钥，通过签名验证身份](images/ssh-finalshell/key-flow.svg)

公钥可以交给需要登录的服务器管理员；私钥要像密码一样保护。公钥末尾的备注可能包含设备名或邮箱，公开时仍应留意。给私钥设置的 **passphrase（密钥口令）** 用来保护本地私钥文件，它不是 VPS 账号密码。即使不再输入服务器密码，登录时也可能需要输入这个口令。

如果私钥丢了，不能靠公钥还原。你需要生成新密钥，并通过仍可用的登录方式或服务商控制台更新授权。如果私钥泄露，要从服务器移除对应公钥并更换密钥，单纯修改账号密码并不能撤销那把密钥的权限。密钥对与保护方式可参考 [Microsoft OpenSSH 密钥管理说明](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_keymanagement)。

## 二、开始前，先确认这几件事

准备好 VPS 地址、SSH 端口和登录用户名，以及一种当前可用的访问方式：密码、已有私钥，或者服务商提供的网页控制台。

下文统一用 `203.0.113.10` 作为文档示例地址，用 `vpsuser` 代表实际登录账号，端口用 `22`。**这些值必须替换成你自己的；示例地址不能用于真实连接。** 云镜像的默认用户也可能是 `ubuntu`、`debian` 等，不要因为截图里写着 `root` 就照抄。

建议 Mac 与 Windows 分别生成一对密钥，再把两份公钥都登记到 VPS。这样其中一台电脑丢失时，可以只撤销它的访问权限。

本文以 Ed25519 为例。先检查目标文件是否已经存在；如果 `ssh-keygen` 提示覆盖，选择 `n`，改个文件名再生成，避免把旧密钥覆盖掉。

## 三、Mac：在终端生成密钥

### 1. 创建目录并生成

在 Mac 的“终端”执行：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -C "mac-vps" -f ~/.ssh/id_ed25519_vps_mac
```

出现 `Enter passphrase` 时，输入一段自己能妥善保存的密钥口令，再输入一次确认。终端输入口令时通常不显示字符，这是正常现象。`-C` 后面的内容只是备注，不必填写邮箱，也不是服务器用户名。

生成后设置私钥权限：

```bash
chmod 600 ~/.ssh/id_ed25519_vps_mac
ls -l ~/.ssh/id_ed25519_vps_mac*
```

此时应看到私钥和同名 `.pub` 公钥各一份。这里设置的是 Mac 本地文件权限，稍后还要单独设置 VPS 上的目录权限。

### 2. 复制公钥

```bash
pbcopy < ~/.ssh/id_ed25519_vps_mac.pub
```

这条命令把公钥复制到剪贴板。也可以用下面的命令查看：

```bash
cat ~/.ssh/id_ed25519_vps_mac.pub
```

内容通常是一整行：算法名、长字符串、备注。类似 `ssh-ed25519 AAAA… mac-vps`，其中省略号只是示意，实际操作必须复制完整内容。

### 3. 找到要给 FinalShell 的私钥

私钥路径是 `/Users/你的用户名/.ssh/id_ed25519_vps_mac`。在 Mac 的文件选择窗口中，可按 `Command + Shift + G`，输入 `~/.ssh` 进入隐藏目录，再选中**不带 `.pub`** 的文件。

生成参数和文件格式可参考 [OpenSSH ssh-keygen 手册](https://man.openbsd.org/ssh-keygen)。

## 四、Windows：在 PowerShell 生成密钥

### 1. 确认有 OpenSSH 客户端

打开 PowerShell，执行：

```powershell
ssh -V
Get-Command ssh-keygen
```

如果提示找不到命令，在 Windows 的“可选功能”里安装 **OpenSSH Client / OpenSSH 客户端**，再重新打开 PowerShell。这里只需要客户端；连接 Linux VPS 不需要在 Windows 上安装 OpenSSH Server。

### 2. 生成 Windows 专用密钥

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh" | Out-Null
ssh-keygen -t ed25519 -C "windows-vps" -f "$env:USERPROFILE\.ssh\id_ed25519_vps_windows"
```

按提示设置密钥口令。生成的两个文件通常位于：

```text
C:\Users\你的用户名\.ssh\id_ed25519_vps_windows
C:\Users\你的用户名\.ssh\id_ed25519_vps_windows.pub
```

不要把私钥放在公共共享目录，也不要通过聊天、邮件或公开仓库传递。使用自己 Windows 账户下的 `.ssh` 目录；如果后面遇到“权限太宽”的报错，再检查私钥文件的“属性 → 安全 → 高级”，移除不必要的其他用户或广泛用户组读取权限，保留本人的必要访问权限。

### 3. 复制公钥

```powershell
Get-Content -Raw "$env:USERPROFILE\.ssh\id_ed25519_vps_windows.pub" | Set-Clipboard
```

FinalShell 导入私钥时，选择不带 `.pub` 的那个文件。Windows 文件资源管理器可以开启“文件扩展名”显示，减少选错文件的机会。

## 五、把公钥放进 VPS

生成密钥只是本地准备工作。服务器还不知道你是谁，必须先登记公钥。

**正在创建新 VPS，且面板支持注入密钥：选方式 A。已有 VPS 能正常登录：通常选方式 B。** 已有实例只有在服务商明确支持更新密钥时，才使用面板绑定；两种方式不必都做。

### 方式 A：在服务商面板添加 SSH 公钥

有些面板提供“添加 SSH 密钥”。名称可以填 `MacBook-VPS` 或 `Windows-VPS`，公钥框则粘贴刚才 `.pub` 文件里的**完整单行内容**。

![错误示例：SSH 公钥输入框里填入了 GitHub 仓库网址](blog/images/ssh-finalshell/panel-wrong-url.png)

**图中是错误填写示例：`https://github.com/...` 是仓库网址，不是 SSH 公钥。** 公钥框也不能填写文件路径、VPS 地址、私钥全文或 `SHA256:...` 指纹。正确内容通常以 `ssh-ed25519` 或 `ssh-rsa` 开头，后面跟密钥数据。

下面按字段对照填写。图中的密钥字符串只表示格式，不能复制使用；你要粘贴自己的 `.pub` 文件完整内容。

![添加 SSH 公钥的正确填写示意：名称是备注，公钥来自本机 pub 文件](images/ssh-finalshell/panel-correct.svg)

| 面板区域 | 本教程应该怎样操作 |
| --- | --- |
| 名称 | 填易辨认的备注，例如 `MacBook-VPS`，不决定 Linux 登录用户名 |
| 公钥 | 粘贴本机 `.pub` 文件完整单行内容，不填网址或文件路径 |
| 生成密钥对 | 已在本机生成时无需再点，避免混淆两套密钥 |
| 密钥类型、大小、私钥格式 | 截图中这些位于“生成密钥对”区域，不能据此认定粘贴的公钥已正确解析 |
| 保存 | 提交前确认公钥完整，再按服务商流程选择实例或绑定账号 |

你提供的截图中，`2048 RSA2` 的标签和公钥框里的网址同时出现，**不能把这个标签当成公钥有效的证明**。实际支持的类型与实例注入方式需要查看该服务商说明；面板名称未明确时，不应猜测点击“保存”之后会发生什么。

面板里“保存了密钥”不一定代表它已安装到现有 VPS。部分服务商只在创建实例时注入，需要在创建页面选择该密钥；已有机器是否支持绑定、更新，要以服务商说明为准。不要为了添加公钥直接重装现有服务器。

即使面板有“生成密钥对”按钮，本文仍采用在自己的电脑生成、只上传公钥的方式，便于明确私钥的保管位置。

### 方式 B：登录已有 Linux VPS，追加到授权文件

先通过当前可用的方式登录，保持这个连接不要关闭。确认当前账号就是稍后 FinalShell 要登录的账号：

```bash
whoami
echo "$HOME"
```

在 **VPS 终端**执行以下命令。`nano` 不存在时，改用服务器已有的文本编辑器：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
nano ~/.ssh/authorized_keys
```

把公钥粘贴到末尾的新一行，保留已有公钥；每把公钥占一行。编辑器屏幕上的自动折行不一定是真换行，但不能手动把一把密钥拆成多行。使用 nano 时，按 `Ctrl + O`、回车保存，再按 `Ctrl + X` 退出。

Mac 和 Windows 使用不同密钥时，把两份 `.pub` 内容分别追加为两行。**此处只放公钥，不放以 `BEGIN OPENSSH PRIVATE KEY` 开头的私钥。**

通常，`root` 的文件是 `/root/.ssh/authorized_keys`，普通用户则在自己的家目录下。给 `root` 添加公钥，不会自动让 `ubuntu` 或 `vpsuser` 也获得授权。以目标用户操作可以减少文件归属错误；不要顺手给整个家目录执行递归改权限命令。

默认授权文件位置和格式见 [OpenSSH sshd 手册](https://man.openbsd.org/sshd)。管理员可以改变 `AuthorizedKeysFile` 配置；如果默认位置不生效，需要按服务器实际配置检查。单纯追加公钥通常无需重启 SSH 服务。

## 六、FinalShell：选择“公钥”，导入“私钥”

下面按照 FinalShell 的连接编辑界面操作。不同版本按钮位置可能略有差异，关键字段一致。

![FinalShell 公钥认证字段示意，主机使用文档示例地址](images/ssh-finalshell/finalshell-fields.svg)

图为字段示意图，并非实际连接成功截图。

1. 新建 SSH 连接，或打开已有连接的编辑窗口。
2. 填写名称、VPS 主机地址、SSH 端口和实际用户名。
3. 在“认证 → 方法”里，把“密码”改成“公钥”。
4. 点击“私钥”一栏旁的“浏览”。
5. 在“选择私钥”窗口点击“导入”，选择本机**不带 `.pub` 的私钥文件**。
6. 如果软件要求口令，填写生成密钥时设置的 passphrase；导入后选中对应条目并确认。
7. 回到连接窗口，确认已经选中私钥，点击“确定”或“应用”，再打开连接。首次出现服务器主机指纹时，通过服务商控制台等可信渠道核对后再接受。

![FinalShell 选择私钥窗口，可导入并选择 ED25519 私钥](blog/images/ssh-finalshell/finalshell-import.png)

截图中的列表名称 `root` 是私钥条目的名称，不能代替连接设置中的用户名。列表出现一把密钥只说明它已被导入，不代表服务器已经安装匹配公钥，也不代表已经登录成功。

为什么方法叫“公钥”，却让你选择私钥？因为“公钥”是认证机制的名称：服务器用公钥验证，而客户端必须持有私钥才能签名。**把 `.pub` 文件导入这个位置，是新手最容易犯的错误之一。**

## 七、验证：确认这次真的用了密钥

先在 FinalShell 中打开一个新的连接，进入终端后执行 `whoami`，检查是否为预期账号。看到私钥列表、保存成功或弹出终端窗口，都不能单独作为认证成功的依据。

接着保留旧连接，另开一个本地终端窗口测试。以下命令禁用本次测试中的密码和键盘交互回退，避免误把“最后又输密码登录成功”当成密钥配置成功。

Mac：

```bash
ssh -p 22 -i ~/.ssh/id_ed25519_vps_mac -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no vpsuser@203.0.113.10
```

Windows PowerShell：

```powershell
ssh -p 22 -i "$env:USERPROFILE\.ssh\id_ed25519_vps_windows" -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no vpsuser@203.0.113.10
```

首次连接会询问是否信任服务器主机密钥。应通过服务商控制台或可信的既有渠道核对主机指纹后再接受。**主机指纹用于验证服务器身份，与你刚生成的用户公钥是两回事。** 如果服务器要求额外的多因素认证，上面的“只用公钥”测试可能无法完成整个登录，应按管理员策略处理。

出现 `Enter passphrase for key ...` 是在解锁本地私钥，不是要求 VPS 密码。登录成功后执行 `whoami`，确认进入了预期账号。

## 八、排错：先看网络，再看身份，最后看格式

不要一遇到失败就重新生成密钥。先根据错误信息判断卡在“连到服务器”还是“验证身份”，再处理对应问题。

| 现象 | 优先检查 |
| --- | --- |
| 连接超时 | VPS 地址、端口、安全组、防火墙及网络是否可达 |
| Connection refused | SSH 服务是否监听该端口，端口是否填错 |
| Permission denied (publickey) | 用户名、公钥安装位置、是否选了匹配私钥、权限及服务器认证策略 |
| invalid private key / 导入失败 | 是否误选 `.pub`、文件是否完整、密钥口令、客户端版本与格式兼容性 |
| 私钥权限过宽 | Mac 的文件权限或 Windows 的文件 ACL 是否允许其他用户访问 |
| 主机密钥改变警告 | 是否重装或更换服务器，通过可信渠道重新核对指纹 |

### 终端能连，FinalShell 不能连

先对照两个客户端的地址、端口、用户名和私钥是否一致。终端用了哪一把私钥，FinalShell 就导入对应文件。再检查密钥口令，并从 [FinalShell 官方网站](https://www.hostbuf.com/) 获取适合系统的版本。

提供的截图显示 ED25519 条目已被识别，但不能据此保证所有版本都支持所有私钥格式。旧版本出现格式问题时，先更新客户端；不要直接覆盖现有密钥。

确实需要兼容 RSA PEM 私钥的客户端时，可以另外生成一对，例如 Mac：

```bash
ssh-keygen -t rsa -b 4096 -m PEM -C "finalshell-compat" -f ~/.ssh/id_rsa_vps_finalshell
```

Windows PowerShell：

```powershell
ssh-keygen -t rsa -b 4096 -m PEM -C "finalshell-compat" -f "$env:USERPROFILE\.ssh\id_rsa_vps_finalshell"
```

生成后仍需设置口令，把这对新密钥的 `.pub` 公钥追加到 VPS，再在 FinalShell 导入它的私钥。PEM 是私钥存储格式，不等于解决全部算法协商问题；不要为了连接而盲目启用旧的 SHA-1 `ssh-rsa` 签名。相关格式提示来自 [FinalShell 官方常见问题](https://www.hostbuf.com/t/1088.html)。

### 两个客户端都不能连

回到仍保留的旧会话，核对目标用户、家目录、`.ssh` 与 `authorized_keys` 权限和归属。再由管理员检查 `PubkeyAuthentication`、`AuthorizedKeysFile`、账号访问限制和 SSH 日志。系统不同，日志可能在 journal、`/var/log/auth.log` 或 `/var/log/secure`。

确需查看客户端详细日志时，可给测试命令加 `-vvv`。日志可能含真实地址、用户名和本地路径，分享前应脱敏；不要贴私钥全文。

## 九、确认成功后，再考虑关闭密码登录

配置初期不要急着禁用密码或关闭旧会话。先确认新窗口能用密钥登录，FinalShell 也正常，并且服务商网页控制台等恢复入口可用。日常管理可以使用普通用户加必要的 sudo 权限。

如果决定只允许密钥认证，应由管理员结合实际系统检查 `PasswordAuthentication`、`KbdInteractiveAuthentication`、`AuthenticationMethods` 及配置片段的覆盖关系，修改后先做配置语法检查，再按发行版方式重新加载服务。关闭某一个密码选项不一定消除所有交互式密码入口；本教程不提供一条直接关闭所有入口的命令。

## 完成后，核对这五项

- 自己电脑保存着私钥，且知道对应的密钥口令。
- VPS 上登记的是匹配的公钥，安装在实际登录用户的授权文件中。
- FinalShell 选择“公钥”认证，导入的是不带 `.pub` 的私钥。
- 新连接已登录成功，`whoami` 返回预期账号。
- 旧登录方式和恢复入口已确认可用，再决定是否调整密码认证策略。

只要记住“电脑保管私钥，服务器登记公钥”，就能把面板、文件和客户端这三处设置对应起来。
