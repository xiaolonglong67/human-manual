# human_manual 插件

chatgpt-on-wechat 插件：通过微信记录和查询朋友的偏好、习惯、忌口等信息。

## 安装

将本目录复制到 chatgpt-on-wechat 的 `plugins/` 目录下：

```powershell
copy -Recurse .\ D:\Desktop\chatgpt-on-wechat\plugins\human_manual
```

或使用符号链接（修改代码后无需重新复制）：

```powershell
New-Item -ItemType SymbolicLink -Path "D:\Desktop\chatgpt-on-wechat\plugins\human_manual" -Target "D:\Desktop\human-manual\plugins\human_manual"
```

## 依赖

插件依赖 `requests` 库（chatgpt-on-wechat 已自带）。

## 数据库

数据存储在插件目录下的 `human_manual.db`（SQLite）。表结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 人物姓名 |
| alias | TEXT | 别名 |
| info | TEXT | JSON 格式信息 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
