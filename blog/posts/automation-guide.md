---
title: 如何做一个自动更新的照片墙和博客系统
date: 2026-03-12
summary: 这篇文章专门讲自动化本身：照片目录、Markdown、生成脚本、自动索引、自动渲染、自动部署是怎么串起来的。
cover: https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1600&q=80
---

# 如何做一个自动更新的照片墙和博客系统

![自动化内容系统示意](https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1600&q=80)

如果你希望未来维护网站时不要每次都手改 HTML，那最重要的不是页面好不好看，而是**自动化链路有没有搭好**。

## 这套自动化的核心

### 照片自动化

- 图片只放进 `photo/`
- 脚本自动扫描
- 自动读取尺寸、时间、大小
- 自动生成 `photo-data.js`

### 文章自动化

- 文章只放进 `blog/posts/`
- 用 front matter 写标题、摘要、日期、封面、置顶
- 自动生成文章索引
- 自动渲染成文章页可用 HTML

## 内容链路

```text
photo/ -> 生成照片数据 -> 照片墙 / 详情页
blog/posts/ -> 生成文章数据 -> 列表页 / 单篇文章页
```

## 部署链路

```text
本地修改内容
   ↓
python3 scripts/generate_posts.py
   ↓
git push
   ↓
GitHub Actions 自动发布
```

## 这套方法的好处

- 几乎不需要重复劳动
- 内容和页面逻辑分开
- 以后扩展标签、搜索、置顶都更容易
- 很适合长期维护

如果你要做的是一个既有相册又有文字内容的小站，这种思路比纯手工页面靠谱得多。
