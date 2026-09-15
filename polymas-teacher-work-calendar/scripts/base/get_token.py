#!/usr/bin/env python3
"""Token 获取公共模块 — 通过工作流接口 oauthGetToken 换取 Token。

本模块内部走 `workflow_client.call_workflow`，不直接调 requests，
以保持整个技能内工作流域名/前置路径的唯一硬编码点在 workflow_client.py。
"""

import sys
from typing import Optional

from base.workflow_client import call_workflow

GET_TOKEN_ROUTE = "oauthGetToken"


def get_token(user_nid: str) -> Optional[str]:
    if not user_nid:
        print("获取Token失败：user_nid 为空", file=sys.stderr)
        return None

    response_data = call_workflow(
        GET_TOKEN_ROUTE,
        {"userNid": user_nid},
    )

    if not response_data:
        return None

    if response_data.get("success") and response_data.get("code") == 200:
        token = response_data.get("data")
        if isinstance(token, str) and token:
            return token
        print("获取Token失败：响应 data 为空或类型异常", file=sys.stderr)
        return None

    msg = response_data.get("msg", "未知原因")
    print(f"获取Token失败：{msg}", file=sys.stderr)
    return None
