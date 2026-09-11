---
title: 如何让 VPS 自动 pull 并自动部署
date: 2026-03-16
summary: 把 GitHub Actions、SSH、部署脚本和 Nginx 串起来，同时做好权限、日志、回滚和并发控制。
cover: https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80
---

# 如何让 VPS 自动 pull 并自动部署

![VPS](https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80)

手动登录 VPS 再执行 `git pull` 很直观，但它依赖记忆，也很难留下完整记录。自动部署的目的不是少敲一条命令，而是把“什么版本、何时发布、失败在哪里、怎样回退”变得可追踪。

## 推荐链路

```text
push 到 main
→ GitHub Actions 运行检查
→ 通过 SSH 调用 VPS 部署脚本
→ 在临时目录构建
→ 原子切换当前版本
→ 健康检查
→ 成功后清理旧版本
```

简单静态站也可以直接在 GitHub Pages 构建，不必额外维护 VPS。只有需要自定义服务、反向代理或服务器端任务时，才值得增加 VPS 这一层。

## VPS 端部署脚本

不要让 Actions 拼接一长串远程命令。把流程放在 VPS 的固定脚本中，更容易审计和本地测试：

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR=/var/www/love
cd "$APP_DIR"

git fetch origin main
git reset --hard origin/main
python3 scripts/generate_posts.py
sudo nginx -t
sudo systemctl reload nginx
```

如果目录里存在服务器独有文件，`reset --hard` 会覆盖它们，因此配置和机密应放到仓库外，并在执行前明确工作目录。更完善的做法是每次部署到带提交号的新目录，检查成功后更新 `current` 软链接。

## GitHub Actions 端

SSH 私钥、主机地址和用户名放进仓库 Secrets，不要提交到代码。服务器上建立专用部署用户，只授予目标目录和必要命令权限。SSH 主机指纹应预先写入 `known_hosts`，避免关闭主机校验。

工作流还应设置 concurrency，防止连续 push 触发两个部署互相覆盖。只有 main 分支通过检查后才允许发布。

## 日志、失败与回滚

至少保留这几项：

- Actions 的构建与连接日志
- VPS 部署脚本的时间、提交 SHA 和退出码
- Nginx 配置检查结果
- 发布后的 HTTP 状态检查
- 最近几个可回退版本

部署失败时不要继续 reload，更不要删除当前可用版本。健康检查可以用 `curl --fail https://example.com/`，确认主要页面能返回后再宣布成功。

## Webhook 方案何时使用

自建 Webhook 接收器响应更快，也不依赖 Actions SSH，但必须验证 GitHub 签名、限制请求体、避免把分支名直接拼进 shell，并处理重复事件。对个人静态站而言，Actions 通常更简单、安全边界也更清楚。

自动部署真正值得做的，不是让每次发布看起来很酷，而是让错误更难进入线上，让回滚不再靠临时回忆。

## 参考资料

- [GitHub Actions](https://docs.github.com/actions)
- [GitHub Actions 中使用机密](https://docs.github.com/actions/security-guides/using-secrets-in-github-actions)
- [验证 GitHub Webhook](https://docs.github.com/webhooks/using-webhooks/validating-webhook-deliveries)
