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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
MAX_ROUNDS =2


from deep_api import call_research_api, call_internet_rag_api
from deep_compress_result import compress_result


LOG = "[deep-agent-research]"


def should_continue(params: dict, round_num: int, max_rounds: int = 2) -> dict:
    """判断是否需要继续研究"""
    if round_num >= max_rounds:
        return {"continue": False, "reason": f"已达最大轮数（{max_rounds}轮）"}

    if round_num == 1:
        action_list = params.get("actionList", [])
        needs_internet = isinstance(action_list, list) and "internet" in action_list
        if needs_internet and params.get("forceFollowUp") is not False:
            return {"continue": True, "reason": "第一轮结果不足，准备联网补充"}
        return {"continue": False, "reason": "第一轮结果充分"}

    return {"continue": False, "reason": "默认单轮完成"}

def refine_params(params: dict, decision: dict, round_num: int) -> dict:
    """修正下一轮参数"""
    next_params = dict(params)
    current_qs = int(next_params.get("querySize", 5))

    if round_num == 1:
        next_params["querySize"] = max(current_qs * 2, 10)
        al = next_params.get("actionList", [])
        if not isinstance(al, list) or "internet" not in al:
            next_params["actionList"] = ["db_search", "internet"]
    else:
        next_params["querySize"] = max(current_qs + 10, 20)

    return next_params

# ==================== 参数校验 ====================


VALID_AGENT_TYPES = {"chat", "write", "file", "analyze", "knowledge_only"}
VALID_ACTIONS = {"db_search", "internet"}


def validate_args(args):
    errors = []

    # text — 强校验：非空且有实际内容
    if not args.query or not args.query.strip():
        errors.append("text（问题）不能为空")

    # action_list — 强校验：必须是合法 JSON 数组，元素只能是 db_search / internet
    try:
        action_list = json.loads(args.action_list)
        if not isinstance(action_list, list) or len(action_list) == 0:
            errors.append(f"action-list 必须是非空 JSON 数组，当前: {args.action_list}")
        else:
            invalid = [a for a in action_list if a not in VALID_ACTIONS]
            if invalid:
                errors.append(f"action-list 含非法值: {invalid}，合法值: {sorted(VALID_ACTIONS)}")
    except json.JSONDecodeError:
        errors.append(f"action-list 不是合法 JSON: {args.action_list}")

    # query_size — 范围校验
    if args.query_size is not None and (args.query_size < 1 or args.query_size > 20):
        errors.append(f"query-size 必须在 1-20 之间，当前: {args.query_size}")

    # agent_type — 合法值校验
    if args.agent_type and args.agent_type not in VALID_AGENT_TYPES:
        errors.append(f"agent-type 非法: {args.agent_type}，合法值: {sorted(VALID_AGENT_TYPES)}")

    if errors:
        return {"success": False, "error": "; ".join(errors)}
    return None


# ==================== 请求构建 ====================


def build_request_params(params: dict) -> dict:
    """
    构建 API 请求参数。
    所有决策参数（app_id, kb_ids, agent_type, action_list, query_size）
    由 search-router 传入，此处直接使用。
    """
    text = params["text"]
    app_code = params.get("app_id", "")
    app_nid = params.get("app_nid") or app_code
    agent_type = params.get("agent_type", "chat")
    action_list = params.get("action_list") or []
    query_size = params.get("query_size", 5)

    # 强校验（text / appCode / actionList 三个 API 必填字段）
    if not text or not str(text).strip():
        raise ValueError("text 不能为空")
    if not isinstance(action_list, list) or len(action_list) == 0:
        raise ValueError(f"action_list 必须是非空列表，当前: {action_list}")
    invalid_actions = [a for a in action_list if a not in VALID_ACTIONS]
    if invalid_actions:
        raise ValueError(f"action_list 含非法值: {invalid_actions}")

    first_action = action_list[0] if action_list else "db_search"
    parent_kb_ids = params.get("parent_kb_ids", [])
    db_prompt = params.get("db_prompt", "")
    history = params.get("history", [])
    file_ids = params.get("file_ids", [])
    file_names = params.get("file_names", [])

    request_params = {
        "text": text,
        "appCode": app_code,
        "appNid": app_nid,
        "agentType": agent_type,
        "actionList": action_list,
        "firstAction": first_action,
        "history": history,
        "querySize": query_size,
        "isHistoryCompress": True,
        "isFileLimit": False,
        "isJumpDeep": True,
        "isJumpFile": True,
    }

    # 知识库参数
    if parent_kb_ids:
        request_params["parentKbIds"] = parent_kb_ids
        request_params["dbPrompt"] = db_prompt
        if agent_type in ("chat", "write"):
            request_params["isResearchThink"] = False
            request_params["isIntentThink"] = False

    # 文件参数
    if file_ids:
        request_params["fileIds"] = file_ids
        request_params["fileName"] = file_names
        if agent_type == "file":
            if not parent_kb_ids:
                request_params.pop("parentKbIds", None)
                request_params.pop("dbPrompt", None)
            request_params["fastVersion"] = False
            request_params["isImage"] = False

    return request_params


# ==================== 主流程 ====================


def run_research(params: dict) -> dict:
    """执行深度研究（支持多轮）"""
    working_params = dict(params)
    formatted_result = ""

    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"{LOG} === 第 {round_num} 轮 ===", file=sys.stderr)

        try:
            request_params = build_request_params(working_params)
        except ValueError as e:
            return {"success": False, "error": f"参数校验失败: {e}"}

        # 第2轮 + 需要联网 → 联网补充 API
        needs_internet = isinstance(request_params.get("actionList"), list) and "internet" in request_params["actionList"]

        if round_num >= 2 and needs_internet:
            print(f"{LOG} 联网补充模式", file=sys.stderr)
            api_result = call_internet_rag_api(request_params)
        else:
            api_result = call_research_api(request_params)
        if api_result.get("success") is False:
            return api_result

        result = api_result.get("data", {}).get("result", "")
        if isinstance(result, dict):
            formatted_result = json.dumps(result, ensure_ascii=False)
        else:
            formatted_result = str(result)

        decision = should_continue(working_params, round_num, MAX_ROUNDS)
        if not decision["continue"] or round_num >= MAX_ROUNDS:
            break

        print(f"{LOG} 继续: {decision['reason']}", file=sys.stderr)
        working_params = refine_params({**working_params, **request_params}, decision, round_num)

    # 压缩处理
    compressed_markdown = formatted_result
    compress_stats = {}
    try:
        compressed = compress_result(formatted_result)
        compressed_markdown = compressed["markdown"]
        compress_stats = compressed["stats"]
        print(f"{LOG} 压缩: {compress_stats.get('keptFull', 0)} 完整, "
              f"{compress_stats.get('keptSummary', 0)} 摘要, "
              f"{compress_stats.get('truncatedCount', 0)} 溢出, "
              f"~{compress_stats.get('estimatedTokens', 0)} tokens", file=sys.stderr)
    except Exception as e:
        print(f"{LOG} 压缩失败（降级）: {e}", file=sys.stderr)

    return {
        "success": True,
        "text": params["text"],
        "app": params.get("app_name", ""),
        "result": compressed_markdown,
        "_compressStats": compress_stats,
    }


# ==================== CLI 入口 ====================


def main():
    parser = argparse.ArgumentParser(description="深度智能体研究（纯执行器）")
    parser.add_argument("query", nargs="?", help="用户问题")
    parser.add_argument("--kb_id", default="", help="知识库ID（逗号分隔）")
    parser.add_argument("--agent_type", default="chat", help="代理类型：chat/write/file")
    parser.add_argument("--action_list", default='["db_search"]', help="数据源列表 JSON")
    parser.add_argument("--query_size", type=int, default=5, help="检索资源数量（1-20）")

    args = parser.parse_args()

    err = validate_args(args)
    if err:
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    # 构建参数
    params = {
        "text": args.query.strip(),
        "app_id": "",
        "app_nid": "",
        "app_name": "",
        "agent_type": args.agent_type,
        "query_size": args.query_size or 5,
        "db_prompt": "",
    }

    # 解析列表参数
    if args.kb_id:
        params["parent_kb_ids"] = [args.kb_id.strip() if args.kb_id.strip() else ""]
    else:
        params["parent_kb_ids"] = []

    try:
        params["action_list"] = json.loads(args.action_list)
    except json.JSONDecodeError:
        params["action_list"] = ["db_search"]

    result = run_research(params)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
