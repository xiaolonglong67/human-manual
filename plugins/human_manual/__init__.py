"""
人类使用说明书 — chatgpt-on-wechat 插件
===========================================

通过微信记录和查询朋友的偏好、习惯、忌口等信息。

用法：
  记录说明书：<自然语言描述>    → 解析并存入数据库
  查询说明书：<人名>           → 查询某人的说明书
  说明书列表                   → 列出所有已记录的人
"""

import json
import os
import sqlite3

import requests
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from plugins import Event, EventAction, EventContext, Plugin, register


# ── 数据库 ────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "human_manual.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                alias       TEXT    DEFAULT '',
                info        TEXT    DEFAULT '{}',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_people_name ON people(name)"
        )


# ── DeepSeek 调用 ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个信息提取助手。用户会发来一段关于某个人的描述，请从中提取结构化信息。

严格返回 JSON（不要 markdown 代码块，只返回纯 JSON），格式如下：

{
  "name": "人物姓名或昵称",
  "aliases": ["别名1", "别名2"],
  "info": {
    "food_preferences": ["爱吃/不爱吃的东西"],
    "habits": ["生活习惯"],
    "important_dates": {"事件": "日期"},
    "personality": ["性格特点"],
    "notes": ["其他值得记录的信息"]
  }
}

规则：
1. 只返回 JSON，不要任何其他文字
2. 没有对应字段的信息就设为空数组或空对象
3. 用中文输出
4. 日期保持原始表述"""


def call_deepseek(user_text, api_key, api_base):
    """调用 DeepSeek 将非结构化文本转为结构化 JSON"""
    url = f"{api_base.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    # 清理可能存在的 markdown 代码块标记
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)


# ── 数据库操作 ─────────────────────────────────────────────────────────

def _lookup_person(db, query_name):
    """按姓名或别名查找人物，返回 (id, name, info_json) 或 None"""
    cur = db.execute(
        "SELECT id, name, info, alias FROM people WHERE name = ? OR alias LIKE ?",
        (query_name, f"%{query_name}%"),
    )
    return cur.fetchone()


def upsert_person(db, parsed):
    """插入或更新人物信息。已存在则合并 info JSON。返回是否为新增。"""
    name = parsed["name"]
    aliases = ",".join(parsed.get("aliases", []))
    new_info = json.dumps(parsed.get("info", {}), ensure_ascii=False)

    existing = db.execute(
        "SELECT id, info FROM people WHERE name = ?", (name,)
    ).fetchone()

    if existing:
        # 合并 info：新值覆盖旧值中同名 key 的数组/对象
        old_info = json.loads(existing[1])
        incoming = parsed.get("info", {})

        for key, val in incoming.items():
            if isinstance(val, list) and key in old_info and isinstance(old_info[key], list):
                # 数组：去重合并
                seen = set(old_info[key])
                for v in val:
                    if v not in seen:
                        old_info[key].append(v)
            elif isinstance(val, dict) and key in old_info and isinstance(old_info[key], dict):
                # 字典：浅合并
                old_info[key].update(val)
            else:
                old_info[key] = val

        merged = json.dumps(old_info, ensure_ascii=False)
        db.execute(
            "UPDATE people SET alias = ?, info = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (aliases, merged, existing[0]),
        )
        return False
    else:
        db.execute(
            "INSERT INTO people (name, alias, info) VALUES (?, ?, ?)",
            (name, aliases, new_info),
        )
        return True


def format_person_card(row):
    """将数据库行格式化为可读文本"""
    _id, name, info_json, alias, created, updated = row
    info = json.loads(info_json)

    lines = [f"📋 【{name}的使用说明书】"]
    if alias:
        lines.append(f"🏷 别名：{alias}")

    food = info.get("food_preferences", [])
    if food:
        lines.append(f"🍽 饮食偏好：{'；'.join(food)}")

    habits = info.get("habits", [])
    if habits:
        lines.append(f"🔄 生活习惯：{'；'.join(habits)}")

    dates = info.get("important_dates", {})
    if dates:
        items = [f"{k}：{v}" for k, v in dates.items()]
        lines.append(f"📅 重要日期：{'；'.join(items)}")

    personality = info.get("personality", [])
    if personality:
        lines.append(f"🧠 性格特点：{'；'.join(personality)}")

    notes = info.get("notes", [])
    if notes:
        lines.append(f"📝 备注：{'；'.join(notes)}")

    if len(lines) == 1:
        return f"📋 【{name}】暂无详细信息。发送「记录说明书：{name}，...」来添加。"
    return "\n".join(lines)


# ── 配置读取 ──────────────────────────────────────────────────────────

def _load_config():
    """读取 chatgpt-on-wechat 的 config.json"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
    config_path = os.path.abspath(config_path)
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 插件主体 ──────────────────────────────────────────────────────────

@register(
    name="HumanManual",
    desire_priority=100,
    desc="人类说明书——记录和查询朋友的偏好与习惯",
    version="1.0",
    author="Song Jincang",
)
class HumanManual(Plugin):
    def __init__(self):
        super().__init__()
        init_db()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type != ContextType.TEXT:
            return

        content = e_context["context"].content.strip()

        # ── 记录说明书 ──
        if content.startswith("记录说明书："):
            raw = content[len("记录说明书："):].strip()
            if not raw:
                e_context["reply"] = Reply(
                    ReplyType.TEXT, "💡 请这样写：\n记录说明书：张三，不吃香菜，生日是5月12日"
                )
                e_context.action = EventAction.BREAK_PASS
                return

            config = _load_config()
            api_key = config.get("open_ai_api_key", os.environ.get("OPENAI_API_KEY", ""))
            api_base = config.get("open_ai_api_base", "https://api.deepseek.com")

            if not api_key or api_key == "你的DeepSeek_API_KEY":
                e_context["reply"] = Reply(
                    ReplyType.TEXT, "❌ 未配置 DeepSeek API Key，请检查 config.json"
                )
                e_context.action = EventAction.BREAK_PASS
                return

            try:
                parsed = call_deepseek(raw, api_key, api_base)
            except Exception as e:
                e_context["reply"] = Reply(
                    ReplyType.TEXT, f"❌ AI 解析失败：{e}"
                )
                e_context.action = EventAction.BREAK_PASS
                return

            with _conn() as db:
                is_new = upsert_person(db, parsed)

            name = parsed["name"]
            if is_new:
                e_context["reply"] = Reply(
                    ReplyType.TEXT, f"✅ 已为「{name}」创建说明书！"
                )
            else:
                e_context["reply"] = Reply(
                    ReplyType.TEXT, f"✅ 已更新「{name}」的说明书！"
                )
            e_context.action = EventAction.BREAK_PASS
            return

        # ── 查询说明书 ──
        if content.startswith("查询说明书："):
            query = content[len("查询说明书："):].strip()
            if not query:
                e_context["reply"] = Reply(
                    ReplyType.TEXT, "💡 请这样写：\n查询说明书：张三"
                )
                e_context.action = EventAction.BREAK_PASS
                return

            with _conn() as db:
                row = _lookup_person(db, query)
                if row:
                    # 补全完整行数据
                    full = db.execute(
                        "SELECT id, name, info, alias, created_at, updated_at FROM people WHERE id = ?",
                        (row[0],),
                    ).fetchone()
                    text = format_person_card(full)
                else:
                    text = (
                        f"🔍 未找到「{query}」的说明书。\n"
                        f"发送「记录说明书：{query}，...」来创建。"
                    )

            e_context["reply"] = Reply(ReplyType.TEXT, text)
            e_context.action = EventAction.BREAK_PASS
            return

        # ── 说明书列表 ──
        if content == "说明书列表":
            with _conn() as db:
                rows = db.execute(
                    "SELECT name, alias FROM people ORDER BY updated_at DESC"
                ).fetchall()

            if not rows:
                e_context["reply"] = Reply(
                    ReplyType.TEXT,
                    "📭 还未记录任何人的说明书。\n发送「记录说明书：人名，描述...」来添加第一条！",
                )
            else:
                lines = ["📚 【已记录的说明书】"]
                for i, (name, alias) in enumerate(rows, 1):
                    label = f"  {name}"
                    if alias:
                        label += f"（{alias}）"
                    lines.append(f"{i}.{label}")
                lines.append(f"\n共 {len(rows)} 条记录。发送「查询说明书：姓名」查看详情。")
                e_context["reply"] = Reply(ReplyType.TEXT, "\n".join(lines))

            e_context.action = EventAction.BREAK_PASS
            return
