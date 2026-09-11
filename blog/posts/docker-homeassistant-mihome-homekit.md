---
title: 用 Docker 搭建 Home Assistant，并连接米家与 HomeKit
date: 2026-03-13
summary: 从容器部署、网络模式和数据备份，到米家设备接入与 HomeKit Bridge 配对，完整梳理家庭智能中枢的搭建思路。
cover: https://images.unsplash.com/photo-1491927570842-0261e477d937?auto=format&fit=crop&w=1600&q=80
---

# 用 Docker 搭建 Home Assistant，并连接米家与 HomeKit

![Home Assistant](https://images.unsplash.com/photo-1491927570842-0261e477d937?auto=format&fit=crop&w=1600&q=80)

Home Assistant 的意义不是再增加一个控制 App，而是把原本割裂的设备状态与家庭动作放进同一套逻辑：米家负责丰富的设备生态，Apple 家庭提供家人更熟悉的入口，Home Assistant 在中间完成整合与自动化。

## 先理解 Docker 方案的边界

Home Assistant Container 适合已经会维护 Docker 的用户，升级和迁移清楚，但不包含 Home Assistant OS 的 Supervisor 与应用商店。需要额外服务时，要用独立容器部署，而不是期待在界面里一键安装。

一个常见 Compose 配置如下：

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: homeassistant
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    environment:
      TZ: Asia/Shanghai
```

局域网发现依赖 mDNS、SSDP 等协议，Linux 主机常使用 host 网络模式。其他平台的 Docker 网络行为可能不同，应以 Home Assistant 官方安装说明为准。

## 第一次启动后先做基础工作

先设置固定局域网地址、时区和备份，再逐个添加核心设备。不要第一天就接入全部设备和自动化，否则出现离线或实体重复时很难判断问题来自哪一层。

`config` 目录包含系统配置与数据库，应定期备份。更新前查看破坏性变更，并保留可回退的镜像版本。

## 接入米家设备

米家并不是一个完全统一的本地协议生态。不同设备可能通过 Xiaomi Miio、Xiaomi BLE、Matter 或厂商云端集成进入 Home Assistant，支持的实体和稳定性也不同。

优先采用 Home Assistant 官方集成与设备本地控制；需要账号或 token 的集成，应单独保管凭据。设备在米家 App 中可用，不代表一定能以同样能力进入 Home Assistant，购买前最好查询具体型号的兼容情况。

## 接入 Apple 家庭

HomeKit Bridge 可以把 Home Assistant 中的实体桥接到 Apple 家庭。启用集成后，使用家庭 App 扫描配对码，再按房间整理设备。

不要一次暴露数百个实体。先筛选灯、开关、传感器和空调等家人真正需要控制的对象，隐藏诊断实体与重复入口。桥接对象过多时可按设备类型拆分多个 Bridge，故障隔离会更清楚。

HomeKit Device 与 HomeKit Bridge 容易混淆：前者是把 HomeKit 设备接入 Home Assistant，后者是把 Home Assistant 实体送到 Apple 家庭。

## 自动化应该围绕生活动作

比较值得先做的场景有：

- 日落后有人回家，打开玄关低亮度照明
- 夜间起床，仅点亮不刺眼的路径灯
- 全家离家后关闭不必要设备，并检查门窗
- 入睡后降低提醒频率，空调按温湿度调整
- 设备连续离线或传感器异常时发送通知

关键是加入条件、延时和人工覆盖。自动化不应与墙壁开关争夺控制权，也不要让一次网络波动触发全屋状态变化。

## 稳定性的几个原则

把照明和门锁等关键功能保留实体控制；给 IoT 设备划分独立网络时，提前处理跨 VLAN 的发现协议；定期检查失效实体和日志；发生故障时从设备、集成、Home Assistant、HomeKit 四层逐级排查。

智能家居真正成熟的标志不是设备数量，而是家里人不需要理解背后的平台，也能自然地开灯、回家和睡觉。

## 参考资料

- [Home Assistant Container](https://www.home-assistant.io/installation/)
- [HomeKit Bridge 集成](https://www.home-assistant.io/integrations/homekit/)
- [Xiaomi Miio 集成](https://www.home-assistant.io/integrations/xiaomi_miio/)
