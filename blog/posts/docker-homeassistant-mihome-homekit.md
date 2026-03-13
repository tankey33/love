---
title: 用 Docker 搭建 Home Assistant，并连接米家与 HomeKit
date: 2026-03-13
summary: 如果你想把智能家居做成一套真正好用的系统，Home Assistant 仍然是最值得投入时间的一环。
cover: https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=1600&q=80
---

# 用 Docker 搭建 Home Assistant，并连接米家与 HomeKit

![Home Assistant 示意](https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=1600&q=80)

如果你想把智能家居做成一套真正好用的系统，Home Assistant 仍然是最值得投入时间的一环。它最大的意义不是“可玩”，而是把本来割裂的设备放进一套可控逻辑里。

## 为什么是 Docker

因为：

- 部署简单
- 迁移方便
- 更新更清晰
- 不容易把系统环境弄乱

## 米家和 HomeKit 怎么理解

通常可以这样看：

- 米家：设备生态丰富，性价比高
- HomeKit：交互体验更好，家里人更容易上手
- Home Assistant：负责把两边串起来

这也是很多家庭最后都会走到的一条路。
