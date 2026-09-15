#!/usr/bin/env python3
"""
compress_result.py — web-domain-search 结果压缩模块

功能：
1. 总 token 控制在阈值内（默认 96K）
2. 所有链接替换为短 ID 占位符，附带映射表
3. 靠前的结果保留完整正文，靠后的渐进截断 → 溢出写入文件
"""

import json
import math
import os
import re
import shutil
import time
import tempfile

# ==================== 配置 ====================

DEFAULT_CONFIG = {
    "max_tokens": 96000,
    "full_content_ratio": 0.6,
    "summary_max_chars": 300,
    "overflow_dir": os.path.join(tempfile.gettempdir(), "openclaw-overflow", "web-search"),
    "max_overflow_dirs": 10,
}


def load_config(skill_dir):
    config = dict(DEFAULT_CONFIG)
    config_path = os.path.join(skill_dir, "compress.config.json")
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config.update(user_config)
    except Exception:
        pass
    return config


# ==================== Token 估算 ====================

def estimate_tokens(text):
    if not text:
        return 0
    tokens = 0.0
    for ch in text:
        code = ord(ch)
        if 0x4E00 < code < 0x9FFF:
            tokens += 0.6
        elif code > 127:
            tokens += 0.5
        else:
            tokens += 0.25
    return math.ceil(tokens)


# ==================== 链接替换 ====================

def replace_links_with_ids(text, link_map, counter):
    if not text:
        return ""
    url_re = re.compile(r'https?://[^\s)>\]"\'`]+')

    def _replacer(m):
        url = m.group(0)
        for k, v in link_map.items():
            if (isinstance(v, str) and v == url) or (isinstance(v, dict) and v.get("previewUrl") == url):
                return k
        counter["count"] += 1
        lid = f"L{counter['count']}"
        link_map[lid] = url
        return lid

    return url_re.sub(_replacer, text)


def replace_markdown_links(text, link_map, counter):
    if not text:
        return text

    md_link_re = re.compile(r'(\[[^\]]*\])\((https?://[^\s)]+)\)')

    def _md_replacer(m):
        link_text = m.group(1)
        url = m.group(2)
        for k, v in link_map.items():
            if (isinstance(v, str) and v == url) or (isinstance(v, dict) and v.get("previewUrl") == url):
                return f"{link_text}({k})"
        counter["count"] += 1
        lid = f"L{counter['count']}"
        link_map[lid] = url
        return f"{link_text}({lid})"

    text = md_link_re.sub(_md_replacer, text)
    text = replace_links_with_ids(text, link_map, counter)
    return text


# ==================== 溢出文件管理 ====================

def cleanup_overflow_dirs(root_dir, max_dirs):
    try:
        if not os.path.isdir(root_dir):
            return
        entries = []
        for name in os.listdir(root_dir):
            full = os.path.join(root_dir, name)
            if os.path.isdir(full):
                entries.append((name, os.path.getmtime(full)))
        entries.sort(key=lambda x: x[1], reverse=True)
        if len(entries) > max_dirs:
            for name, _ in entries[max_dirs:]:
                shutil.rmtree(os.path.join(root_dir, name), ignore_errors=True)
    except Exception:
        pass


# ==================== 单条结果格式化 ====================

def format_single_result(item, index, link_map, counter, is_full, config):
    """
    格式化单个结果项
    
    注意：直接输出可点击的 Markdown 链接格式 [标题](URL)，不使用 L1、L2 占位符
    """
    num = index + 1

    title = item.get("title") or f"结果 {num}"
    # 不再使用 replace_markdown_links，保持原始标题

    source_link = ""
    url = item.get("url") or item.get("link")
    if url:
        # 直接输出可点击的链接，不使用占位符
        source_link = f"[查看原文]({url})"

    meta = []
    platform = item.get("platformName") or item.get("source")
    if platform:
        meta.append(f"🌐 {platform}")
    pub_time = item.get("publishTime") or item.get("date")
    if pub_time:
        meta.append(f"📅 {pub_time}")

    content = item.get("description") or item.get("snippet") or item.get("content") or item.get("text") or ""
    # 不再替换链接为占位符，保持原始内容

    summary_content = content[:config["summary_max_chars"]] + "..." if len(content) > config["summary_max_chars"] else content

    meta_str = " | ".join(meta) + (" | " + source_link if source_link else "")

    full_md = f"### [{num}] {title}\n\n{meta_str}\n\n{content}\n\n"
    summary_md = f"### [{num}] {title}\n\n{meta_str}\n\n{summary_content}\n\n> 💡 *此条结果已截断，完整内容见溢出文件*\n\n"
    overflow_md = f"### [{num}] {title}\n\n{content}\n\n"

    return {"full": full_md, "summary": summary_md, "overflow": overflow_md, "overflow_full": full_md}


# ==================== 核心压缩 ====================

def compress_result(raw_result, options=None):
    skill_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    config = load_config(skill_dir)
    if options:
        config.update(options)

    link_map = {}
    counter = {"count": 0}

    # 兼容多种输入格式
    results = []
    if isinstance(raw_result, dict):
        if isinstance(raw_result.get("results"), list):
            results = list(raw_result["results"])
        elif isinstance(raw_result.get("data"), dict) and isinstance(raw_result["data"].get("resultList"), list):
            results = list(raw_result["data"]["resultList"])
        elif isinstance(raw_result.get("data"), list):
            results = list(raw_result["data"])
    elif isinstance(raw_result, list):
        results = list(raw_result)

    if not results:
        return {
            "markdown": "> 网络搜索未找到相关结果。\n",
            "linkMap": {},
            "overflowFiles": [],
            "stats": {"totalResults": 0, "keptFull": 0, "keptSummary": 0, "truncatedCount": 0, "overflowFileCount": 0, "estimatedTokens": 0},
        }

    # web 结果已按相关度排序，不需要再排

    max_tokens = config["max_tokens"]
    header_budget = 1500
    map_budget = min(len(results) * 100, 5000)
    content_budget = max_tokens - header_budget - map_budget
    full_budget = int(content_budget * config["full_content_ratio"])

    used_tokens = 0
    full_phase = True
    processed_items = []
    overflow_items = []
    kept_full = 0
    kept_summary = 0

    for i, item in enumerate(results):
        item_md = format_single_result(item, i, link_map, counter, full_phase, config)
        item_tokens = estimate_tokens(item_md["full"])

        if used_tokens + item_tokens <= content_budget and full_phase:
            processed_items.append(item_md["full"])
            used_tokens += item_tokens
            kept_full += 1
            if used_tokens >= full_budget:
                full_phase = False
        elif used_tokens < content_budget:
            full_phase = False
            summary_tokens = estimate_tokens(item_md["summary"])
            if used_tokens + summary_tokens <= content_budget:
                processed_items.append(item_md["summary"])
                used_tokens += summary_tokens
                kept_summary += 1
                if item_md.get("overflow"):
                    overflow_items.append(item_md["overflow"])
            else:
                overflow_items.append(item_md.get("overflow_full") or item_md["full"])
        else:
            overflow_items.append(item_md.get("overflow_full") or item_md["full"])

    markdown = f"## 🌐 网络搜索结果\n\n> 共 **{len(results)}** 条结果（前 {kept_full} 条完整，{kept_summary} 条摘要）\n\n"
    markdown += "\n".join(processed_items)

    overflow_files = []
    overflow_dir_path = None
    if overflow_items:
        try:
            os.makedirs(config["overflow_dir"], exist_ok=True)
            cleanup_overflow_dirs(config["overflow_dir"], config["max_overflow_dirs"] - 1)
            ts = int(time.time() * 1000)
            overflow_dir_path = os.path.join(config["overflow_dir"], f"req-{ts}")
            os.makedirs(overflow_dir_path, exist_ok=True)
            for idx, ov in enumerate(overflow_items):
                fname = f"{idx + 1:02d}.md"
                fpath = os.path.join(overflow_dir_path, fname)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"# 网络搜索 - 溢出资源 #{idx + 1}\n\n> 因 token 限制被截断，此处保留完整内容。\n\n{ov}")
                overflow_files.append(fpath)
        except Exception:
            pass

        markdown += "\n---\n\n"
        markdown += f"> 📖 还有 **{len(overflow_items)}** 条结果被截断，每条资源单独保存：\n"
        for fp in overflow_files:
            markdown += f"> - `{os.path.basename(fp)}`\n"
        if overflow_dir_path:
            markdown += f"> \n> 📂 溢出文件夹: `{overflow_dir_path}`\n"

    # 不再输出 LINK_MAP，因为已经直接使用可点击链接
    # markdown += "\n\n<!-- LINK_MAP\n" + json.dumps(link_map, ensure_ascii=False, indent=2) + "\n-->\n"

    return {
        "markdown": markdown,
        "linkMap": {},  # 不再需要 linkMap
        "overflowFiles": overflow_files,
        "stats": {
            "totalResults": len(results),
            "keptFull": kept_full,
            "keptSummary": kept_summary,
            "truncatedCount": len(overflow_items),
            "overflowFileCount": len(overflow_files),
            "estimatedTokens": estimate_tokens(markdown),
        },
    }
