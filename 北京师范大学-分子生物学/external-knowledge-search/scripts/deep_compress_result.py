#!/usr/bin/env python3
"""
compress_result.py — deep-agent-research 结果压缩模块

特殊处理：
- 输入是已格式化的 Markdown（含 URL_MAP 注释）
- 需要解析已有 URL_MAP，合并到统一 linkMap
- 支持纯文本回答（非 resultList）的压缩
- 按资源段落切分（### [N] ...）
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
    "summary_max_chars": 500,
    "overflow_dir": os.path.join(tempfile.gettempdir(), "openclaw-overflow", "deep-research"),
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
            actual_url = v if isinstance(v, str) else v.get("previewUrl", "")
            if actual_url == url:
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
        link_text, url = m.group(1), m.group(2)
        for k, v in link_map.items():
            actual_url = v if isinstance(v, str) else v.get("previewUrl", "")
            if actual_url == url:
                return f"{link_text}({k})"
        counter["count"] += 1
        lid = f"L{counter['count']}"
        link_map[lid] = url
        return f"{link_text}({lid})"

    text = md_link_re.sub(_md_replacer, text)

    img_re = re.compile(r'(!\[[^\]]*\])\((https?://[^\s)]+)\)')

    def _img_replacer(m):
        img_tag, url = m.group(1), m.group(2)
        for k, v in link_map.items():
            actual_url = v if isinstance(v, str) else v.get("previewUrl", "")
            if actual_url == url:
                return f"{img_tag}({k})"
        counter["count"] += 1
        lid = f"L{counter['count']}"
        link_map[lid] = url
        return f"{img_tag}({lid})"

    text = img_re.sub(_img_replacer, text)
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


# ==================== 解析已有 URL_MAP ====================

def extract_and_migrate_url_map(markdown, link_map, counter):
    """从 Markdown 中提取 <!-- URL_MAP ... --> 并迁移占位符到统一 L{n} 格式"""
    map_match = re.search(r'<!-- URL_MAP\n([\s\S]*?)\n-->', markdown)
    if not map_match:
        return markdown

    try:
        old_map = json.loads(map_match.group(1))
    except (json.JSONDecodeError, ValueError):
        return markdown

    id_migration = {}
    for old_id, url_data in old_map.items():
        url_value = url_data if isinstance(url_data, str) else url_data.get("previewUrl", "")

        existing_id = None
        for k, v in link_map.items():
            existing_url = v if isinstance(v, str) else v.get("previewUrl", "")
            if existing_url == url_value:
                existing_id = k
                break

        if existing_id:
            id_migration[old_id] = existing_id
        else:
            counter["count"] += 1
            new_id = f"L{counter['count']}"
            link_map[new_id] = url_data  # 保留原始格式
            id_migration[old_id] = new_id

    # 移除旧 URL_MAP 注释
    cleaned = re.sub(r'\n?<!-- URL_MAP\n[\s\S]*?\n-->\n?', '', markdown)

    # 替换所有旧占位符
    for old_id, new_id in id_migration.items():
        escaped = re.escape(old_id)
        cleaned = re.sub(escaped + r'(?![0-9A-Za-z_])', new_id, cleaned)

    return cleaned


# ==================== 按资源段落切分 ====================

def split_into_resource_blocks(markdown):
    """将 Markdown 按资源段落切分"""
    lines = markdown.split('\n')
    blocks = []
    current_block = None
    header_lines = []

    for line in lines:
        if re.match(r'^###\s*\[?\d+\]?\s', line) or re.match(r'^###\s+\d+\.\s', line):
            if current_block:
                blocks.append(current_block)
            current_block = {"title": line, "content": ""}
        elif current_block is not None:
            current_block["content"] += line + "\n"
        else:
            header_lines.append(line)

    if current_block:
        blocks.append(current_block)

    return {"header": "\n".join(header_lines), "blocks": blocks}


# ==================== 核心压缩 ====================

def compress_result(raw_markdown, options=None):
    """压缩 deep-agent-research 返回的 Markdown"""
    # skill_dir: deep-agent-research 根目录
    skill_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    config = load_config(skill_dir)
    if options:
        config.update(options)

    link_map = {}
    counter = {"count": 0}

    if not raw_markdown or not isinstance(raw_markdown, str) or not raw_markdown.strip():
        return {
            "markdown": "> 深度研究未返回结果。\n",
            "linkMap": {},
            "overflowFiles": [],
            "stats": {"totalResults": 0, "keptFull": 0, "keptSummary": 0, "truncatedCount": 0, "overflowFileCount": 0, "estimatedTokens": 0},
        }

    # 1. 提取并迁移已有 URL_MAP
    processed_md = extract_and_migrate_url_map(raw_markdown, link_map, counter)

    # 2. 替换剩余裸 URL
    processed_md = replace_markdown_links(processed_md, link_map, counter)

    # 3. 如果总 token 在预算内，直接返回
    total_tokens = estimate_tokens(processed_md)
    if total_tokens <= config["max_tokens"]:
        final_md = processed_md + "\n\n<!-- LINK_MAP\n" + json.dumps(link_map, ensure_ascii=False, indent=2) + "\n-->\n"
        return {
            "markdown": final_md,
            "linkMap": link_map,
            "overflowFiles": [],
            "stats": {
                "totalResults": 0, "keptFull": 0, "keptSummary": 0,
                "truncatedCount": 0, "overflowFileCount": 0,
                "estimatedTokens": estimate_tokens(final_md),
            },
        }

    # 4. 需要截断 → 按资源块切分
    split = split_into_resource_blocks(processed_md)
    header = split["header"]
    blocks = split["blocks"]

    if not blocks:
        # 纯文本，直接字符截断
        max_chars = int(config["max_tokens"] * 2.5)
        truncated = processed_md[:max_chars]
        overflow_text = processed_md[max_chars:]

        overflow_files = []
        overflow_dir_path = None
        if overflow_text:
            try:
                os.makedirs(config["overflow_dir"], exist_ok=True)
                cleanup_overflow_dirs(config["overflow_dir"], config["max_overflow_dirs"] - 1)
                ts = int(time.time() * 1000)
                overflow_dir_path = os.path.join(config["overflow_dir"], f"req-{ts}")
                os.makedirs(overflow_dir_path, exist_ok=True)
                fpath = os.path.join(overflow_dir_path, "01.md")
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"# 深度研究 - 溢出内容\n\n> 因 token 限制被截断，此处保留完整内容。\n\n{processed_md}")
                overflow_files.append(fpath)
            except Exception:
                pass

        final_md = truncated
        if overflow_text and overflow_files:
            final_md += f"\n\n> 📖 内容已截断。详情看 `{os.path.basename(overflow_files[0])}`\n"
            if overflow_dir_path:
                final_md += f"> 📂 溢出文件夹: `{overflow_dir_path}`\n"
        final_md += "\n\n<!-- LINK_MAP\n" + json.dumps(link_map, ensure_ascii=False, indent=2) + "\n-->\n"

        return {
            "markdown": final_md,
            "linkMap": link_map,
            "overflowFiles": overflow_files,
            "stats": {
                "totalResults": 0, "keptFull": 0, "keptSummary": 0,
                "truncatedCount": 1 if overflow_text else 0,
                "overflowFileCount": len(overflow_files),
                "estimatedTokens": estimate_tokens(final_md),
            },
        }

    # 5. 有资源块 → 逐块分配 token 预算
    header_tokens = estimate_tokens(header)
    map_budget = min(len(link_map) * 100, 8000)
    content_budget = config["max_tokens"] - header_tokens - map_budget - 500
    full_budget = int(content_budget * config["full_content_ratio"])

    used_tokens = 0
    full_phase = True
    processed_blocks = []
    overflow_blocks = []
    kept_full = 0
    kept_summary = 0

    for block in blocks:
        block_md = block["title"] + "\n" + block["content"]
        block_tokens = estimate_tokens(block_md)

        if used_tokens + block_tokens <= content_budget and full_phase:
            processed_blocks.append(block_md)
            used_tokens += block_tokens
            kept_full += 1
            if used_tokens >= full_budget:
                full_phase = False
        elif used_tokens < content_budget:
            full_phase = False
            sc = block["content"]
            summary_content = sc[:config["summary_max_chars"]] + "..." if len(sc) > config["summary_max_chars"] else sc
            summary_md = block["title"] + "\n" + summary_content + "\n> 💡 *此条结果已截断，完整内容见溢出文件*\n\n"
            summary_tokens = estimate_tokens(summary_md)
            if used_tokens + summary_tokens <= content_budget:
                processed_blocks.append(summary_md)
                used_tokens += summary_tokens
                kept_summary += 1
                overflow_blocks.append(block_md)
            else:
                overflow_blocks.append(block_md)
        else:
            overflow_blocks.append(block_md)

    # 6. 组装最终 Markdown
    markdown = header + "\n\n"
    if kept_summary > 0 or overflow_blocks:
        markdown += f"> 共 **{len(blocks)}** 个资源块（前 {kept_full} 个完整，{kept_summary} 个摘要）\n\n"
    markdown += "\n".join(processed_blocks)

    # 7. 写入溢出文件
    overflow_files = []
    overflow_dir_path = None
    if overflow_blocks:
        try:
            os.makedirs(config["overflow_dir"], exist_ok=True)
            cleanup_overflow_dirs(config["overflow_dir"], config["max_overflow_dirs"] - 1)
            ts = int(time.time() * 1000)
            overflow_dir_path = os.path.join(config["overflow_dir"], f"req-{ts}")
            os.makedirs(overflow_dir_path, exist_ok=True)
            for idx, blk in enumerate(overflow_blocks):
                fname = f"{idx + 1:02d}.md"
                fpath = os.path.join(overflow_dir_path, fname)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(f"# 深度研究 - 溢出资源 #{idx + 1}\n\n> 因 token 限制被截断，此处保留完整内容。\n\n{blk}")
                overflow_files.append(fpath)
        except Exception:
            pass

        markdown += "\n---\n\n"
        markdown += f"> 📖 还有 **{len(overflow_blocks)}** 个资源块被截断，每个资源单独保存：\n"
        for fp in overflow_files:
            markdown += f"> - `{os.path.basename(fp)}`\n"
        if overflow_dir_path:
            markdown += f"> \n> 📂 溢出文件夹: `{overflow_dir_path}`\n"

    # 8. 附加链接映射表
    markdown += "\n\n<!-- LINK_MAP\n" + json.dumps(link_map, ensure_ascii=False, indent=2) + "\n-->\n"

    return {
        "markdown": markdown,
        "linkMap": link_map,
        "overflowFiles": overflow_files,
        "stats": {
            "totalResults": len(blocks),
            "keptFull": kept_full,
            "keptSummary": kept_summary,
            "truncatedCount": len(overflow_blocks),
            "overflowFileCount": len(overflow_files),
            "estimatedTokens": estimate_tokens(markdown),
        },
    }
