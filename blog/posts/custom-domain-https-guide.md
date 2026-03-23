---
title: 如何给这个站接自定义域名与 HTTPS
date: 2026-03-16
summary: 从域名解析、CNAME、Nginx 到 Let's Encrypt，把域名与 HTTPS 的接入流程整理清楚。
cover: https://images.unsplash.com/photo-1484417894907-623942c8ee29?auto=format&fit=crop&w=1600&q=80
---

# 如何给这个站接自定义域名与 HTTPS

![域名与 HTTPS 配置](https://images.unsplash.com/photo-1484417894907-623942c8ee29?auto=format&fit=crop&w=1600&q=80)

一个网站从“能打开”到“像真的在运行”，域名和 HTTPS 几乎是必须补上的两步。

## GitHub Pages

1. 在仓库根目录放 `CNAME`
2. 在域名服务商后台把 DNS 指向 GitHub Pages
3. 到仓库 Pages 设置页确认域名生效

官方文档：<https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site>

## VPS + Nginx

1. 把域名 A 记录解析到 VPS IP
2. 在 Nginx 里配置 `server_name`
3. 申请证书并开启 HTTPS

Let's Encrypt：<https://letsencrypt.org/>

Certbot：<https://certbot.eff.org/>

最常见的命令：

```bash
sudo certbot --nginx -d your-domain.com
```

## 最后检查

- `http://` 是否自动跳转到 `https://`
- 证书是否正常
- 图片、脚本、字体资源是否还有混合内容错误
