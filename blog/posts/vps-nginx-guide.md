---
title: 如何把这个网站部署到 VPS 与 Nginx
date: 2026-03-13
summary: 如果你想完全掌控环境，这篇文章会从 VPS 选择、Nginx 配置、域名解析到 HTTPS 一步步讲清楚。
cover: https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=80
---

# 如何把这个网站部署到 VPS 与 Nginx

![VPS 与 Nginx 示意](https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=80)

如果你不想只依赖 GitHub Pages，而是希望自己掌控部署环境，那 VPS + Nginx 是最经典也最稳定的做法。

## 你需要准备

- 一台 VPS
- 一个域名
- Nginx
- 网站代码仓库

## 常见 VPS 服务商

- Vultr：<https://www.vultr.com/>
- DigitalOcean：<https://www.digitalocean.com/>
- Linode：<https://www.linode.com/>
- Oracle Cloud Free Tier：<https://www.oracle.com/cloud/free/>

## 第一步：把代码拉到服务器

```bash
git clone https://github.com/你的用户名/你的仓库.git /var/www/love
cd /var/www/love
python3 scripts/generate_posts.py
```

## 第二步：安装 Nginx

Nginx 官网：<https://nginx.org/>

大多数 Debian / Ubuntu 系系统可以直接：

```bash
sudo apt update
sudo apt install nginx -y
```

## 第三步：写站点配置

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

写完后启用配置并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 第四步：绑定域名

把域名的 A 记录解析到你的 VPS IP。

## 第五步：开启 HTTPS

Let's Encrypt：<https://letsencrypt.org/>

Certbot：<https://certbot.eff.org/>

```bash
sudo certbot --nginx -d your-domain.com
```

## 日常更新怎么做

最简单的方法就是：

```bash
cd /var/www/love
git pull origin main
python3 scripts/generate_posts.py
sudo systemctl reload nginx
```

如果你想更自动化，也可以下一步接 GitHub Actions 自动 ssh 部署。
