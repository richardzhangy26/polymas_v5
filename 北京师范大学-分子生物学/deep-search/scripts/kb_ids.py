
from __future__ import annotations
import json
import os
import sys
# ==================== 路径 ====================

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.dirname(SKILL_DIR)


# 缓存 TTL
CACHE_TTL = 1 * 60 * 60  # 1 小时


def _val(key: str, fallback: str = "") -> str:
    return os.environ.get(key) or fallback


def load_runtime_context() -> dict:
    metadata_raw = os.getenv("metadata", "")
    if not metadata_raw:
        return {
            "msgKey": "",
            "msgId": "",
            "traceId": "",
            "userId": "",
            "toNid": "",
        }
    try:
        metadata = json.loads(metadata_raw)
    except json.JSONDecodeError as e:
        return {
            "msgKey": "",
            "msgId": "",
            "traceId": "",
            "userId": "",
            "toNid": "",
        }

    if not isinstance(metadata, dict):
        return {
            "msgKey": "",
            "msgId": "",
            "traceId": "",
            "userId": "",
            "toNid": "",
        }

    msg_key = metadata.get("msgKey")
    msg_id = metadata.get("msgId")
    user_id = os.getenv("userId", "")
    to_nid = os.getenv("toNid", "")
    trace_id = os.getenv("traceId", "")

    missing = []
    if not msg_key:
        missing.append("metadata.msgKey")
    if not msg_id:
        missing.append("metadata.msgId")
    if not user_id:
        missing.append("userId")
    if not to_nid:
        missing.append("toNid")
    if not trace_id:
        missing.append("traceId")

    if missing:
        missing_text = "、".join(missing)
        print(f"缺少必要环境变量字段：{missing_text}")
        return {
            "msgKey": "",
            "msgId": "",
            "traceId": "",
            "userId": "",
            "toNid": "",
        }

    return {
        "msgKey": msg_key,
        "msgId": msg_id,
        "traceId": trace_id,
        "userId": user_id,
        "toNid": to_nid,
    }

# ==================== API 端点（自包含） ====================
# 用户基本信息
USER_BASE = _val("USER_INFO_API_BASE_URL", "http://kb-memory-api.polymas.com")

# 默认值
# DEFAULT_KB_ID = _val("KNOWLEDGE_ID", "")
DEFAULT_USER_ID = load_runtime_context().get("userId","")
DEFAULT_APP_CODE = load_runtime_context().get("toNid","")


# ==================== API 调用 ====================
def _fetch_from_api(user_id: str, agent_id: str, method: str = "GET"):
    """从 API 获取用户配置（apps + user info）

    支持 GET 和 POST 两种方式：
    - GET:  query string 传参
    - POST: JSON body 传参
    """
    import urllib.request
    import urllib.error

    method = method.upper()
    headers = {"Content-Type": "application/json"}
    body = None

    if method == "POST":
        url = f"{USER_BASE}/api/apps/config"
        body = json.dumps({"userId": user_id, "include_user": True}).encode("utf-8")
    else:
        if agent_id:
            url = f"{USER_BASE}/api/knowledge/base/queryUserKnowledgeBase?userNid={user_id}&agentNid={agent_id}"
        else:
            url = f"{USER_BASE}/api/knowledge/base/queryUserKnowledgeBase?userNid={user_id}"
    try:
        print(url)
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        # 标准的 code | status | data 结构，且 data 中必须包含 apps 列表才认为成功
        _data = result.get("data")
        # 如果userId不在里面 补进去
        return _data
    except Exception:
        return []



# ==================== 公开接口 ====================

def get_kbids():
    # 1. API（_fetch_from_api 内部已构建双向映射）
    if DEFAULT_USER_ID:
        api_result = _fetch_from_api(DEFAULT_USER_ID,DEFAULT_APP_CODE)
        kb_lists_ = [res.get("kbId", "") for res in api_result]
        kb_lists_ = list(set(kb_lists_))
    else:
        kb_lists_ = []

    return kb_lists_


