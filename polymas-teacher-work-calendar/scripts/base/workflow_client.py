#!/usr/bin/env python3
"""工作流调用公共模块 — 本技能内所有工作流接口的唯一入口。

本文件是本技能内 **唯一** 硬编码工作流域名与前置路径的位置，
后续换域名只需修改 `WORKFLOW_BASE_URL`。所有业务脚本、鉴权脚本
（get_token.py）都通过 `call_workflow` 发起 HTTP 调用。

网关侧所有 workflow 接口**统一使用 POST**，本客户端不再暴露 method 参数。

调用示例：
  from base.workflow_client import call_workflow
  result = call_workflow("getTeachingSchedule", {"sortId": 0, "type": 0, "startDate": "...", "endDate": "...", "limit": ""}, token=token)

返回值：解析后的 JSON dict；网络异常或解析失败返回 None（错误详情打印到 stderr）。
"""

import requests
import sys
from typing import Optional, Dict, Any

WORKFLOW_BASE_URL = "https://cloudapi.polymas.com/bridge/service/main/skill"
TIMEOUT = 60


def call_workflow(
    route: str,
    payload: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None,
    timeout: int = TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """调用工作流接口。

    参数:
      route   — 工作流路由名称（如 getTeachingSchedule）
      payload — 请求参数（JSON body）
      token   — 用户鉴权 Token（由 get_token 获取）
      timeout — 超时秒数

    返回:
      工作流完整响应数据（字典）。
      失败时返回 None。
    """
    url = f"{WORKFLOW_BASE_URL}/{route}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token

    try:
        response = requests.post(url, json=payload or {}, headers=headers, timeout=timeout)
        print(f"工作流 [{route}] 状态码: {response.status_code}", file=sys.stderr)
        print(f"工作流 [{route}] 响应头: {dict(response.headers)}", file=sys.stderr)
        response.raise_for_status()
        text = response.text
        print(f"工作流 [{route}] 响应体长度: {len(text)}, 内容: {text[:1000]}", file=sys.stderr)
        if not text or not text.strip():
            print(f"工作流 [{route}] 响应体为空", file=sys.stderr)
            return None
        try:
            return response.json()
        except Exception:
            print(f"工作流 [{route}] 响应体非 JSON: {text[:500]}", file=sys.stderr)
            return None
    except requests.exceptions.RequestException as e:
        print(f"工作流 [{route}] 网络错误：{e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"工作流 [{route}] 调用异常：{e}", file=sys.stderr)
        return None
