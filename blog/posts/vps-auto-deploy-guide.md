---
title: 如何让 VPS 自动 pull 并自动部署
date: 2026-03-16
summary: 如果你已经有 VPS，这篇文章讲如何把 GitHub、Webhook、脚本和 Nginx 串起来，让更新真正自动化。
cover: https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80
---

# 如何让 VPS 自动 pull 并自动部署

![VPS 自动部署示意](https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80)

很多人一开始都是本地 push，登录 VPS，再手动 `git pull`。这当然能用，但时间一长就会想把最后一步也自动化。

## 最简单的思路

```text
本地 push
  ↓
GitHub Actions / Webhook 触发
  ↓
VPS 拉取最新代码
  ↓
重新生成内容
  ↓
Reload Nginx
```

## 常见实现方式

### 方案 1：GitHub Actions SSH 到 VPS

适合大多数人，链路直观。

- GitHub Actions：<https://github.com/features/actions>
- 通过 SSH 执行远程命令

### 方案 2：Webhook + 自己的部署脚本

适合更想自己掌控流程的人。

## VPS 上的最小部署脚本示意

```bash
cd /var/www/love
git pull origin main
python3 scripts/generate_posts.py
sudo systemctl reload nginx
```

真正稳定的关键不是脚本有多花，而是：

- 路径固定
- 权限清楚
- 失败时能看到日志
