# Phicomm M1 → WeCom

斐讯 M1 原厂固件的最小接收服务：接收温湿度、PM2.5、甲醛数据，回复心跳，提供最小激活接口，并发送企业微信异常/恢复/定时报告。

## 安全说明

- 不要把 Wi-Fi 密码、SSH 密码或 Webhook key 提交到仓库。
- `m1-aircat.env.example` 只含占位符；真实文件应放在服务器 `/etc/m1-aircat.env` 并设为 `0600`。
- 示例为了兼容原厂设备在独立的 443 监听器上启用了 TLS 1.0；不要把它用于普通网站。
- 9000/443 端口应通过防火墙尽量限制来源。

## 安装

```bash
sudo useradd --system --home /var/lib/m1-aircat --shell /usr/sbin/nologin m1-aircat
sudo install -d -o m1-aircat -g m1-aircat /opt/m1-aircat /var/lib/m1-aircat
sudo install -m 0755 server.py /opt/m1-aircat/server.py
sudo install -m 0644 m1-aircat.service /etc/systemd/system/m1-aircat.service
sudo install -m 0600 m1-aircat.env.example /etc/m1-aircat.env
```

生成仅供 M1 假云端使用的证书：

```bash
sudo openssl req -x509 -newkey rsa:2048 -sha256 -days 3650 -nodes \
  -subj '/CN=aircat.phicomm.com' \
  -keyout /opt/m1-aircat/cloud.key \
  -out /opt/m1-aircat/cloud.crt
sudo chown -R m1-aircat:m1-aircat /opt/m1-aircat /var/lib/m1-aircat
```

编辑 `/etc/m1-aircat.env` 后启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now m1-aircat
sudo journalctl -u m1-aircat -f
```

最后在 M1 使用的 DNS 网关中，将 `aircat.phicomm.com` 映射到服务器地址。原厂设备会连接 TCP 9000，并通过 HTTPS 443 请求激活。
