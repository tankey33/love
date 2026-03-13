# Blog Posts

把新的 `.md` 文件直接放进这个目录，然后 push 到 GitHub 即可自动上线。

## 最简格式

```md
---
title: 文章标题
date: 2026-03-13
summary: 一句话摘要
---

# 正文标题

这里写正文。
```

## 已自动完成的事

当你 push 到 `main` 后，GitHub Actions 会自动：

1. 生成 `blog/posts.json`
2. 预渲染文章为 `blog/rendered/*.html`
3. 部署到 GitHub Pages

## 支持内容

- 标题
- 段落
- 列表
- 引用
- 代码块
- 表格
- 图片
- 行内代码
- 粗体 / 斜体

## 图片写法

```md
![说明文字](photo/03.jpg)
```
