---
title: 手把手教你搭建一个像这样的网站
date: 2026-03-13
summary: 从本地建站、整理照片、写 Markdown，到 push 到 GitHub、自动发布、再到 VPS 部署和域名接入，把整套流程一步一步写清楚。
pinned: true
cover: https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1600&q=80
---

# 手把手教你搭建一个像这样的网站

![建站](https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1600&q=80)

- 首页负责氛围和入口
- `photo/` 文件夹负责照片墙
- `blog/posts/` 负责碎碎念 / 博客内容
- Python 脚本负责自动生成文章和照片数据
- GitHub 负责托管代码
- GitHub Pages 或 VPS 负责上线

---

## 一、先理解：这个网站到底是什么结构

你现在看到的这个站，本质上是一个**静态网站**。

### 站点页面

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
- 显示拍摄参数（有就显示，没有就隐藏）
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

做静态站，以上这些就够了。

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

把图片丢进这个目录后，脚本会自动扫描、排序、生成数据。

#### `blog/posts/`
放所有 Markdown 文章。

文章直接在这里新增 `.md` 文件。

#### `blog/rendered/`
自动生成出来的文章 HTML。

这里不用手改，它是脚本自动产物。

#### `assets/js/photo-data.js`
自动生成出来的照片数据文件。

这里也不用手动改。

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

> 把图片丢进 `photo/` 文件夹。

然后脚本会自动：

- 按文件时间排序（新到旧）
- 读取图片宽高
- 读取文件大小
- 生成 `assets/js/photo-data.js`

也就是说，不需要再做这些事：

- 不需要手动给每张图编号
- 不需要手动写图片数组
- 不需要手动改照片墙 HTML
- 不需要手动改详情页链接

![照片目录](https://images.unsplash.com/photo-1516321497487-e288fb19713f?auto=format&fit=crop&w=1600&q=80)

---

## 五、文章系统是怎么自动工作的

文章系统现在的逻辑是：

> 把 `.md` 文件放进 `blog/posts/`。

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
cover: https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1600&q=80
pinned: false
---

# 我的第一篇文章

这里是正文。

![插图](https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=80)
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

如果没有文章置顶，页面默认会把**日期最新**的一篇文章放到首卡位置。

---

## 六、本地怎么生成内容

文件准备好以后，日常维护就很简单。

### 每次更新内容

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

```bash
python3 -m http.server 8080
```

然后打开：

<http://localhost:8080>

---

## 七、如何 push 到 GitHub

### 第一步：初始化 Git 仓库

```bash
git init
git branch -M main
```

### 第二步：连接 GitHub 仓库

GitHub 官网：<https://github.com/>

创建好仓库之后，把远程仓库连进来：

```bash
git remote add origin https://github.com/你的用户名/你的仓库名.git
```

### 第三步：提交并推送

```bash
git add .
git commit -m "Initial site setup"
git push -u origin main
```

之后日常更新只需要：

```bash
git add .
git commit -m "Update content"
git push origin main
```

---

## 八、如何通过 GitHub 自动发布

最省心的方式就是 **GitHub Pages**。

GitHub Pages：<https://pages.github.com/>

仓库里已经有：

```text
.github/workflows/deploy-pages.yml
```

当你 push 到 `main` 后，GitHub Actions 会自动：

1. 检出仓库
2. 运行 `python3 scripts/generate_posts.py`
3. 生成文章和照片数据
4. 自动部署到 GitHub Pages

GitHub Actions：<https://github.com/features/actions>

---

## 九、如何在 VPS 上搭建

想完全掌控环境，也可以放到 VPS 上。

### 常见 VPS 服务商

- Vultr：<https://www.vultr.com/>
- DigitalOcean：<https://www.digitalocean.com/>
- Linode：<https://www.linode.com/>
- Oracle Cloud Free Tier：<https://www.oracle.com/cloud/free/>

### 最常见的方法：Nginx 托管静态站

Nginx 官网：<https://nginx.org/>

流程很直接：

1. 把仓库 clone 到 VPS
2. 用 Nginx 指向网站目录
3. 配域名
4. 配 HTTPS

例如：

```bash
git clone https://github.com/你的用户名/你的仓库.git /var/www/love
cd /var/www/love
python3 scripts/generate_posts.py
```

Nginx 配置大概会像这样：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/love;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

---

## 十、如何接域名和 HTTPS

### GitHub Pages 路线

- [如何给这个站接自定义域名与 HTTPS](note.html?slug=custom-domain-https-guide)

### HTTPS 常用工具

- Let's Encrypt：<https://letsencrypt.org/>
- Certbot：<https://certbot.eff.org/>

如果是 Nginx 环境，最常见命令是：

```bash
sudo certbot --nginx -d your-domain.com
```

---

## 十一、这些网站和服务之间怎么联动

最常见的一条链路是：

```text
本地修改内容
   ↓
python3 scripts/generate_posts.py
   ↓
git push 到 GitHub
   ↓
GitHub Actions 自动运行
   ↓
GitHub Pages 自动发布
```

也可以是：

```text
本地修改内容
   ↓
git push 到 GitHub
   ↓
VPS 上 git pull
   ↓
Nginx 继续提供静态站
```

想继续往自动部署走，可以看：

- [如何让 VPS 自动 pull 并自动部署](note.html?slug=vps-auto-deploy-guide)
- [如何继续把它做成完整内容系统](note.html?slug=content-system-guide)

---

## 十二、后续维护

其实很少：

### 加照片时

```bash
# 1. 把图片丢进 photo/
# 2. 生成
python3 scripts/generate_posts.py
# 3. 提交

git add .
git commit -m "Add photos"
git push origin main
```

### 加文章时

```bash
# 1. 把 md 丢进 blog/posts/
# 2. 生成
python3 scripts/generate_posts.py
# 3. 提交

git add .
git commit -m "Add post"
git push origin main
```

### 改页面样式时

```bash
git add .
git commit -m "Refine layout"
git push origin main
```

---

## 十三、最简总结

从零开始时，路径可以很简单：

1. 本地建项目目录
2. 准备页面文件
3. 准备 `photo/`
4. 准备 `blog/posts/`
5. 准备自动生成脚本
6. 用 Git 管理
7. push 到 GitHub
8. 用 GitHub Pages 或 VPS 发布

这套方法的核心不在“某个框架”，而在这几点：

- 内容和页面分开
- 照片自动化
- 文章自动化
- 发布自动化

只要这四件事搭对了，你后面维护网站会轻松很多。

![内容站](https://images.unsplash.com/photo-1505238680356-667803448bb6?auto=format&fit=crop&w=1600&q=80)

## 关联网站

- GitHub：<https://github.com/>
- GitHub Pages：<https://pages.github.com/>
- GitHub Actions：<https://github.com/features/actions>
- Python：<https://www.python.org/>
- Git：<https://git-scm.com/>
- VS Code：<https://code.visualstudio.com/>
- Nginx：<https://nginx.org/>
- Let's Encrypt：<https://letsencrypt.org/>
- Certbot：<https://certbot.eff.org/>

## 补充栏目

- [如何给这个站接自定义域名与 HTTPS](note.html?slug=custom-domain-https-guide)
- [如何让 VPS 自动 pull 并自动部署](note.html?slug=vps-auto-deploy-guide)
- [如何继续把它做成完整内容系统](note.html?slug=content-system-guide)
