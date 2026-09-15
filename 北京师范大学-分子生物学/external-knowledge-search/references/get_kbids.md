## 子技能说明

该技能用于获取当前用户可用的知识库（apps）列表，作为后续检索 `kb_id` 的来源。

**核心功能**：
- 从 `metadata`（JSON 字符串）与环境变量中加载用户运行时上下文
- 调用用户配置 API（`USER_INFO_API_BASE_URL`）获取该用户绑定的应用与知识库列表
- 以 `{ "apps": [...] }` 结构输出，供路由阶段选择 `kb_id`

**返回信息包括**：
- 应用基本信息：appId、name、description、dbPrompt
- 知识库列表：knowledgeBases（字符串数组）

**使用场景**：
- 检索流程开始前，需要确定使用哪个知识库
- 反思阶段需要切换到其他候选知识库时

**用户角色**：登录态用户（依赖 `userId`）

---

## 触发条件

当满足以下任一条件时调用该脚本：

1. 检索流程开始（Step 1 [PREPARE]），尚未确定 `kb_id`
2. 反思阶段需要切换知识库
3. 用户主动询问可用知识库（如 "我有哪些知识库？"）

---

## 不触发条件

1. 当前会话已通过同一阶段获取到知识库列表（同一轮会话首次调用一次即可）
2. 用户已显式提供 `kb_id`

---

## 参数定义

### 环境变量

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| metadata | JSON string | ✅ | 至少包含 `msgKey`、`msgId` 字段 |
| userId | string | ✅ | 当前用户 ID |
| toNid | string | ✅ | 目标节点 ID |
| traceId | string | ✅ | 链路追踪 ID |
| USER_INFO_API_BASE_URL | string | ❌ | 用户配置 API 地址，默认 `http://kb-memory-api.polymas.com` |

---

## 返回定义

### 成功响应

```json
{
  "apps": [
    {
      "appId": "string，应用 ID",
      "name": "string，应用名称",
      "description": "string，应用描述",
      "dbPrompt": "string，知识库 prompt 提示词",
      "knowledgeBases": ["string，知识库 ID 列表"]
    }
  ]
}
```

### 失败响应

```json
{ "apps": { "knowledgeBases": "" } }
```

**常见失败原因**：
- 缺少 `userId` 环境变量
- `metadata` 不是合法 JSON 或缺少必填字段
- 用户配置 API 调用异常（网络错误、超时、HTTP 错误）

---

## 执行流程

**Step 1 [LOAD]: 加载运行时上下文**

1. 执行逻辑：从环境变量加载 `metadata`、`userId`、`toNid`、`traceId`
2. 终止条件：
   - `metadata` 不存在或非法 → 返回空上下文
   - 关键字段缺失 → 打印 `缺少必要环境变量字段：...` 并返回空上下文

---

**Step 2 [FETCH]: 调用用户配置 API**

1. 执行逻辑：以 `GET` 方式访问 `{USER_INFO_API_BASE_URL}/api/apps/config?userId={userId}&include_user=true`
2. 终止条件：
   - 任意异常 → 返回空 `apps` 列表

---

**Step 3 [BUILD]: 构建响应**

1. 执行逻辑：将 `data.apps` 包装为 `{ "apps": [...] }` 后输出到 stdout
2. 终止条件：无

---

## 执行流程强制约束

- 所有 **[LOAD]** 步骤触发终止条件时，必须返回非空 JSON（即使 `apps` 为空），避免上游 JSON 解析失败
- 严格按照执行流程顺序执行
- 错误信息打印到 stderr，stdout 仅输出最终 JSON
