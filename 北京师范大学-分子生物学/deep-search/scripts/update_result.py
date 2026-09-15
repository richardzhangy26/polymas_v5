#!/usr/bin/env python3
"""
update_result.py — JSON 结果文件管理工具

负责管理 deep_search.py 生成的 JSON 文件。

文件结构：
{
  "intent": ["意图1", "意图2"],
  "results": [
    {"intent": ["意图1"], "order": "1", "title": "...", ...},
    {"intent": ["意图1", "意图2"], "order": "2", "title": "...", ...}
  ]
}

操作：
  --op annotate_intents   将覆盖检查的意图标注写回每条检索结果
  --op delete             删除指定意图（从 intent 列表和结果的 intent 字段中移除）
"""

import argparse
import json
import sys
import os


def load_json(file_path):
    """读取 JSON 文件"""
    if not os.path.exists(file_path):
        return {"intent": [], "results": []}
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {"intent": [], "results": []}
    return data


def save_json(file_path, data):
    """保存 JSON 文件"""
    dir_path = os.path.dirname(file_path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def op_annotate_intents(data: dict, coverage_json: str) -> dict:
    """将覆盖检查的意图标注写回每条检索结果。

    coverage_json 是 coverage_check.md Step 3 输出的 JSON 字符串，格式：
    {
      "coverage_details": [
        {"intent": "意图1", "status": "covered", "matched_orders": ["1", "3"]},
        {"intent": "意图2", "status": "partial", "matched_orders": ["2"]}
      ]
    }

    逻辑：根据 matched_orders 反向构建 order -> [intent] 映射，写入每条结果的 intent 字段。
    """
    try:
        coverage_data = json.loads(coverage_json)
    except json.JSONDecodeError:
        return {"success": False, "error": f"coverage_json 不是合法 JSON"}

    coverage_details = coverage_data.get("coverage_details", [])

    # 构建 order -> [intent] 反向映射
    order_intent_map = {}
    for detail in coverage_details:
        intent = detail.get("intent", "")
        matched_orders = detail.get("matched_orders", [])
        for order in matched_orders:
            order_str = str(order)
            if order_str not in order_intent_map:
                order_intent_map[order_str] = []
            order_intent_map[order_str].append(intent)

    # 写回主 JSON
    results = data.get("results", [])
    filtered_results = []
    removed_count = 0
    for item in results:
        order = str(item.get("order", ""))
        if order in order_intent_map:
            item["intent"] = order_intent_map[order]
            filtered_results.append(item)
        else:
            removed_count += 1
    for idx, item in enumerate(filtered_results, start=1):
        item["order"] = str(idx)

    data["results"] = filtered_results


    return {
        "success": True,
        "op": "annotate_intents",
        "updated_count": len(filtered_results),
        "message": f"已为 {len(filtered_results)} 条结果写入 intent 标注"
    }


def op_delete(data: dict, intent: str) -> dict:
    """删除指定意图。

    逻辑：
    1. 从顶层 intent 列表中移除该意图
    2. 从每条结果的 intent 字段中移除该意图
    3. 如果某结果的 intent 变为空列表，则删除该结果
    4. 重新排列剩余结果的 order
    """
    # 1. 从顶层 intent 列表移除
    intent_list = data.get("intent", [])
    if intent not in intent_list:
        return {"success": False, "error": f"未找到意图: {intent}"}
    intent_list.remove(intent)

    # 2 & 3. 从每条结果中移除该意图，空则删除
    results = data.get("results", [])
    filtered_results = []
    removed_count = 0
    for item in results:
        item_intents = item.get("intent", [])
        if intent in item_intents:
            item_intents.remove(intent)
        # 如果该结果不再关联任何意图，则删除
        if len(item_intents) == 0:
            removed_count += 1
        else:
            filtered_results.append(item)

    # 4. 重新排列 order
    for idx, item in enumerate(filtered_results, start=1):
        item["order"] = str(idx)

    data["intent"] = intent_list
    data["results"] = filtered_results

    return {
        "success": True,
        "op": "delete",
        "intent": intent,
        "removed_count": removed_count,
        "remaining_intents": intent_list,
        "message": f"已删除意图 [{intent}]，移除 {removed_count} 条结果，剩余 {len(intent_list)} 个意图"
    }


def main():
    parser = argparse.ArgumentParser(description="JSON 结果文件管理工具")
    parser.add_argument("--file", required=True, help="目标 JSON 文件路径")
    parser.add_argument("--op", required=True, choices=["annotate_intents", "delete"],
                        help="操作类型：annotate_intents/delete")
    parser.add_argument("--intent", help="意图描述（用于 delete）")
    parser.add_argument("--annotation-data", help="覆盖检查返回的 coverage_details JSON 字符串（用于 annotate_intents）")

    args = parser.parse_args()

    # 加载现有数据
    data = load_json(args.file)

    # 执行操作
    if args.op == "annotate_intents":
        if not args.annotation_data:
            print(json.dumps({"success": False, "error": "annotate_intents 操作必须提供 --annotation-data"}, ensure_ascii=False))
            sys.exit(1)
        result = op_annotate_intents(data, args.annotation_data)

    elif args.op == "delete":
        if not args.intent:
            print(json.dumps({"success": False, "error": "delete 操作必须提供 --intent"}, ensure_ascii=False))
            sys.exit(1)
        result = op_delete(data, args.intent)

    # 保存文件
    if result.get("success"):
        save_json(args.file, data)

    # 输出结果
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
