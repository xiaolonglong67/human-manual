"""
DeepSeek API 异步调用 — 将非结构化文本转为结构化 JSON
"""

import json
import os

import httpx

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com").strip()

# 重试配置
MAX_RETRIES = 2
RETRY_DELAY_SEC = 1.0

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
    """调用 DeepSeek 将非结构化文本转为结构化 JSON，带自动重试"""
    import asyncio

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

    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code >= 500:
                    last_error = ValueError(f"DeepSeek 服务器错误 (HTTP {resp.status_code}): {resp.text[:300]}")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY_SEC)
                        continue
                    raise last_error

                if resp.status_code >= 400:
                    raise ValueError(
                        f"DeepSeek API 请求错误 (HTTP {resp.status_code}): {resp.text[:300]}"
                    )

                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    raise ValueError(
                        f"DeepSeek 返回非 JSON (HTTP {resp.status_code}): {resp.text[:300]}"
                    )

                if "choices" not in data:
                    raise ValueError(f"DeepSeek 返回异常: {json.dumps(data, ensure_ascii=False)[:300]}")
                content = data["choices"][0]["message"]["content"]

            # — 清理可能的 markdown 代码块标记 —
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 1 else content
                if content.endswith("```"):
                    content = content[:-3]

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                raise ValueError(f"DeepSeek 返回非 JSON: {content[:500]}")

        except (ValueError, json.JSONDecodeError) as e:
            # 非 5xx 错误不重试
            if "HTTP 5" not in str(e) and attempt < MAX_RETRIES:
                last_error = e
                await asyncio.sleep(RETRY_DELAY_SEC)
                continue
            raise

    raise last_error or RuntimeError("DeepSeek 调用失败")
