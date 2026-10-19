# Tankey & Monody · 我们的纪念册

纯静态纪念站，使用 GitHub Pages 发布，Cloudflare Access 保护独立的内容管理后台。不需要前端框架。

## 页面与源码

- `index.html`：共同时间、周年纪念日、往年今日。
- `photo.html`：自适应照片墙与可分享的大图查看器。
- `notes.html` / `note.html`：手记目录与文章。
- `movie.html` / `music.html`：电影、音乐收藏与榜单。
- `timeline.html`：由真实拍摄日期和手记串起的年表。
- `assets/css/tokens.css`：日间、夜间主题变量；`base.css`：共享组件；其余 CSS 按页面划分。
- `assets/js/theme.js`：主题选择、音乐状态与安装离线功能。其余脚本各自管理页面。
- `photo/`：照片源文件和同名 JSON 资料。公开当前版本也必须脱敏。
- `blog/posts/`：Markdown 手记；`blog/rendered/` 与 `blog/posts.json` 由构建生成。
- `scripts/prepare_photos.py`：移除敏感嵌入信息，生成公开图片和三档 WebP 缩略图。
- `scripts/generate_posts.py`：生成文章与标准 JSON 照片索引。
- `scripts/build_site.py`：仅组装公开文件，自动生成内容哈希和分享元信息。
- `admin-worker/`：上传、去重、压缩进度、文章管理；仅部署到独立管理域名。

## 本地预览

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python scripts/prepare_photos.py
.venv/bin/python scripts/generate_posts.py
.venv/bin/python scripts/build_site.py
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory _site
```

打开 `http://127.0.0.1:8765`。每次构建重新生成 `_site/`；不向其中手工编辑内容。

## 新增照片

推荐使用受 Access 保护的管理后台。后台先读取原始照片资料，再压缩和上传；同名 JSON 保留拍摄日期、相机、镜头、光圈、快门等。只有原文件确实含有的信息才会显示。

实况照片须同时提供同名静态图和 MOV/MP4，例如 `IMG_1234.HEIC` 与 `IMG_1234.MOV`。HEIC 会先转换。浏览器的“照片”选择器有时只提供静态图，不能凭空恢复实况视频；可改从“文件”选择成对文件。重复静态图会跳过，后来补传的同名实况视频仍会绑定。

直接将照片放进 `photo/` 也可触发构建，但公开仓库内的原始位置资料同样会公开。提交前先备份，再执行：

```sh
.venv/bin/python scripts/prepare_photos.py --sanitize-source
```

此操作只修改当前文件，不清理 Git 历史。JPEG 不重复压缩，允许公开的拍摄资料保存在同名 JSON。

位置默认隐藏。仅在明确希望展示的旅行照片旁车文件中设置：

```json
{"isTravel": true, "shareLocation": true, "city": "旅行城市"}
```

即使公开位置，也仅发布到约 `0.1°` 范围。`"hideLocation": true` 始终优先。更多说明见 `PRIVACY.md`。

## 手记与时间线

新增 `blog/posts/文章地址.md`，在头部写 `title`、`date`、`summary`；使用现有文章作为模板。也可通过后台编辑发布。

时间线仅显示已有真实日期记录。新增共同里程碑时编辑 `data/milestones.json`，不要把照片上传日期误写为事件发生日期。

## 发布与缓存

仓库 Settings → Pages → Build and deployment → Source 必须选择 **GitHub Actions**，不要同时使用旧的分支发布，避免未构建源码覆盖处理后的照片墙。电影音乐榜单定时或手动刷新，不阻塞每次照片上传。

推送 main、后台发布或定时更新触发 `.github/workflows/deploy-pages.yml`。工作流安装 Pillow，准备脱敏图片，生成索引和文章，然后把 `_site/` 发布到 Pages。`.git`、后台源码、构建脚本、未脱敏源目录不进入网站制品。

照片 JSON 使用带内容哈希的文件名，CSS/JS 版本由构建内容决定，不再手工改日期。照片索引使用 HTTP 验证缓存，浏览器无需每次完整下载。PWA 只缓存已访问的页面和最近的图片，缓存有数量上限；不预下载整个相册或音频。

## 音乐与浏览器限制

背景曲目来自 `music/white.mp3`，界面按文件名显示 White。播放开关、音量和位置保存在本机；跨页尝试从原位置续播。浏览器可能要求再次轻点播放，因此静态多页站无法承诺音频始终无缝。首页空白处连续三次点击播放、连续两次点击暂停，音乐按钮单击切换。

## 备份与存储

2026-10-19 优化前版本为 `0c3dc89c6ae5019608d941cb028810988f0b34ad`。独立 ZIP、完整 Git bundle 与校验信息保存在本机 `Documents/Codex/backups/`。原始私密备份不应提交回公开仓库。

缩略图仅在构建时生成，不回写 Git，避免继续扩大历史。大规模相册可迁移到私有 R2 桶并使用受控公开域名；迁移需要确定桶、域名和访问策略，已有代码不自动创建付费服务。Git LFS 不是脱敏措施，也不能清理旧提交。
