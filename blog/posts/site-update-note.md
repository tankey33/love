---
title: 如何从零搭建一个像这样的网站
date: 2026-03-13
summary: 从本地整理文件，到 GitHub 自动发布，再到 VPS 部署与绑定域名，这篇文章把整套流程和功能结构一次讲清楚。
pinned: true
cover: photo/03.jpg
---

# 如何从零搭建一个像这样的网站

![站点示意图](photo/03.jpg)

如果你也想做一个像这样的网站，其实不需要很重的技术栈。它本质上是一个**静态网站**，重点不在复杂后端，而在内容组织、页面结构、自动化生成和部署方式。

这篇文章把整套流程拆开来说：

- 网站有什么功能
- 本地怎么搭建
- 怎么 push 到 GitHub
- 怎么自动发布
- 怎么放到 VPS
- 域名怎么接进去

## 这个网站现在有哪些功能

先说结构。现在这套站点已经不是单页，而是一个比较完整的小型内容站：

### 1. 首页

- 时间线和氛围型视觉
- 音乐控制
- 响应式布局
- 手机和桌面都能正常看

### 2. 照片墙

- 自动从 `photo/` 目录读取图片
- 按文件时间新到旧排序
- 自动读取图片尺寸
- 自动生成照片数据
- 点击可以进入详情页

![照片墙演示](photo/08.jpg)

### 3. 照片详情页

- 自动读取图片基础信息
- 自动尝试读取 EXIF
- 显示拍摄参数（有就显示，没有就隐藏）
- 左右切图
- 直方图展示

### 4. 碎碎念 / 博客

- 文章写成 `.md`
- 放进 `blog/posts/`
- 自动生成文章列表
- 自动渲染成页面
- 支持置顶文章
- 支持封面图
- 支持搜索

### 5. 自动化发布

- push 到 GitHub 后自动生成内容
- 自动部署到 GitHub Pages
- 不需要每次手工改 HTML

## 本地怎么搭建

最简单的目录结构大概像这样：

```text
love/
├─ index.html
├─ photo.html
├─ photo-detail.html
├─ notes.html
├─ note.html
├─ photo/
├─ blog/posts/
├─ blog/rendered/
├─ assets/js/
├─ scripts/generate_posts.py
└─ .github/workflows/deploy-pages.yml
```

### 本地工作流

你平时只需要处理三类内容：

1. 页面文件
   - `index.html`
   - `photo.html`
   - `photo-detail.html`
   - `notes.html`
   - `note.html`

2. 图片
   - 直接放进 `photo/`

3. 文章
   - 直接放进 `blog/posts/`

也就是说，本地维护的重点其实很简单：
- 写页面
- 放图片
- 写 md

## 如何写一篇文章

最简单的文章格式是：

```md
---
title: 文章标题
date: 2026-03-13
summary: 一句话摘要
cover: photo/03.jpg
pinned: true
---

# 正文标题

这里写正文。

![插图](photo/08.jpg)
```

这里几个字段的作用分别是：

- `title`：文章标题
- `date`：日期
- `summary`：列表摘要
- `cover`：列表页封面图
- `pinned`：是否置顶

如果你不想让它置顶，就不要写 `pinned: true`。

## 如何让照片墙自动工作

现在照片墙已经改成自动化逻辑：

- 你只要把图片丢进 `photo/`
- 生成脚本会自动读取：
  - 文件名
  - 文件时间
  - 尺寸
  - 文件大小
- 然后自动生成 `assets/js/photo-data.js`

所以你不需要再一张张手写图片数据。

![照片目录演示](photo/06.jpg)

## 如何在本地生成内容

这个项目现在用一个 Python 脚本来处理内容：

```bash
python3 scripts/generate_posts.py
```

它会做两件事：

### 1. 处理文章

- 扫描 `blog/posts/*.md`
- 生成 `blog/posts.json`
- 生成 `blog/rendered/*.html`

### 2. 处理照片

- 扫描 `photo/`
- 读取图片信息
- 生成 `assets/js/photo-data.js`

所以这一个脚本，已经把“文章自动化”和“照片自动化”都串起来了。

## 如何 push 到 GitHub

如果你已经在本地初始化了仓库，那么平时更新内容的流程很简单：

```bash
git add .
git commit -m "Update site content"
git push origin main
```

通常你会在这些场景下 push：

- 新增文章
- 新增照片
- 改页面样式
- 改自动化脚本

## 如何通过 GitHub 自动部署

这个站点最省心的方式，就是 GitHub Pages。

你需要准备：

1. 一个 GitHub 仓库
2. 开启 GitHub Pages
3. 配置好 `.github/workflows/deploy-pages.yml`

现在这套 workflow 已经可以做到：

- push 到 `main`
- 自动运行生成脚本
- 自动部署到 GitHub Pages

也就是说，只要你 push，网站就会自己更新。

## 如何部署到 VPS

如果你不想只用 GitHub Pages，也可以放到 VPS。

最常见的方式是：

### 方案 1：Nginx 直接托管静态文件

适合这种站。

流程：

1. 把仓库 clone 到 VPS
2. 用 Nginx 指向网站目录
3. 配置域名
4. 配置 HTTPS

例如 Nginx 站点根目录可以直接指向：

```text
/var/www/love
```

然后把你的仓库内容同步过去。

### 方案 2：本地 push，VPS pull

最简单的维护方式：

- 本地改完 push 到 GitHub
- VPS 上 `git pull`
- Nginx 直接提供静态资源

### 方案 3：GitHub Actions 自动部署到 VPS

如果你想完全自动化，可以让 GitHub Actions：

- 在 push 后自动 ssh 到 VPS
- 自动 pull 最新代码
- 自动 reload Nginx

这个适合后面你网站更稳定时再接。

## GitHub Pages 和 VPS 怎么选

### GitHub Pages 更适合：

- 纯静态网站
- 更新频率不算夸张
- 想省事
- 不想管服务器

### VPS 更适合：

- 你还想挂别的服务
- 你要更强的可控性
- 你有自己的域名和 SSL 策略
- 你后面可能想接更多动态功能

## 域名怎么接

如果你要用自己的域名：

### GitHub Pages

- 仓库里放 `CNAME`
- DNS 解析到 GitHub Pages

### VPS

- DNS 解析到你的 VPS IP
- Nginx 配置 `server_name`
- 用 Let's Encrypt 配 HTTPS

## 这套方案为什么适合长期维护

因为它不是“每加一张图就改一次页面”，也不是“每写一篇文章就手抄一遍 HTML”。

它的核心是：

- **内容和页面分开**
- **图片自动化**
- **文章自动化**
- **部署自动化**

所以以后你维护的难度会很低。

你只需要记住：

- 图片丢进 `photo/`
- 文章丢进 `blog/posts/`
- 改完 push

剩下的都交给生成脚本和发布流程。

## 最后给一个最简操作流

如果你以后只是日常更新，最简单就是这几步：

### 加照片

- 丢进 `photo/`

### 加文章

- 丢进 `blog/posts/`

### 本地生成（可选，本地预览时用）

```bash
python3 scripts/generate_posts.py
```

### 提交并推送

```bash
git add .
git commit -m "Add new photos and post"
git push origin main
```

### 自动上线

- GitHub Actions 自动构建
- GitHub Pages 自动更新

这就是现在这套网站最舒服的维护方式。

![结尾配图](photo/11.jpg)

如果后面你愿意，我还可以继续把下一篇文章也给你补上：

- **如何给这个站接自定义域名与 HTTPS**
- **如何在 VPS 上用 Nginx 正式部署**
- **如何继续把它做成完整内容系统**
