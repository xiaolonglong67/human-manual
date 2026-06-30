# 🧠 人类使用说明书

> 你的私人微信外脑 —— 记录朋友的偏好、习惯、忌口，随时查询。

---

## 🏗 系统架构

```
微信消息 ←→ Gewechat (Docker) ←→ chatgpt-on-wechat ←→ DeepSeek API
                                                    ↕
                                              SQLite 本地数据库
```

---

## 📋 前置准备

| 软件 | 用途 | 下载 |
|------|------|------|
| **VS Code** | 代码编辑 + Claude Code 助手 | https://code.visualstudio.com/ |
| **Python 3.8+** | 运行 chatgpt-on-wechat | https://www.python.org/downloads/ |
| **Docker Desktop** | 运行 Gewechat 微信协议服务 | https://www.docker.com/products/docker-desktop/ |
| **DeepSeek API Key** | 大模型调用 | https://platform.deepseek.com/ |

---

## 🚀 从零到一：完整部署流程

### 第一步：启动 Gewechat（微信协议层）

```powershell
# 进入本项目目录
cd D:\Desktop\human-manual

# 拉取镜像并启动
docker compose up -d
```

验证：浏览器访问 `http://127.0.0.1:2531/v2/api`，看到返回内容即表示成功。

---

### 第二步：克隆 chatgpt-on-wechat

```powershell
# 回到 Desktop
cd D:\Desktop

# 克隆官方仓库
git clone https://github.com/zhayujie/chatgpt-on-wechat.git

# 进入目录
cd chatgpt-on-wechat

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-optional.txt
```

---

### 第三步：配置

**3.1 复制配置文件**

```powershell
# 将本项目的 config.json 复制到 chatgpt-on-wechat 目录
copy D:\Desktop\human-manual\config.json D:\Desktop\chatgpt-on-wechat\config.json
```

**3.2 修改 config.json 中的 API Key**

打开 `D:\Desktop\chatgpt-on-wechat\config.json`，把 `open_ai_api_key` 改为你的 DeepSeek API Key：

```json
{
  "open_ai_api_key": "sk-xxxxxxxxxxxxxxxx",
  ...
}
```

**3.3 安装插件**

```powershell
# 方式一：复制插件目录
copy -Recurse D:\Desktop\human-manual\plugins\human_manual D:\Desktop\chatgpt-on-wechat\plugins\human_manual

# 方式二：符号链接（推荐，修改插件后无需重新复制）
New-Item -ItemType SymbolicLink -Path "D:\Desktop\chatgpt-on-wechat\plugins\human_manual" -Target "D:\Desktop\human-manual\plugins\human_manual"
```

---

### 第四步：启动 Bot

```powershell
cd D:\Desktop\chatgpt-on-wechat
python app.py
```

控制台输出中会看到：
```
[HumanManual] 人类说明书——记录和查询朋友的偏好与习惯
```
这表示插件已成功加载。

**首次运行时**，控制台会输出 `gewechat_app_id` 和 `gewechat_token`。记下这两个值，填入 `config.json` 中对应字段，然后重启 `python app.py`。

---

### 第五步：扫码登录

启动后，控制台会显示一个二维码。用你的微信小号扫码登录（建议用小号，以免主号被封）。

---

## 📱 使用指南

### 记录说明书

```
记录说明书：张三，不吃香菜，喜欢辣的，生日是5月12日，每天早上6点起床
```

AI 会自动解析并结构化存储。回复：
```
✅ 已为「张三」创建说明书！
```

多次记录同一人物会智能合并信息：

```
记录说明书：张三，性格内向但很细心，最喜欢的颜色是蓝色
```

回复：
```
✅ 已更新「张三」的说明书！
```

### 查询说明书

```
查询说明书：张三
```

回复：
```
📋 【张三的使用说明书】
🍽 饮食偏好：不吃香菜；喜欢辣的
🔄 生活习惯：每天早上6点起床
📅 重要日期：生日：5月12日
🧠 性格特点：内向；细心
📝 备注：最喜欢的颜色是蓝色
```

### 查看全部记录

```
说明书列表
```

回复：
```
📚 【已记录的说明书】
  1. 张三（阿张）
  2. 李四

共 2 条记录。发送「查询说明书：姓名」查看详情。
```

---

## 🛠 目录结构

```
human-manual/
├── README.md                    # 本文件
├── .gitignore                   # Git 忽略规则
├── docker-compose.yml           # Gewechat 一键启动
├── config.json                  # Bot 配置模板
└── plugins/
    └── human_manual/
        ├── __init__.py          # 插件主逻辑
        └── README.md            # 插件说明
```

---

## ❓ 常见问题

**Q: Docker 启动失败？**
- 确保 Docker Desktop 正在运行（任务栏有鲸鱼图标）
- 端口 2531/2532 被占用？用 `netstat -ano | findstr 2531` 检查

**Q: 扫码后没反应？**
- 查看控制台日志排查
- 确认 `gewechat_app_id` 和 `gewechat_token` 已正确填入 config.json

**Q: 记录说明书时 AI 解析失败？**
- 检查 DeepSeek API Key 是否正确
- 检查网络是否能访问 `https://api.deepseek.com`
- 查看控制台详细错误信息

**Q: 微信账号会被封吗？**
- 建议使用微信小号
- Gewechat 是基于网页版微信协议的，有被封风险，请自行评估

---

## 📝 待扩展功能

- [ ] Web 管理面板（可视化查看和编辑）
- [ ] 自然语言复杂查询（"谁不吃香菜？"）
- [ ] 定时提醒（生日、纪念日）
- [ ] 数据导出（Markdown / JSON）
- [ ] 多人共享
