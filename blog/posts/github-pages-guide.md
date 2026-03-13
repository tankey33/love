---
title: 如何把这个网站部署到 GitHub Pages
date: 2026-03-14
summary: 从仓库创建、Pages 设置、Actions 自动发布到自定义域名接入，这篇文章专门讲 GitHub Pages 这一条路。
cover: https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1600&q=80
---

# 如何把这个网站部署到 GitHub Pages

![GitHub Pages 部署示意](https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1600&q=80)

如果你想要一种**最省事、最轻量、最适合静态站**的上线方式，那么 GitHub Pages 基本是第一选择。

## 你需要准备什么

- 一个 GitHub 账号：<https://github.com/>
- 一个仓库
- 网站代码
- （可选）自己的域名

## 第一步：创建仓库

登录 GitHub 后新建一个 repository。

如果你还没注册，可以从这里开始：<https://github.com/signup>

创建完成后，把本地项目连接上去：

```bash
git init
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库.git
```

## 第二步：push 代码

```bash
git add .
git commit -m "Initial site"
git push -u origin main
```

## 第三步：打开 GitHub Pages

GitHub Pages 官方说明：<https://pages.github.com/>

如果你已经配置好 `.github/workflows/deploy-pages.yml`，那网站 push 后会由 GitHub Actions 自动构建并部署。

GitHub Actions：<https://github.com/features/actions>

## 第四步：检查自动部署

每次你 push 到 `main`，它会自动：

- 生成文章索引
- 生成照片数据
- 渲染文章 HTML
- 发布到 Pages

## 第五步：绑定自定义域名（可选）

如果你有自己的域名，可以在仓库根目录放一个 `CNAME` 文件，并在域名 DNS 面板中把记录指向 Pages。

GitHub 域名文档：<https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site>

这样，一套静态网站就能低成本、长期稳定地跑起来。
