---
title: 手把手教你搭建一个像这样的网站
date: 2026-03-13
summary: 从本地建站、整理照片、写 Markdown，到 push 到 GitHub、自动发布、再到 VPS 部署和域名接入，这篇文章把整套流程一步一步写清楚。
pinned: true
cover: photo/03.jpg
---

# 手把手教你搭建一个像这样的网站

![站点示意图](photo/03.jpg)

如果你也想做一个像这样的网站，其实完全可以从一个很简单的静态站开始，不需要一上来就搭数据库、后台管理系统、复杂框架。

这篇文章我按**手把手**的方式来写，尽量让你可以直接照着做。

这套站点现在的思路是：

- 首页负责氛围和入口
- `photo/` 文件夹负责照片墙
- `blog/posts/` 负责碎碎念 / 博客内容
- Python 脚本负责自动生成文章和照片数据
- GitHub 负责托管代码
- GitHub Pages 或 VPS 负责上线

如果你只是想要一个好看、轻量、可长期维护的网站，这种方案很合适。

---

## 一、先理解：这个网站到底是什么结构

你现在看到的这个站，本质上是一个**静态网站**。

它不是 WordPress，也不是必须依赖服务器动态渲染的博客系统。它更像是一组静态页面，加上一些自动生成的数据文件。

### 现在这套站点主要有这些页面

#### 1. 首页

- 负责整体氛围
- 可以放时间、标题、音乐、入口
- 更偏“展示”

#### 2. 照片墙 `photo.html`

- 自动读取 `photo/` 文件夹里的图片
- 按文件时间新到旧排序
- 自动根据图片尺寸排版
- 不需要手动写图片列表

#### 3. 照片详情页 `photo-detail.html`

- 点开单张图可查看详情
- 自动读取尺寸、大小、部分 EXIF
- 有直方图展示
- 可以左右切图

#### 4. 碎碎念列表页 `notes.html`

- 展示所有文章
- 支持置顶文章
- 支持搜索
- 支持卡片图文展示

#### 5. 单篇文章页 `note.html`

- 展示渲染后的文章内容
- 支持图片、代码、公式、表格、引用等

所以你可以把它理解成：

> 一个小型静态内容网站，里面同时有首页、相册和文章系统。

---

## 二、你需要准备什么

### 最少需要这些

1. 一台自己的电脑
2. 一个 GitHub 账号
3. 一个代码仓库
4. （可选）一个域名
5. （可选）一台 VPS

### 推荐安装这些工具

#### 1. Git
官网：<https://git-scm.com/>

#### 2. Python 3
官网：<https://www.python.org/>

#### 3. VS Code
官网：<https://code.visualstudio.com/>

#### 4. GitHub
官网：<https://github.com/>

如果你只是做静态站，以上这些就够了。

---

## 三、本地项目怎么搭起来

先在本地建一个目录，比如：

```bash
mkdir love
cd love
```

推荐目录结构像这样：

```text
love/
├─ index.html
├─ photo.html
├─ photo-detail.html
├─ notes.html
├─ note.html
├─ photo/
├─ blog/
│  ├─ posts/
│  ├─ rendered/
│  └─ posts.json
├─ assets/
│  └─ js/
├─ scripts/
│  └─ generate_posts.py
└─ .github/
   └─ workflows/
      └─ deploy-pages.yml
```

### 每个目录是干什么的

#### `photo/`
放所有照片。

以后你只要把图片丢进这个目录，脚本就会自动扫描、排序、生成数据。

#### `blog/posts/`
放所有 Markdown 文章。

以后你写文章，就直接在这里新增 `.md` 文件。

#### `blog/rendered/`
自动生成出来的文章 HTML。

你不需要手改这里，它是脚本自动产物。

#### `assets/js/photo-data.js`
自动生成出来的照片数据文件。

也不需要手动改。

#### `scripts/generate_posts.py`
最关键的自动化脚本。

它负责：

- 扫描文章
- 生成文章索引
- 预渲染 HTML
- 扫描照片
- 生成照片数据

---

## 四、照片墙是怎么自动工作的

现在这套逻辑已经改成：

> 你只要把图片丢进 `photo/` 文件夹。

然后脚本会自动：

- 按文件时间排序（新到旧）
- 读取图片宽高
- 读取文件大小
- 生成 `assets/js/photo-data.js`

也就是说，你以后不需要再做这些事：

- 不需要手动给每张图编号
- 不需要手动写图片数组
- 不需要手动改照片墙 HTML
- 不需要手动改详情页链接

### 你以后加照片的步骤

#### 第一步：把照片放进 `photo/`

例如：

```text
photo/
├─ img_001.jpg
├─ img_002.jpg
├─ img_003.jpg
```

#### 第二步：运行生成脚本

```bash
python3 scripts/generate_posts.py
```

#### 第三步：提交到 GitHub

```bash
git add .
git commit -m "Add new photos"
git push origin main
```

完成后，照片墙就会自动更新。

![照片墙演示](photo/08.jpg)

---

## 五、文章系统是怎么自动工作的

文章系统现在的逻辑是：

> 你只要把 `.md` 文件放进 `blog/posts/`。

脚本就会自动：

- 读取文章 front matter
- 生成文章列表 `blog/posts.json`
- 生成渲染后的 HTML `blog/rendered/*.html`
- 让 `notes.html` 自动显示它们

### 最简单的文章写法

新建一个文件，比如：

```text
blog/posts/my-first-post.md
```

内容可以这样写：

```md
---
title: 我的第一篇文章
date: 2026-03-13
summary: 这是一篇示例文章
cover: photo/03.jpg
pinned: false
---

# 我的第一篇文章

这里是正文。

![插图](photo/08.jpg)
```

### 这些字段分别是什么

#### `title`
文章标题。

#### `date`
文章日期，用来排序。

#### `summary`
列表页摘要。

#### `cover`
卡片封面图。

#### `pinned`
是否置顶。

如果某篇文章设置：

```md
pinned: true
```

那它会优先成为 `notes.html` 的大图首卡。

如果没有任何文章置顶，那么页面默认会把**日期最新**的一篇文章放到首卡位置。

这就是你现在网站上的置顶机制。

---

## 六、文章支持哪些内容

现在这套文章系统已经支持：

- 标题
- 段落
- 列表
- 引用
- 代码块
- 表格
- 图片
- 行内代码
- 粗体 / 斜体
- 数学公式（页面端渲染）

### 代码块示例

```python
def hello():
    print("hello world")
```

### 表格示例

| 功能 | 说明 |
| --- | --- |
| 照片墙 | 自动扫描 `photo/` |
| 文章系统 | 自动扫描 `blog/posts/` |
| 发布 | push 后自动上线 |

### 图片示例

```md
![示意图](photo/06.jpg)
```

### 链接示例

```md
[GitHub](https://github.com/)
```

---

## 七、本地怎么预览和生成

如果你已经把文件准备好了，日常维护就很简单。

### 每次更新内容时，建议这样做

#### 1. 改内容
例如：

- 新增照片到 `photo/`
- 新增文章到 `blog/posts/`
- 调整页面 HTML

#### 2. 本地运行生成脚本

```bash
python3 scripts/generate_posts.py
```

这个脚本会同时更新：

- `blog/posts.json`
- `blog/rendered/*.html`
- `assets/js/photo-data.js`

#### 3. 本地查看
如果你用 VS Code，可以装一个简单的本地预览插件；或者开一个本地静态服务器，比如：

```bash
python3 -m http.server 8080
```

然后打开：

<http://localhost:8080>

---

## 八、如何 push 到 GitHub

### 第一步：初始化 Git 仓库

如果你的项目还没初始化：

```bash
git init
git branch -M main
```

### 第二步：连接 GitHub 仓库

先去 GitHub 创建一个仓库。

GitHub：<https://github.com/>

创建好之后，把远程仓库连进来：

```bash
git remote add origin https://github.com/你的用户名/你的仓库名.git
```

### 第三步：提交并推送

```bash
git add .
git commit -m "Initial site setup"
git push -u origin main
```

之后日常更新就只需要：

```bash
git add .
git commit -m "Update content"
git push origin main
```

---

## 九、如何通过 GitHub 自动发布

如果你不想自己折腾服务器，最省心的方式就是 **GitHub Pages**。

GitHub Pages：<https://pages.github.com/>

### 现在这套流程是怎么自动化的

仓库里已经有：

```text
.github/workflows/deploy-pages.yml
```

当你 push 到 `main` 后，GitHub Actions 会自动：

1. 检出仓库
2. 运行：

```bash
python3 scripts/generate_posts.py
```

3. 生成照片和文章数据
4. 自动部署到 GitHub Pages

### GitHub Actions 是什么

官网：<https://github.com/features/actions>

它相当于 GitHub 自带的自动化流水线。

所以你以后不需要每次自己手工上传网站文件，只要 push，网站就会自动更新。

---

## 十、如果要在 VPS 上搭建，怎么做

如果你已经有 VPS，也完全可以放在自己的服务器上。

### 最常见的方法：Nginx 托管静态站

Nginx 官网：<https://nginx.org/>

思路是：

1. 把代码拉到 VPS
2. Nginx 指向网站目录
3. 配置域名
4. 配置 HTTPS

### 一个最常见的站点目录

例如：

```text
/var/www/love
```

你可以把仓库内容放到这里。

### 最简单的同步方式

#### 本地 push 到 GitHub

```bash
git push origin main
```

#### VPS 上 pull

```bash
cd /var/www/love
git pull origin main
```

如果你不想每次手工 pull，也可以让 VPS 直接从 GitHub Actions 自动触发部署。

---

## 十一、如何在 VPS 上配置域名

### 1. 准备域名

你需要在域名服务商那里买一个域名。

### 2. 解析到 VPS

把域名的 A 记录指向你的 VPS IP。

例如：

```text
love.example.com -> 你的 VPS IP
```

### 3. Nginx 配置 `server_name`

大概会像这样：

```nginx
server {
    listen 80;
    server_name love.example.com;
    root /var/www/love;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

### 4. 配 HTTPS

最常见的方式是 Let's Encrypt。

Let's Encrypt：<https://letsencrypt.org/>

Certbot：<https://certbot.eff.org/>

你可以用：

```bash
sudo certbot --nginx -d love.example.com
```

这样 HTTPS 基本就能配好。

---

## 十二、GitHub Pages 和 VPS 怎么选

### GitHub Pages 适合你如果：

- 网站是纯静态的
- 你想最省事
- 你不想自己维护服务器
- 你只是要一个稳定、好看的展示站

### VPS 更适合你如果：

- 你已经有服务器
- 你想完全掌控环境
- 你还准备在同一台机器上挂别的服务
- 你后面可能还想接动态功能

### 最实际的建议

如果你现在主要是：

- 放照片
- 写文章
- 做展示

那我更建议先用：

- **GitHub + GitHub Pages**

因为省事，足够稳定，也最容易长期维护。

如果后面你需要更复杂的东西，再迁到 VPS。

---

## 十三、几个互相关联的网站和服务

为了更方便，你可以把这几个东西串起来：

### 1. GitHub 仓库

管理代码：

<https://github.com/>

### 2. GitHub Pages

自动发布静态站：

<https://pages.github.com/>

### 3. GitHub Actions

自动构建与部署：

<https://github.com/features/actions>

### 4. VPS（可选）

如果你要自托管，可以选：

- <https://www.vultr.com/>
- <https://www.digitalocean.com/>
- <https://www.linode.com/>
- <https://www.oracle.com/cloud/free/>

### 5. 域名（可选）

如果要自定义域名，可以在你自己的域名商购买后接入。

### 它们之间怎么联动

最常见的联动方式是：

```text
本地写内容
   ↓
git push 到 GitHub
   ↓
GitHub Actions 自动生成并部署
   ↓
GitHub Pages 自动更新
   ↓
域名指向 Pages 或 VPS
```

这是最顺的一条链路。

---

## 十四、以后你日常维护时，真正需要做的事

其实不会很多。

### 加照片时

1. 把图片丢进 `photo/`
2. 本地运行：

```bash
python3 scripts/generate_posts.py
```

3. push：

```bash
git add .
git commit -m "Add photos"
git push origin main
```

### 加文章时

1. 把 `.md` 丢进 `blog/posts/`
2. 本地运行：

```bash
python3 scripts/generate_posts.py
```

3. push：

```bash
git add .
git commit -m "Add post"
git push origin main
```

### 改页面样式时

1. 改 HTML / CSS / JS
2. 提交
3. push

就这么简单。

---

## 十五、给你一个真正最简的整套流程

如果你今天要从零开始，最短路径是：

### 第一步
建项目目录，准备页面文件。

### 第二步
准备：

- `photo/`
- `blog/posts/`
- `scripts/generate_posts.py`

### 第三步
把网站代码放进去。

### 第四步
初始化 Git：

```bash
git init
git branch -M main
```

### 第五步
建 GitHub 仓库并连接：

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
```

### 第六步
推送：

```bash
git add .
git commit -m "Initial site"
git push -u origin main
```

### 第七步
开启 GitHub Pages。

### 第八步
以后只维护：

- `photo/`
- `blog/posts/`
- 页面文件

这就够了。

---

## 十六、如果你还想继续往下做

后面还可以继续加这些功能：

- 标签分类
- 多置顶文章排序
- 文章封面自动抽取
- EXIF 更完整展示
- 图片压缩和 WebP/AVIF 自动生成
- VPS 自动部署脚本
- 自定义域名与 HTTPS 完整教程

![结尾配图](photo/11.jpg)

如果你愿意，我下一篇还可以继续给你写成真正的系列教程，例如：

1. **如何把这个站部署到 GitHub Pages**
2. **如何把这个站部署到 VPS + Nginx**
3. **如何从零做一个自动更新的照片墙与博客系统**

这样你后面照着一步步做，会更轻松。
