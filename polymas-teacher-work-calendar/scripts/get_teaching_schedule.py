#!/usr/bin/env python3
"""
教学日程查询工具 — 查询教师的工作日历安排。

用法:
  python3 get_teaching_schedule.py [options]

参数:
  --type        事件类型（0=日历 1=作业 2=考试 3=AI提醒，默认0）
  --start-date  开始日期（格式: yyyy-MM-dd）
  --end-date    结束日期（格式: yyyy-MM-dd）
  --start-date  开始日期（格式: yyyy-MM-dd，未传默认今天）
  --end-date    结束日期（格式: yyyy-MM-dd，未传默认同开始日期）
  --sort-id     排序ID（可选；默认按日期自动判断：历史日期 -1，今天及未来 1；不得传 0）
  --limit       返回数量限制（默认20）

依赖环境变量:
  userId — 由运行时上下文自动注入
"""
import sys
import json
import argparse
from datetime import date
from typing import Optional, Dict, Any

from base.load_context import load_runtime_context
from base.get_token import get_token
from base.workflow_client import call_workflow

SCHEDULE_ROUTE = "getTeachingSchedule"


def resolve_sort_id(start_date: str, end_date: str, sort_id: Optional[int] = None) -> int:
    """推断 sortId 取值（不能为 0，否则接口查不出数据）。

    规则:
      1. 显式传入 sort_id 时直接使用；
      2. 日期范围整体在过去（结束日期早于今天）时返回 -1（往上划找之前的）；
      3. 其余情况（含未传日期、今天及未来）返回 1（往下滑找之后的）。
    """
    if sort_id is not None:
        return sort_id
    last_day = end_date or start_date
    if last_day and last_day < date.today().strftime("%Y-%m-%d"):
        return -1
    return 1


def get_teaching_schedule(
    user_nid: str,
    schedule_type: int = 0,
    start_date: str = "",
    end_date: str = "",
    sort_id: Optional[int] = None,
    limit: int = 20,
) -> Optional[Dict[str, Any]]:
    """查询教师教学日程安排。

    参数:
      user_nid      — 用户 ID
      schedule_type — 事件类型（0=日历 1=作业 2=考试 3=AI提醒）
      start_date    — 开始日期（yyyy-MM-dd，未传默认今天）
      end_date      — 结束日期（yyyy-MM-dd，未传默认同开始日期）
      sort_id       — 排序ID（可选；默认按日期自动判断：历史日期 -1，今天及未来 1；不得传 0）
      limit         — 数量限制（0表示不限）

    返回:
      日程列表数据。
    """
    token = get_token(user_nid)
    if not token:
        return None

    # 接口必须传日期，空日期会导致后端 SQL 报错（Incorrect DATE value: ''）
    if not start_date:
        start_date = date.today().strftime("%Y-%m-%d")
    if not end_date:
        end_date = start_date

    sort_id = resolve_sort_id(start_date, end_date, sort_id)
    payload = {
        "sortId": sort_id,
        "type": schedule_type,
        "startDate": start_date,
        "endDate": end_date,
    }
    if limit:
        payload["limit"] = limit

    return call_workflow(SCHEDULE_ROUTE, payload, token=token)


def main() -> Optional[Dict[str, Any]]:
    parser = argparse.ArgumentParser(description="教学日程查询工具")
    parser.add_argument("--type", type=int, default=0,
                        choices=[0, 1, 2, 3],
                        help="事件类型（0=日历 1=作业 2=考试 3=AI提醒，默认0）")
    parser.add_argument("--start-date", default="",
                        help="开始日期（格式: yyyy-MM-dd）")
    parser.add_argument("--end-date", default="",
                        help="结束日期（格式: yyyy-MM-dd）")
    parser.add_argument("--sort-id", type=int, default=None,
                        help="排序ID（可选；默认按日期自动判断：历史日期 -1，今天及未来 1；不得传 0）")
    parser.add_argument("--limit", type=int, default=20,
                        help="返回数量限制（默认20）")
    args = parser.parse_args()

    context = load_runtime_context()
    data = get_teaching_schedule(
        context["userId"],
        args.type,
        args.start_date,
        args.end_date,
        args.sort_id,
        args.limit,
    )
    print(json.dumps(data, ensure_ascii=False, indent=2) if data else "null")
    return data


if __name__ == "__main__":
    main()
