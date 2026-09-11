---
title: 如何从零搭建 OpenClaw 并接入 Telegram
date: 2026-03-14
summary: 从运行环境、Gateway 和 Telegram Bot 到权限、日志与故障排查，先建立稳定的最短链路。
cover: https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1600&q=80
---

# 如何从零搭建 OpenClaw 并接入 Telegram

![OpenClaw](https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=1600&q=80)

搭建这类个人智能助手时，最容易犯的错误是第一天就接入所有模型、消息通道、记忆和自动化。更稳的路线是先完成一条最短链路：模型能回应，Gateway 稳定运行，Telegram 能收发，再逐层增加能力。

> OpenClaw 的安装命令和配置字段可能随版本变化。执行前请以项目当前 README 与发布说明为准，不要直接复制来源不明的一键脚本。

## 准备环境

使用项目支持的 Node.js 版本，确认 `node`、`npm` 和 Git 可用。单独创建工作目录和运行用户，不要用 root 长期启动服务。模型 API Key、Telegram Bot Token 等机密放在环境变量或权限受控的配置文件中，绝不提交到公开仓库。

## 先完成本地对话

安装后运行官方初始化或 onboard 流程，只配置一个模型提供方。先在本地确认：

- 能连续正常回复
- 超时与配额错误有明确日志
- 工作目录具有正确读写权限
- 重启后配置仍能加载

模型层不稳定时，继续排查 Telegram 只会让变量更多。

## 启动 Gateway

Gateway 应由 systemd、launchd 或容器重启策略托管，而不是依赖一个终端窗口。绑定地址优先限制在本机或局域网；需要远程访问时使用 VPN 或有认证的反向代理，不要直接把管理端口暴露到公网。

为日志设置轮转，记录启动时间、版本和主要错误，但避免把完整 token、用户消息或敏感文件内容写进日志。

## 接入 Telegram

通过 BotFather 创建机器人并取得 token，再按项目文档配置消息通道。第一次只允许自己的 chat ID，确认私聊链路后再考虑群聊。

如果机器人不回复，按顺序检查：

1. token 是否正确且未泄露；
2. Gateway 是否在运行；
3. 服务器能否访问 Telegram API；
4. polling 与 webhook 是否重复启用；
5. chat ID 或允许列表是否匹配；
6. 模型调用是否超时或被限流。

若 token 曾出现在公开日志或截图中，应立即在 BotFather 重新生成。

## 再增加记忆、工具和自动化

每增加一项能力，都明确它能读取什么、能写入什么、是否需要人工确认。文件删除、外部消息发送和系统命令属于高风险操作，默认应限制范围并保留审计记录。

先稳定运行几天，再逐步接入记忆、定时任务和更多通道。一个能力较少但边界清楚的助手，远比权限无限却难以排错的系统可靠。

## 参考资料

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Node.js 安全最佳实践](https://nodejs.org/en/learn/getting-started/security-best-practices)
