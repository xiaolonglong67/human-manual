"""
数据库操作 — 异步 SQLite（aiosqlite）

表结构：
  users  — id, username, password(bcrypt hash), created_at
  people — id, user_id(FK), name, alias, info(JSON), created_at, updated_at
"""

import json
import os
from contextlib import asynccontextmanager

import aiosqlite

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "human_manual.db"))
DB_PATH = os.path.abspath(DB_PATH)


@asynccontextmanager
async def get_db():
    """获取数据库连接（异步上下文管理器）"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """初始化表结构"""
    async with get_db() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL UNIQUE,
                password    TEXT    NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                name        TEXT    NOT NULL,
                alias       TEXT    DEFAULT '',
                info        TEXT    DEFAULT '{}',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # 每个用户下 name 唯一
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_name ON people(user_id, name)"
        )
        await db.commit()


# ── 用户操作 ──

async def create_user(db: aiosqlite.Connection, username: str, password_hash: str) -> int:
    """创建用户，返回 user_id。用户名已存在则返回 None"""
    try:
        cur = await db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password_hash),
        )
        await db.commit()
        return cur.lastrowid
    except aiosqlite.IntegrityError:
        return None


async def get_user(db: aiosqlite.Connection, username: str):
    """按用户名查找用户，返回 Row 或 None"""
    cur = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
    return await cur.fetchone()


# ── 人物操作 ──

async def lookup_person(db: aiosqlite.Connection, user_id: int, query_name: str):
    """按姓名或别名查找人物，返回 Row 或 None"""
    cur = await db.execute(
        "SELECT id, name, info, alias FROM people WHERE user_id = ? AND (name = ? OR alias LIKE ?)",
        (user_id, query_name, f"%{query_name}%"),
    )
    return await cur.fetchone()


async def upsert_person(db: aiosqlite.Connection, user_id: int, parsed: dict) -> bool:
    """
    插入或更新人物信息。已存在则合并 info JSON。
    返回 True 表示新增，False 表示更新。
    """
    name = parsed["name"]
    aliases = ",".join(parsed.get("aliases", []))
    new_info = json.dumps(parsed.get("info", {}), ensure_ascii=False)

    cur = await db.execute(
        "SELECT id, info FROM people WHERE user_id = ? AND name = ?", (user_id, name)
    )
    existing = await cur.fetchone()

    if existing:
        # 合并 info
        old_info = json.loads(existing["info"])
        incoming = parsed.get("info", {})

        for key, val in incoming.items():
            if (
                isinstance(val, list)
                and key in old_info
                and isinstance(old_info[key], list)
            ):
                seen = set(old_info[key])
                for v in val:
                    if v not in seen:
                        old_info[key].append(v)
            elif (
                isinstance(val, dict)
                and key in old_info
                and isinstance(old_info[key], dict)
            ):
                old_info[key].update(val)
            else:
                old_info[key] = val

        merged = json.dumps(old_info, ensure_ascii=False)
        await db.execute(
            "UPDATE people SET alias = ?, info = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (aliases, merged, existing["id"]),
        )
        await db.commit()
        return False
    else:
        await db.execute(
            "INSERT INTO people (user_id, name, alias, info) VALUES (?, ?, ?, ?)",
            (user_id, name, aliases, new_info),
        )
        await db.commit()
        return True


async def get_person_full(db: aiosqlite.Connection, person_id: int):
    """获取人物完整信息"""
    cur = await db.execute(
        "SELECT id, name, info, alias, created_at, updated_at FROM people WHERE id = ?",
        (person_id,),
    )
    return await cur.fetchone()


async def list_people(db: aiosqlite.Connection, user_id: int):
    """列出用户的所有说明书"""
    cur = await db.execute(
        "SELECT name, alias FROM people WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    return await cur.fetchall()


# ── 格式化（纯函数，无需异步） ──

def format_person_card(row) -> str:
    """将数据库行格式化为可读文本"""
    info = json.loads(row["info"])
    name = row["name"]
    alias = row["alias"]

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
