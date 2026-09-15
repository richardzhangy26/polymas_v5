#!/usr/bin/env python3
"""
运行时上下文加载工具 — 从环境变量中加载并打印当前用户与会话上下文。

用法:
  python3 load_context.py

依赖环境变量:
  metadata — JSON 字符串（可空对象 `{}`）
  userId   — 当前操作用户 ID
  toNid    — 目标用户 ID
  traceId  — 会话链路追踪 ID
"""
import sys
import json
import os
from typing import Dict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def load_runtime_context() -> Dict[str, str]:
    metadata_raw = os.getenv("metadata", "{}")
    if not metadata_raw:
        raise RuntimeError("缺少环境变量 metadata（应为 JSON 字符串）")

    try:
        metadata = json.loads(metadata_raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"环境变量 metadata 不是合法 JSON：{e}") from e

    if not isinstance(metadata, dict):
        raise RuntimeError("环境变量 metadata 必须是 JSON 对象")

    user_id = os.getenv("userId")
    to_nid = os.getenv("toNid")
    trace_id = os.getenv("traceId")

    missing = []
    if not user_id:
        missing.append("userId")
    if not to_nid:
        missing.append("toNid")
    if not trace_id:
        missing.append("traceId")

    if missing:
        missing_text = "、".join(missing)
        raise RuntimeError(f"缺少必要环境变量字段：{missing_text}")

    return {
        "userId": user_id,
        "toNid": to_nid,
        "traceId": trace_id
    }


def main():
    try:
        context = load_runtime_context()
        print(json.dumps(context, ensure_ascii=False))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
