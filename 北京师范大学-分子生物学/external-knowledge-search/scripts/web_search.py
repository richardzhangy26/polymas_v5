#!/usr/bin/env python3
"""
web-domain-search — 网络搜索 (CoPaw Python 版)
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

# ==================== 配置（模块加载时一次性读取并缓存） ====================
_CONFIG = {
    "api_base_url": "http://kb-business-service.polymas.com",
    "api_endpoint": "/api/knowledge/base/proxy/ai/understood/openDomainRag-recommend",
}


def get_config():
    return _CONFIG


# ==================== 参数校验 ====================


def validate_args(args):
    errors = []

    if not args.text or not args.text.strip():
        errors.append("text 不能为空")

    if args.query_size < 1 or args.query_size > 10:
        errors.append(f"query_size 必须在 1-10 之间，当前: {args.query_size}")

    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return None


# ==================== API 调用 ====================


def call_search_api(text: str, query_size: int) -> dict:
    """调用网络搜索 API

    公共参数映射:
        text → API text（恰好同名）
        query_size → API querySize（恰好同名）
    """
    cfg = get_config()
    url = cfg["api_base_url"] + cfg["api_endpoint"]

    body = {
        "querySize": query_size,
        "text": text,
        "courseName": "",
        "channelList": ["internet"],
        "limitDomainList": [],
        "stopWords": [],
        "queryMode": 1,
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


def format_results(api_response: dict, text: str) -> dict:
    # 兼容新 API 格式
    data = api_response.get("data", {})
    if isinstance(data, dict):
        result_list = data.get("resultList", [])
    elif isinstance(data, list):
        result_list = data
    else:
        result_list = []

    formatted = []
    for item in result_list:
        formatted.append({
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "url": item.get("url", ""),
            "similarity": item.get("similarity", 0),
            "publishTime": item.get("publishTime", ""),
            "platformName": item.get("platformName", ""),
            "coverUrl": item.get("coverUrl", ""),
            "previewUrl": item.get("previewUrl", ""),
            "previewUrlIcon": item.get("previewUrlIcon", "🌐"),
        })

    return {
        "success": True,
        "query": text,
        "count": len(formatted),
        "results": formatted,
    }


# ==================== 主入口 ====================


def main():
    parser = argparse.ArgumentParser(description="网络搜索")
    parser.add_argument("text", nargs="?", help="用户问题")
    parser.add_argument("--query-size", type=int, default=3,
                        help="返回结果数量（1-10，公共参数，内部映射为 API querySize）")

    args = parser.parse_args()

    # 参数校验
    err = validate_args(args)

    if err:
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    # 调用 API（text → text, query_size → querySize）
    api_resp = call_search_api(args.text.strip(), args.query_size)

    if api_resp.get("success") is False:
        print(json.dumps(api_resp, ensure_ascii=False))
        sys.exit(1)

    # 格式化输出
    result = format_results(api_resp, args.text.strip())

    # 压缩处理
    try:
        from web_compress_result import compress_result
        compressed = compress_result(result)
        result["_compressed"] = {
            "markdown": compressed["markdown"],
            "linkMap": compressed["linkMap"],
            "overflowFiles": compressed["overflowFiles"],
            "stats": compressed["stats"],
        }
    except Exception as e:
        print(f"[web-domain-search] 压缩失败（降级为未压缩）: {e}", file=sys.stderr)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
