#!/usr/bin/env python3
"""
deep-agent-research — 纯研究执行器

所有路由决策（App选择/KB匹配/agentType/actionList/querySize）
已移至 search-router。本脚本只负责：
  1. 接收完整参数 → 调 API → 返回结果
  2. 多轮判断（should_continue）
  3. 结果压缩（compress_result）

用法（由 search-router 调用）:
    python scripts/research.py "问题" [选项]
"""

import argparse
import json
import sys
import os
from datetime import datetime
from kb_ids import get_kbids, DEFAULT_APP_CODE, DEFAULT_USER_ID

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MAX_ROUNDS =2

KB_LIST = get_kbids()

from deep_api import call_research_api



LOG = "[deep-agent-research]"


# ==================== 参数校验 ====================

VALID_AGENT_TYPES = {"chat", "write", "file", "analyze", "knowledge_only"}
VALID_ACTIONS = {"db_search", "internet"}

def validate_args(args):
    errors = []

    # query_list — 必须是合法 JSON 数组
    if not args.query_list or not args.query_list.strip():
        errors.append("query_list 不能为空")
    else:
        try:
            intent_list = json.loads(args.query_list.strip())
            if not isinstance(intent_list, list) or len(intent_list) == 0:
                errors.append("query_list 必须是非空 JSON 数组")
            else:
                for item in intent_list:
                    if not isinstance(item, dict) or "intent" not in item:
                        errors.append(f"query_list 每个元素必须包含 intent 字段，当前: {item}")
                        break
        except json.JSONDecodeError:
            errors.append(f"query_list 不是合法 JSON: {args.query_list}")

    # action_list — 强校验
    try:
        action_list = json.loads(args.action_list)
        if not isinstance(action_list, list) or len(action_list) == 0:
            errors.append(f"action-list 必须是非空 JSON 数组，当前: {args.action_list}")
    except json.JSONDecodeError:
        errors.append(f"action-list 不是合法 JSON: {args.action_list}")

    # query_size — 范围校验
    if args.query_size is not None and (args.query_size < 1 or args.query_size > 20):
        errors.append(f"query-size 必须在 1-20 之间，当前: {args.query_size}")

    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return None


# ==================== 请求构建 ====================


def build_request_params(params: dict) -> dict:
    """
    构建 API 请求参数。
    输入格式：
    {
        "intentList": [{"intent": "...", "searchList": [...]}],
        "actionList": ["db_search"],
        "parentKbIds": ["..."],
        "querySize": 5
    }
    """
    intent_list = params.get("intentList", [])
    action_list = params.get("actionList", ["db_search"])
    parent_kb_ids = params.get("parentKbIds", [])
    query_size = params.get("querySize", 5)

    # 强校验
    if not intent_list or not isinstance(intent_list, list):
        raise ValueError("intentList 不能为空且必须是列表")
    if not isinstance(action_list, list) or len(action_list) == 0:
        raise ValueError(f"actionList 必须是非空列表，当前: {action_list}")

    request_params = {
        "intentList": intent_list,
        "isImage": True,
        "actionList": action_list,
        "querySize": query_size,
    }

    if parent_kb_ids:
        request_params["parentKbIds"] = parent_kb_ids

    return request_params


# ==================== 主流程 ====================


def run_research(params: dict) -> dict:
    """执行深度研究"""
    request_params = build_request_params(params)
    api_result = call_research_api(request_params)
    return api_result
    

def write_json_file(file_path, data, indent=2):
    # 自动创建目录
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def read_json_file(file_path):
    """读取已有 JSON 文件"""
    if not file_path or not os.path.exists(file_path):
        return {"intent": [], "results": []}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def deduplicate_and_reorder(results: list) -> list:
    """去重 + 重排 order：
    1. 按 id 去重（id 相同只保留一个，优先保留先出现的）
    2. 重新分配 order（从 1 开始递增）
    """
    seen_ids = set()
    unique_results = []
    for item in results:
        item_id = item.get("id")
        if item_id is not None:
            if item_id in seen_ids:
                continue  # 跳过重复 id
            seen_ids.add(item_id)
        unique_results.append(item)
    # 重新分配 order
    for idx, item in enumerate(unique_results, start=1):
        item["order"] = str(idx)
    return unique_results


def merge_add(existing_data: dict, new_intents: list, new_results: list) -> dict:
    """新增模式：将新意图和新结果追加到已有数据中"""
    merged_intents = list(existing_data.get("intent", []))
    for intent in new_intents:
        if intent not in merged_intents:
            merged_intents.append(intent)
    combined_results = list(existing_data.get("results", [])) + new_results
    merged_results = deduplicate_and_reorder(combined_results)
    return {"intent": merged_intents, "results": merged_results}


def merge_replace_all(new_intents: list, new_results: list) -> dict:
    """全量替换模式：直接用新数据覆盖"""
    reordered_results = deduplicate_and_reorder(new_results)
    return {"intent": new_intents, "results": reordered_results}


def merge_replace_intents(existing_data: dict, replace_intents: list, new_results: list) -> dict:
    """部分替换模式：删除指定意图的旧结果，加入新结果"""
    # 过滤掉匹配指定意图的旧结果
    old_results = existing_data.get("results", [])
    filtered_results = [
        r for r in old_results
        if not any(intent in r.get("intent", []) for intent in replace_intents)
    ]
    # 合并新结果 + 去重 + 重排 order
    combined_results = filtered_results + new_results
    merged_results = deduplicate_and_reorder(combined_results)
    # intent 列表保持不变（意图没删，只是重新检索）
    return {"intent": existing_data.get("intent", []), "results": merged_results}


# ==================== CLI 入口 ====================


def main():
    parser = argparse.ArgumentParser(description="深度智能体研究（纯执行器）")
    parser.add_argument("query_list", help='意图列表 JSON，格式: [{"intent":"...","searchList":[...]}]')
    parser.add_argument("--action_list", default='["db_search","internet"]', help="数据源列表 JSON")
    parser.add_argument("--query_size", type=int, default=10, help="检索资源数量（1-20）")
    parser.add_argument("--raw_query", default="", help="用户原始 query（用于生成文件名）")
    parser.add_argument("--op", default="", help="操作类型：add/replace_all/replace_intents")
    parser.add_argument("--json_file", default="", help="目标 JSON 文件路径（用于 Task 3 直接更新）")

    args = parser.parse_args()

    err = validate_args(args)
    if err:
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    # 解析 intentList
    intent_list = json.loads(args.query_list.strip())

    # 构建参数
    params = {
        "intentList": intent_list,
        "querySize": args.query_size or 10,
    }

    # 获取 kb ids
    if KB_LIST:
        params["parentKbIds"] = KB_LIST
    else:
        params["parentKbIds"] = []

    try:
        params["actionList"] = json.loads(args.action_list)
    except json.JSONDecodeError:
        params["actionList"] = ["db_search","internet"]

    # 执行检索
    result = run_research(params)
    new_intents = [item.get("intent", "") for item in intent_list]
    new_results = result.get("result", []) if result.get("success") else []
    for i in range(len(new_results)):
        new_results[i]["order"] = str(i)
    # 确定输出路径
    if args.json_file:
        # Task 3 模式：直接更新目标 JSON 文件
        output_path = args.json_file
    else:
        # Task 2 模式：生成新文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if args.raw_query:
            file_label = args.raw_query.strip()
        else:
            file_label = "unknown"
        if len(file_label) > 50:
            file_label = file_label[:50]
        filename = f"{timestamp}_{file_label}.json"
        output_dir =  f"/app/working/{DEFAULT_APP_CODE}/{DEFAULT_USER_ID}/tmp" 
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

    # 根据 op 执行不同的写入逻辑
    if args.op == "add":
        # 新增：读取已有 JSON，追加新意图和新结果
        existing_data = read_json_file(output_path)
        output_data = merge_add(existing_data, new_intents, new_results)
    elif args.op == "replace_all":
        # 全量替换：直接覆盖
        output_data = merge_replace_all(new_intents, new_results)
    elif args.op == "replace_intents":
        # 部分替换：删除指定意图的旧结果，加入新结果
        existing_data = read_json_file(output_path)
        output_data = merge_replace_intents(existing_data, new_intents, new_results)
    else:
        # 无 op：直接写入
        output_data = {"intent": new_intents, "results": new_results}

    write_json_file(output_path, output_data)
    print(json.dumps({"success": result.get("success", False), "output": output_path}, ensure_ascii=False))
    
    return {"success": result.get("success", False), "output": output_path}


if __name__ == "__main__":
    main()
