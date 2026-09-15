"""
API 调用层 — 深度研究 + 联网补充

缓存逻辑已移至 search-router。此处仅负责 HTTP 调用和响应解析。
"""

import json
import sys
import os
import urllib.request
import urllib.error


"""
latex_utils.py — LaTeX → Unicode 符号转换

将简单 LaTeX 数学表达式（下标/上标）转为 Unicode 字符，
适用于 AI 课程中的公式在纯文本环境下的可读性优化。
"""

import re

# ==================== 映射表 ====================

SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
}

SUBSCRIPT_LETTER_MAP = {
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'h': 'ₕ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ',
    's': 'ₛ', 't': 'ₜ',
}

SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
}

SUPERSCRIPT_LETTER_MAP = {
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
}


def _to_subscript(char):
    return SUBSCRIPT_MAP.get(char) or SUBSCRIPT_LETTER_MAP.get(char) or char


def _to_superscript(char):
    return SUPERSCRIPT_MAP.get(char) or SUPERSCRIPT_LETTER_MAP.get(char) or char


def convert_latex_to_unicode(text):
    """将简单 LaTeX 下标/上标转为 Unicode

    支持的模式：
      $Base_{sub}$  → Base + 下标字符
      $Base^{sup}$  → Base + 上标字符
      $Base_x$      → Base + 单字符下标
      $Base^x$      → Base + 单字符上标
    """
    if not text:
        return text

    # Pattern 1: $Base_{sub}$
    text = re.sub(
        r'\$([A-Za-z]+)\s*_\s*\{\s*([^}]+?)\s*\}\$',
        lambda m: m.group(1) + ''.join(_to_subscript(c) for c in m.group(2).strip()),
        text,
    )

    # Pattern 2: $Base^{sup}$
    text = re.sub(
        r'\$([A-Za-z]+)\s*\^\s*\{\s*([^}]+?)\s*\}\$',
        lambda m: m.group(1) + ''.join(_to_superscript(c) for c in m.group(2).strip()),
        text,
    )

    # Pattern 3: $Base_x$ (单字符下标)
    text = re.sub(
        r'\$([A-Za-z]+)\s*_\s*([A-Za-z0-9])\$',
        lambda m: m.group(1) + _to_subscript(m.group(2)),
        text,
    )

    # Pattern 4: $Base^x$ (单字符上标)
    text = re.sub(
        r'\$([A-Za-z]+)\s*\^\s*([A-Za-z0-9])\$',
        lambda m: m.group(1) + _to_superscript(m.group(2)),
        text,
    )

    return text


def _val(key: str, fallback: str = "") -> str:
    """三级取值：环境变量 > .env.local > .env.shared > 硬编码"""
    return (
        os.environ.get(key)
        or fallback
    )



RESEARCH_BASE = _val("KB_RESEARCH_API_BASE_URL", "http://kb-research-service.polymas.com")
BUSINESS_BASE = _val("KB_BUSINESS_API_BASE_URL", "http://kb-business-service.polymas.com")

ENDPOINTS = {
    "research": f"{RESEARCH_BASE}/research/deepAgentResearch",
    "internet_rag": f"{BUSINESS_BASE}/api/knowledge/base/proxy/ai/understood/openDomainRag-recommend",
}

def call_research_api(params: dict) -> dict:
    """调用深度研究 API（支持 SSE 流式解析）"""
    headers = {"Content-Type": "application/json"}

    url = ENDPOINTS["research"]
    body = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw_text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    return parse_api_response(raw_text)


def call_internet_rag_api(params: dict) -> dict:
    """调用联网补充 API"""
    headers = {"Content-Type": "application/json"}
    url = ENDPOINTS["internet_rag"]

    body = json.dumps({
        "querySize": params.get("querySize", 5),
        "text": params.get("text", ""),
        "channelList": [],
        "queryMode": 1,
        "deepSearchMode": False,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw_text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"连接失败: {e.reason}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"data": {"result": raw_text}}


# ==================== SSE 解析 ====================


def parse_api_response(raw_text: str) -> dict:
    """解析 API 响应（SSE / JSON / 纯文本）"""
    # SSE 格式
    if raw_text.startswith("data:"):
        lines = [l for l in raw_text.split("\n") if l.startswith("data:")]
        final_result_list = None
        final_content = None
        process_stages = []

        for i, line in enumerate(lines):
            json_str = line[5:].strip()
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            message = (data.get("choices") or [{}])[0].get("message", {})
            if not message:
                continue

            result_list = message.get("resultList") or []
            content = message.get("content", "")
            json_content = message.get("jsonContent") or {}
            is_last = (i == len(lines) - 1)

            if not is_last:
                process_stages.append({
                    "step": json_content.get("step", i),
                    "resultCount": len(result_list) if result_list else 0,
                    "action": json_content.get("action", ""),
                })
                continue

            # 最后一步
            if result_list:
                final_result_list = result_list
                final_content = content
            else:
                final_content = content

        if final_result_list:
            formatted = format_result_list(final_result_list, final_content)
            return {"data": {"result": formatted}, "_meta": {"stages": len(lines), "hasResultList": True}}

        if final_content:
            return {"data": {"result": final_content}, "_meta": {"stages": len(lines), "hasResultList": False}}

        return {"data": {"result": "未找到相关资源，请尝试其他查询。"}}

    # JSON 格式
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"data": {"result": raw_text}}


def format_result_list(result_list: list, api_content: str = None) -> str:
    """格式化 resultList 为 Markdown + URL 映射"""
    md = ""
    url_map = {}

    if api_content and api_content.strip():
        md += "## 💡 参考回答\n\n"
        md += f"{api_content.strip()}\n\n---\n\n"

    md += "## 📚 检索资源\n\n"
    md += f"共找到 **{len(result_list)}** 个相关资源：\n\n"

    for idx, item in enumerate(result_list):
        url_id = f"URL{idx + 1}"

        # URL 映射
        if item.get("previewUrl"):
            url_map[f"{url_id}P"] = {
                "previewUrl": item["previewUrl"],
                "previewType": item.get("previewType", "PDF"),
                "fileName": item.get("fileName", ""),
                "platformName": item.get("platformName", "知识库"),
                "publishTime": item.get("publishTime") or item.get("pubdate", ""),
            }
        if item.get("src") and item.get("src") != item.get("previewUrl"):
            url_map[f"{url_id}S"] = {
                "previewUrl": item["src"],
                "previewType": "WEBLINK",
                "platformName": item.get("platformName", "知识库"),
            }

        # 标题
        title = item.get("title", "未命名文档")
        if item.get("previewUrl"):
            md += f"### [{idx + 1}] [{title}]({url_id}P)\n\n"
        else:
            md += f"### [{idx + 1}] {title}\n\n"

        # 元数据
        meta = []
        if item.get("fileName"):
            meta.append(f"📄 {item['fileName']}")
        if item.get("pubdate"):
            meta.append(f"📅 {item['pubdate']}")
        if meta:
            md += " | ".join(meta) + "\n\n"

        # 推荐理由
        if item.get("reason"):
            md += f"**📌 推荐理由**：{item['reason']}\n\n"

        # 内容摘要
        if item.get("description"):
            desc = item["description"]
            import re
            img_matches = list(re.finditer(r"<img\s+src='([^']+)'(?:\s+alt='([^']*)')?", desc))
            for img_idx, m in enumerate(img_matches):
                img_id = f"IMG{idx + 1}_{img_idx + 1}"
                url_map[img_id] = m.group(1)

            clean_desc = re.sub(r"<img[^>]*>", "", desc)
            clean_desc = re.sub(r"\n{3,}", "\n\n", clean_desc).strip()
            clean_desc = convert_latex_to_unicode(clean_desc)

            md += f"**📄 内容摘要**：\n{clean_desc}\n\n"

            for img_idx, m in enumerate(img_matches):
                img_id = f"IMG{idx + 1}_{img_idx + 1}"
                alt_text = m.group(2) or title
                md += f"![{alt_text}]({img_id})\n\n"

        # 原文链接
        if item.get("src") and item.get("src") != item.get("previewUrl"):
            md += f"**🔗 原文**：[查看完整文档]({url_id}S)\n\n"

        md += "---\n\n"

    # URL 映射表
    md += "\n<!-- URL_MAP\n" + json.dumps(url_map, ensure_ascii=False, indent=2) + "\n-->\n"

    return md
