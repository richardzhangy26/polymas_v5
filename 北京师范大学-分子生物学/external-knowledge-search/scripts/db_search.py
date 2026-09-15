#!/usr/bin/env python3
"""
db-search — 知识库检索 (CoPaw Python 版)

用法:
    python scripts/search.py "查询内容" [--kb-ids ID1,ID2] [--query-size 5] [--text-list '["q1","q2"]'] [--with-llm]

返回 JSON 到 stdout，CoPaw Agent 通过 execute_shell_command 调用。
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def _val(key: str, fallback: str = "") -> str:
    """三级降级：环境变量 > .env.local > .env.shared > 硬编码"""
    return  fallback


# 配置常量（模块加载时求值，后续零 IO）
_CONFIG = {
    "api_base_url": _val("KB_DATA_API_BASE_URL", "http://kb-data.polymas.com"),
    "api_endpoint": "/api/knowledge/base/block/customSearch",
    "default_kb_ids": _val("KB_IDS", "p9RGivNVOJ"),
}


def get_config():
    return _CONFIG


# ==================== 参数校验 ====================


def validate_args(args):
    """校验参数"""
    errors = []

    if not args.query or not args.query.strip():
        errors.append("text 不能为空")

    if args.query_size < 1 or args.query_size > 20:
        errors.append(f"query_size 必须在 1-20 之间，当前: {args.query_size}")
    # text_list 校验
    if args.text_list:
        try:
            tl = json.loads(args.text_list)
            if not isinstance(tl, list):
                errors.append("text_list 必须是 JSON 数组")
            elif len(tl) > 10:
                errors.append(f"text_list 最多 10 个，当前: {len(tl)}")
        except json.JSONDecodeError:
            errors.append("text_list 不是合法 JSON")

    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return None


# ==================== API 调用 ====================


def call_search_api(text: str, query_size: int, kb_id: str, text_list: list, with_llm: bool) -> dict:
    """调用知识库检索 API

    公共参数映射:
        text → API keyWord
        query_size → API pageSize
    """
    cfg = get_config()
    url = cfg["api_base_url"] + cfg["api_endpoint"]

    # 处理 kb_ids：逗号分隔 → 数组

    body = {
        "queryMode": 1,
        "pageSize": query_size,
        "knowledgeBaseIds": [kb_id],
        "keyWord": text,
        "textList": text_list,
        "withLlm": with_llm,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 结果格式化 ====================


def format_results(api_response: dict, text: str, kb_ids: str, text_list: list, with_llm: bool) -> dict:
    """格式化结果为标准输出"""
    results = api_response.get("data", {}).get("data", [])
    total = api_response.get("data", {}).get("total", 0)

    formatted = []
    for item in results:
        # 优先使用 content，如果为空则回退到 description
        content = item.get("content", "") or item.get("description", "")

        formatted.append({
            "title": item.get("title", ""),
            "description": content,  # 使用 content 或 description
            "similarity": item.get("similarity", 0),
            "previewUrl": item.get("previewUrl", ""),
            "previewUrlIcon": item.get("previewUrlIcon", "🔗"),
            "previewType": item.get("previewType", ""),
            "fileName": item.get("fileName", ""),
            "resourceName": item.get("resourceName", ""),
            "contentUid": item.get("contentUid", ""),
        })

    return {
        "success": True,
        "query": text,
        "knowledgeBaseIds": kb_ids,
        "textList": text_list,
        "withLlm": with_llm,
        "count": len(formatted),
        "total": total,
        "results": formatted,
    }


# ==================== 主入口 ====================


def main():
    parser = argparse.ArgumentParser(description="知识库检索")
    parser.add_argument("query", nargs="?", help="用户问题")
    parser.add_argument("--kb_id", default="", help="知识库ID（逗号分隔）")
    parser.add_argument("--query_size", type=int, default=5, help="返回结果数量（1-20，公共参数，内部映射为 API pageSize）")
    parser.add_argument("--text_list", default="[]", help="额外检索语句 JSON 数组")
    parser.add_argument("--with-llm", default="False",action="store_true", help="启用 LLM 增强模式")

    args = parser.parse_args()

    # 参数校验
    err = validate_args(args)

    if err:
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)
    print(args.query, args.kb_id, file=sys.stderr)
    # 解析 text_list
    try:
        text_list = json.loads(args.text_list) if args.text_list else []
    except json.JSONDecodeError:
        text_list = []

    # 确定 kb_ids（参数 > 配置文件 > 默认）
    kb_ids = args.kb_id.strip() if args.kb_id.strip() else ""
    print(kb_ids, file=sys.stderr)
    if not kb_ids:
        print(
            json.dumps({"success": False, "error": "未指定知识库 ID（--kb-ids 或 KB_IDS 环境变量）"}, ensure_ascii=False))
        sys.exit(1)

    # 调用 API（text → keyWord, query_size → pageSize）
    api_resp = call_search_api(args.query.strip(), args.query_size, kb_ids, text_list, args.with_llm)

    # 检查 API 级错误
    if api_resp.get("success") is False:
        print(json.dumps(api_resp, ensure_ascii=False))
        sys.exit(1)

    # 格式化输出
    result = format_results(api_resp, args.query.strip(), kb_ids, text_list, args.with_llm)

    # 压缩处理（token 控制 + 链接 ID 化 + 渐进截断）
    try:
        from db_compress_result import compress_result
        compressed = compress_result(result)
        result["_compressed"] = {
            "markdown": compressed["markdown"],
            "linkMap": compressed["linkMap"],
            "overflowFiles": compressed["overflowFiles"],
            "stats": compressed["stats"],
        }
    except Exception as e:
        print(f"[db-search] 压缩失败（降级为未压缩）: {e}", file=sys.stderr)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
