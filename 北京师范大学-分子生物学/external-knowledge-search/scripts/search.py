#!/usr/bin/env python3
"""
db-search — 知识库检索 (CoPaw Python 版)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# ==================== 配置（模块加载时一次性读取并缓存） ====================

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _val(key: str, fallback: str = "") -> str:
    """三级降级：环境变量 > .env.local > .env.shared > 硬编码"""
    return os.environ.get(key) or fallback


# 配置常量（模块加载时求值，后续零 IO）
_CONFIG = {
    "api_base_url": _val("KB_DATA_API_BASE_URL", "https://ai-platform-cloud-proxy.polymas.com/ai/understood/polymasWiki-search"),
    "api_endpoint": "",
    "default_kb_ids": _val("KB_IDS", "p9RGivNVOJ"),
}


def get_config():
    return _CONFIG


# ==================== 参数校验 ====================


def validate_args(args):
    """校验参数"""
    errors = []

    if not args.text or not args.text.strip():
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


def call_search_api(query: str, kb_id: str) -> dict:
    """调用知识库检索 API

    公共参数映射:
        text → API keyWord
        query_size → API pageSize
    """
    cfg = get_config()
    url = cfg["api_base_url"] + cfg["api_endpoint"]

    # 处理 kb_ids：逗号分隔 → 数组

    body = {
        "query": query,
        "kb_id": kb_id,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:

            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:

        print(f"HTTP 错误 {e.code}: {e.reason}", file=sys.stderr)
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:

        print(f"HTTP 错误 {e}: {e}", file=sys.stderr)
        return {"success": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 结果格式化 ====================

def format_results(api_response: dict, text: str, kb_ids: str) -> dict:
    """格式化结果为标准输出"""
    data = api_response.get("data", {})
    results = data.get("traversal_nodes", [])
    tree_view = data.get("tree_view", [])
    total = len(results)

    formatted = []
    for item in results:
        # 优先使用 content，如果为空则回退到 description
        content = item.get("enriched_content", "")
        formatted.append({
            "title": item.get("title", ""),
            "description": content,  # 使用 content 或 description
            "previewUrl": item.get("linkMap",{}).get("previewUrl", ""),
            "previewUrlIcon": item.get("linkMap",{}).get("previewUrlIcon", "🔗"),
            "previewType": item.get("linkMap",{}).get("previewType", ""),
            "fileName": item.get("fileName", ""),
            "resourceName": item.get("resourceName", ""),
        })

    return {
        "success": True,
        "query": text,
        "knowledgeBaseIds": kb_ids,
        "count": len(formatted),
        "total": total,
        "results": formatted,
        "tree_view": tree_view,
    }


# ==================== 主入口 ====================


def main():
    parser = argparse.ArgumentParser(description="知识库检索")
    parser.add_argument("query", nargs="?", help="用户问题")
    parser.add_argument("--kb_id", default="", help="知识库ID（逗号分隔）")

    args = parser.parse_args()

    # 确定 kb_ids（参数 > 配置文件 > 默认）
    cfg = get_config()
    kb_ids = args.kb_id.strip() if args.kb_id.strip() else ""

    if not kb_ids:
        print(
            json.dumps({"success": False, "error": "未指定知识库 ID（--kb-ids 或 KB_IDS 环境变量）"}, ensure_ascii=False))
        sys.exit(1)

    # 调用 API（text → keyWord, query_size → pageSize）
    api_resp = call_search_api(args.query, args.kb_id)
    result = format_results(api_resp, args.query, kb_ids)


    try:
        from compress_result import compress_result
        compressed = compress_result(result)
        result["_compressed"] = {
            "markdown": compressed["markdown"],
            "linkMap": compressed["linkMap"],
            "overflowFiles": compressed["overflowFiles"],
            "stats": compressed["stats"],
        }
    except Exception as e:
        print(f"[db-search] 压缩失败（降级为未压缩）: {e}", file=sys.stderr)

    # 格式化输出
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    main()
