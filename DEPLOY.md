# 人类使用说明书 — 阿里云 ECS Docker 部署指南

## 前提

阿里云 ECS 免费试用已领取，SSH 已能登录。

## 第一次部署

```bash
# 1. 安装 Docker（CentOS / Alibaba Cloud Linux）
sudo dnf install -y docker || sudo yum install -y docker
sudo systemctl enable docker --now

# 2. 在服务器上克隆项目
git clone https://github.com/xiaolonglong67/human-manual.git
cd human-manual

# 3. 设置 API Key（替换为你的真实 Key）
echo 'DEEPSEEK_API_KEY=你的DeepSeek API Key' > .env

# 4. 启动
docker compose up -d --build

# 5. 验证
curl http://localhost:8000/api/health
```

## 更新部署

```bash
cd human-manual
git pull
docker compose up -d --build
```

## 常用命令

```bash
docker compose logs -f          # 查看日志
docker compose restart          # 重启
docker compose down             # 停止
```

## 访问

浏览器打开 `http://<你的ECS公网IP>:8000`

⚠️ 阿里云安全组里放行 8000 端口（入方向）
