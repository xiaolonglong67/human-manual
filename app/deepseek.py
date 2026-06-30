"""
DeepSeek API 异步调用 — 将非结构化文本转为结构化 JSON
"""

import json
import os

import httpx

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com").strip()

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


async def call_deepseek(user_text: str) -> dict:
    """调用 DeepSeek 将非结构化文本转为结构化 JSON"""
    url = f"{DEEPSEEK_API_BASE.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
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

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    # 清理可能的 markdown 代码块标记
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
    return json.loads(content)
