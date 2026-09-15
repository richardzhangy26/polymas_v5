#!/usr/bin/env python3
"""
search-router — 分发 + 参数对齐 + 结果标准化

职责（仅此三件事）：
  1. 接收 Agent 传入的参数，对齐后分发给 db/web/deep
  2. 标准化各工具的返回结果为统一格式
  3. 校验出参完整性
"""

import argparse
import json
import os
import sys
import re
from concurrent.futures import ThreadPoolExecutor
import subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


LOG = "[search-router]"
SKILLS_ROOT = os.path.dirname(os.path.abspath(__file__))
WIKI_SEARCH_SCRIPT = os.path.join(SKILLS_ROOT, "search.py")
DB_SEARCH_SCRIPT = os.path.join(SKILLS_ROOT, "db_search.py")
DEEP_RESEARCH_SCRIPT = os.path.join(SKILLS_ROOT, "deep_search.py")
WEB_SEARCH_SCRIPT = os.path.join(SKILLS_ROOT, "web_search.py")

# ==================== 结果标准化 ====================

def _run_script(script_path: str, args: list, timeout: int = 60) -> dict:
    """运行 Python 脚本，返回解析后的 JSON"""
    print(f"{LOG} script_path: {script_path}", file=sys.stderr)
    if not os.path.exists(script_path):
        return {"success": False, "error": f"脚本不存在: {script_path}"}

    cmd = [sys.executable, script_path] + args
    print(cmd)
    print(f"{LOG} exec: {' '.join(cmd)}", file=sys.stderr)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(script_path),  # 在脚本目录下运行（import 路径正确）
        )

        # stderr 打印出来（调试信息）
        if proc.stderr:
            for line in proc.stderr.strip().split("\n"):
                print(f"  {line}", file=sys.stderr)

        if proc.returncode != 0:
            return {"success": False, "error": f"脚本退出码 {proc.returncode}: {proc.stderr[:500]}"}

        # 解析 stdout JSON
        stdout = proc.stdout.strip()
        if not stdout:
            return {"success": False, "error": "脚本无输出"}

        return json.loads(stdout)

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"脚本超时（{timeout}s）"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON 解析失败: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def call_wiki_search(query: str, kb_ids: list) :
    """调用 db-search

    公共参数 query_size → db-search CLI --query-size → API pageSize

    返回: { success, query, count, total, results: [...], _compressed: { markdown, linkMap, ... } }
    """
    args = [query]
    if kb_ids:
        args += ["--kb_id", str(kb_ids)]
    return _run_script(WIKI_SEARCH_SCRIPT, args, timeout=120)


def call_web_search(query: str, query_size: int = 3) -> dict:
    """调用 web-domain-search

    公共参数 query_size → web CLI --query-size → API querySize

    返回: { success, query, count, results: [...], _compressed: { markdown, linkMap, ... } }
    """
    args = [query, "--query-size", str(query_size)]
    return _run_script(WEB_SEARCH_SCRIPT, args, timeout=30)


def call_db_search(query: str, kb_ids: list,
                   text_list: list = None, with_llm: bool = False) -> dict:
    """调用 db-search

    公共参数 query_size → db-search CLI --query-size → API pageSize

    返回: { success, query, count, total, results: [...], _compressed: { markdown, linkMap, ... } }
    """
    args = [query]
    if kb_ids:
        args += ["--kb_id", str(kb_ids)]
    if text_list is not None and len(text_list) > 0:
        args += ["--text_list", json.dumps(text_list, ensure_ascii=False)]
    if with_llm:
        args.append("--with-llm")

    return _run_script(DB_SEARCH_SCRIPT, args, timeout=30)


def call_deep_research(query: str, kb_ids: list = None,
                       db_prompt: str = None, agent_type: str = None,
                       query_size: int = None, action_list: list = None,
                       no_internet: bool = False,
                       file_ids: list = None, file_names: list = None) -> dict:
    """调用 deep-agent-research

    参数对齐 research.py argparse:
      --app-id, --app-nid, --app-name, --kb-ids, --db-prompt,
      --agent-type, --action-list, --query-size, --file-ids, --file-names

    注意：research.py 没有 --mode / --user-id / --no-internet
      - mode → 映射为 --agent-type
      - user_id → 重构后不需要（路由在 search-router 完成）
      - no_internet → 通过 action_list=["db_search"] 实现

    返回: { success, text, app, result (markdown), _compressStats }
    """
    args = [query]
    if kb_ids:
        args += ["--kb_id", str(kb_ids)]
    if db_prompt:
        args += ["--db-prompt", db_prompt]
    if agent_type:
        args += ["--agent-type", agent_type]
    if query_size:
        args += ["--query-size", str(query_size)]
    # no_internet → 强制 action_list 为 db_search only
    if no_internet and not action_list:
        action_list = ["db_search"]
    if action_list:
        args += ["--action-list", json.dumps(action_list, ensure_ascii=False)]
    if file_ids:
        args += ["--file-ids", ",".join(file_ids)]
    if file_names:
        args += ["--file-names", ",".join(file_names)]
    return _run_script(DEEP_RESEARCH_SCRIPT, args, timeout=120)


def _normalize_db(result: dict) -> dict:
    c = result.get("_compressed", {})
    return {
        "success": True,
        "strategy":"serial",
        "results":{
            "markdown": c.get("markdown", ""),
            "linkMap": c.get("linkMap", {}),
            "overflowFiles": c.get("overflowFiles", []),
            "tree_view": result.get("tree_view", ""),  # tree_view 是 URL 字符串
        }
    }
def _normalize_deep(result: dict) -> dict:
    text = result.get("result", "")
    stats = result.get("_compressStats", {})
    link_map = {}
    m = re.search(r"<!-- URL_MAP\s*\n(.*?)\n\s*-->", text, re.DOTALL)
    if m:
        try:
            link_map = json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return {"markdown": text, "linkMap": link_map, "overflowFiles": [], "stats": stats}


def _normalize_web(result: dict) -> dict:
    c = result.get("_compressed", {})
    return {
        "success": True,
        "strategy": "parallel",
        "results": {
            "markdown": c.get("markdown", ""),
            "linkMap": c.get("linkMap", {}),
            "overflowFiles": c.get("overflowFiles", []),
            "tree_view": "",  # web 搜索无 tree_view
        }
    }

def _normalize_parallel(result: dict) -> dict:
    return {
        "success": True,
        "strategy": "parallel",
        "results": {
            "markdown": result.get("markdown", ""),
            "linkMap": result.get("linkMap", {}),
            "overflowFiles": result.get("overflowFiles", []),
            "tree_view": result.get("tree_view", ""),  # tree_view 是 URL 字符串
        }
    }


def _merge_parallel(db_norm_: dict, web_norm_: dict) -> dict:
    """合并 db + web 结果（parallel 模式）"""
    parts, link_map, overflow = [], {}, []
    db_norm = db_norm_.get("results", {})
    web_norm = web_norm_.get("results", {})
    tree_view = db_norm.get("tree_view", [])  # 取 db 侧的 tree_view
    if db_norm.get("markdown"):
        parts.append("# 📄 知识库检索\n\n" + db_norm["markdown"])
        link_map.update(db_norm.get("linkMap", {}))
        overflow.extend(db_norm.get("overflowFiles", []))

    if web_norm.get("markdown"):
        web_md = web_norm["markdown"]
        web_lm = web_norm.get("linkMap", {})
        # linkMap key 冲突时 web 侧加 W 前缀
        remap = {}
        for k, v in web_lm.items():
            if k in link_map:
                new_key = f"W{k}"
                remap[k] = new_key
                link_map[new_key] = v
            else:
                link_map[k] = v
        for old, new in sorted(remap.items(), key=lambda x: -len(x[0])):
            web_md = re.sub(r'\b' + re.escape(old) + r'\b', new, web_md)
        parts.append("## 🌐 互联网搜索\n\n" + web_md)
        overflow.extend(web_norm.get("overflowFiles", []))

    ds = db_norm.get("stats", {})
    ws = web_norm.get("stats", {})
    return {
        "markdown": "\n\n---\n\n".join(parts),
        "linkMap": link_map,
        "overflowFiles": overflow,
        "tree_view": tree_view,
        "stats": {
            "totalResults": (ds.get("totalResults", 0) or 0) + (ws.get("totalResults", 0) or 0),
            "estimatedTokens": (ds.get("estimatedTokens", 0) or 0) + (ws.get("estimatedTokens", 0) or 0),
            "dbResults": ds.get("totalResults", 0) or 0,
            "webResults": ws.get("totalResults", 0) or 0,
        },
    }


# ==================== 分发执行 ====================

def execute(params: dict) -> dict:
    """按 Agent 指定的 strategy 直接分发，不做判断。"""
    kb_id = params.get("kb_id","")
    query = params.get("query")
    strategy = params.get("strategy", "serial")
    text_list = params.get("text_list", "[]")
    # 确保 text_list 是 list 类型
    if isinstance(text_list, str):
        try:
            text_list = json.loads(text_list)
        except json.JSONDecodeError:
            text_list = []
    if not isinstance(text_list, list):
        text_list = []
    qs = params.get("query_size", 5)
    meta = {"layers_executed": []}

    # --- serial: 只执行 db，结果够不够由 Agent 判断 ---
    if strategy == "serial":
        print(f"{LOG} exec: wiki-search", file=sys.stderr)
        wiki_result = call_wiki_search(query, kb_id)
        print(f"{LOG} wiki-search result: success={wiki_result.get('success')}, total={wiki_result.get('total', '?')}", file=sys.stderr)
        if wiki_result.get("success") and wiki_result.get("results"):
            result = wiki_result
        else:
            if not wiki_result.get("success"):
                print(f"{LOG} wiki-search failed: {wiki_result.get('error', 'unknown')}", file=sys.stderr)
            print(f"{LOG} exec: db-search", file=sys.stderr)
            result = call_db_search(query, kb_id, text_list)
            print(f"{LOG} db-search result: success={result.get('success')}, total={result.get('total', '?')}", file=sys.stderr)
        meta["layers_executed"].append("db")
        meta["dbTotal"] = result.get("total", 0) if result.get("success") else 0
        if result.get("success"):
            return _normalize_db(result)
        else:
            return _err(result, meta, params)

    # --- external_only: 直接 web ---
    if strategy == "external_only":
        print(f"{LOG} exec: web-search", file=sys.stderr)
        result = call_web_search(query, qs)
        meta["layers_executed"].append("web")
        if result.get("success"):
            return _normalize_web(result)
        else:
            return _err(result, meta, params)

    if strategy == "deep_only":
        print(f"{LOG} exec: deep-search", file=sys.stderr)
        result = call_deep_research(query, kb_id)
        print(f"{LOG} deep-search result: success={result.get('success')}", file=sys.stderr)
        meta["layers_executed"].append("deep")
        if result.get("success"):
            return _normalize_deep(result)
        else:
            return _err(result, meta, params)

    if strategy == "parallel":
        print(f"{LOG} exec: db + web parallel", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=3) as pool:
            db_f = pool.submit(call_wiki_search, query, kb_id)
            old_db_f = pool.submit(call_db_search, query, kb_id,text_list)
            web_f = pool.submit(call_web_search, query, qs)
            db_r, web_r,old_db_r = db_f.result(), web_f.result(),old_db_f.result()
        meta["layers_executed"] = ["db", "web"]
        meta["dbTotal"] = db_r.get("total", 0) if db_r.get("success") else 0
        final_db_r = db_r
        if meta["dbTotal"] == 0 and old_db_r.get("success"):
            meta["dbTotal"] = old_db_r.get("total", 0)
            final_db_r = old_db_r
        meta["webCount"] = web_r.get("count", 0) if web_r.get("success") else 0
        db_n = _normalize_db(final_db_r) if final_db_r.get("success") else {"success":True,"results":{"markdown": "", "linkMap": {}, "stats": {}}}
        web_n = _normalize_web(web_r) if web_r.get("success") else {"success":True,"results":{"markdown": "", "linkMap": {}, "stats": {}}}
        return _normalize_parallel(_merge_parallel(db_n, web_n))



    # 兜底：未知策略当 serial
    print(f"{LOG} 未知策略 '{strategy}'，降级为 serial", file=sys.stderr)
    params['strategy'] = "serial"
    return execute(params)



# ==================== 输出构建 ====================




def _err(result: dict, meta: dict, params: dict) -> dict:
    return {
        "success": False,
        "error": result.get("error", "未知错误"),
        "strategy": meta.get("strategy", "serial"),
        "layers": meta.get("layers_executed", []),
        "routing": meta
    }


# ==================== CLI 入口 ====================

def main():
    parser = argparse.ArgumentParser(description="search-router")
    parser.add_argument("query", default="", help="改写后的检索 query")
    parser.add_argument("kb_id", nargs="?", default="", help="逗号分隔")
    parser.add_argument("--strategy", default="parallel")
    parser.add_argument("--text_list", default="[]")


    args, unknown_args = parser.parse_known_args()

    query = args.query if args.query else ""
    if not query:
        print(json.dumps({"success": False, "error": "缺少 text 参数"}, ensure_ascii=False))
        sys.exit(1)
    # 5. 构建参数 + 执行
    params = {
        "query": query,
        "kb_id": args.kb_id,
        "strategy": args.strategy,
        "text_list": args.text_list
    }
    result = execute(params)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
