# 人类使用说明书 — Ubuntu 22.04 Docker 部署指南

## 前提

阿里云 ECS Ubuntu 22.04，SSH 已登录。安全组放行 **8000 端口**。

## 从零部署（4步）

```bash
# 1. 安装 Docker（官方脚本一键搞定）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 2. 克隆项目
git clone https://github.com/xiaolonglong67/human-manual.git
cd human-manual

# 3. 设置 Key 并启动（替换为你的真实 Key）
echo 'DEEPSEEK_API_KEY=你的DeepSeek API Key' > .env
docker compose up -d --build

# 4. 验证
curl http://localhost:8000/api/health
# 返回 {"status":"ok"} 即成功
```

## 更新部署

```bash
cd human-manual
git pull
docker compose up -d --build
```

## 常用命令

```bash
docker compose logs -f     # 实时日志
docker compose restart     # 重启
docker compose down        # 停止
```

## 访问

浏览器打开 `http://<ECS公网IP>:8000`

> ⚠️ 阿里云控制台 → 安全组 → 添加规则 → **入方向 TCP 8000** 放行
