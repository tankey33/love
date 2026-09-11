---
title: 如何给这个站接自定义域名与 HTTPS
date: 2026-03-16
summary: 从域名解析、CNAME、GitHub Pages 到 Nginx 与 Let's Encrypt，把域名和 HTTPS 接入过程完整梳理一遍。
cover: https://images.unsplash.com/photo-1484417894907-623942c8ee29?auto=format&fit=crop&w=1600&q=80
---

# 如何给这个站接自定义域名与 HTTPS

![域名与 HTTPS 配置](https://images.unsplash.com/photo-1484417894907-623942c8ee29?auto=format&fit=crop&w=1600&q=80)

网站能通过临时地址打开，只代表部署成功；拥有稳定的自定义域名、全站 HTTPS 和明确的跳转规则，才算真正进入长期使用状态。

## 先决定由谁提供页面

如果网站部署在 GitHub Pages，DNS 应指向 GitHub Pages，并在仓库 Pages 设置中绑定域名。如果页面实际由 VPS 上的 Nginx 提供，DNS 就应该指向 VPS 公网地址。不要让同一个主机名同时承担两套互相竞争的解析。

还要先选定主域名，例如使用 `love.example.com`，还是使用根域名 `example.com`。其他入口统一 301 跳转到主域名，搜索引擎和浏览器缓存都会更清楚。

## GitHub Pages 的配置

子域名通常添加 CNAME 记录，指向 `用户名.github.io`；根域名则按 GitHub 官方文档设置 A/AAAA 或 ALIAS/ANAME。仓库根目录保留一个 `CNAME` 文件，内容只写域名本身：

```text
love.example.com
```

然后在仓库的 Settings → Pages 中填写同一域名。DNS 生效可能需要时间，可用 `dig` 或公共 DNS 检查工具确认实际解析结果。

GitHub 建议验证自定义域名，以降低域名被其他仓库错误占用的风险。绑定完成后再开启 Enforce HTTPS；证书签发期间反复删除和添加域名，反而可能让验证重新排队。

## VPS 与 Nginx 的配置

将域名 A 记录指向 VPS IPv4 地址，如使用 IPv6 再增加 AAAA。Nginx 先提供纯 HTTP 站点，确认域名和站点目录无误：

```nginx
server {
    listen 80;
    server_name love.example.com;
    root /var/www/love;
    index index.html;
}
```

确认可以访问后，再使用 Certbot 申请 Let's Encrypt 证书：

```bash
sudo certbot --nginx -d love.example.com
```

Certbot 通常会写入证书路径和 HTTP 到 HTTPS 的跳转。之后用 `sudo certbot renew --dry-run` 检查自动续期是否正常。

## HTTPS 生效后还要检查什么

浏览器出现小锁并不代表配置已经完整。还应检查：

- 所有 HTTP 入口是否永久跳转到 HTTPS
- 页面中的图片、脚本和字体是否仍通过 HTTP 加载
- `www` 与非 `www`、旧域名与新域名是否统一
- 证书是否覆盖当前使用的全部主机名
- DNS 是否残留错误的 AAAA 或旧 CDN 记录
- 页面是否设置唯一的 canonical 地址

混合内容是最常见问题：页面本身是 HTTPS，但某张图片仍是 HTTP，浏览器会阻止加载或降低安全等级。

## 常见故障的排查顺序

先查 DNS，再查服务器监听端口，然后查证书，最后查浏览器缓存。DNS 未生效时，修改 Nginx 没有意义；证书域名不匹配时，清缓存也解决不了。

```bash
dig love.example.com
curl -I http://love.example.com
curl -I https://love.example.com
sudo nginx -t
```

每一步只回答一个问题，排查会比不断重装证书更快。

## 参考资料

- [GitHub：配置 Pages 自定义域名](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)
- [GitHub：保护自定义域名](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages)
- [Let's Encrypt](https://letsencrypt.org/)
- [Certbot](https://certbot.eff.org/)
