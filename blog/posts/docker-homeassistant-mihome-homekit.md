---
title: 用 Docker 搭建 Home Assistant，并连接米家与 HomeKit
date: 2026-03-13
summary: 如果你想把智能家居做成一套真正好用的系统，Home Assistant 仍然是最值得投入时间的一环。
cover: https://images.unsplash.com/photo-1491927570842-0261e477d937?auto=format&fit=crop&w=1600&q=80
---

# 用 Docker 搭建 Home Assistant，并连接米家与 HomeKit

![Home Assistant 示意](https://images.unsplash.com/photo-1491927570842-0261e477d937?auto=format&fit=crop&w=1600&q=80)

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

## 真正有价值的不是接入，而是场景

很多人把时间花在“设备有没有加进去”，但真正提升体验的是场景：

- 回家自动亮灯
- 夜里自动调暗
- 离家自动关闭部分设备
- 卧室和客厅分区控制

当这些细节慢慢稳定下来，家里的自动化才会真正像系统而不是玩具。

## 连接时的建议

- 尽量先接最核心的设备
- 不要第一天把所有自动化都写满
- 先保证稳定，再慢慢优化细节
