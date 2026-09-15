# Agent 浏览器工具调研：复用登录态、网络请求与脚本化

调研日期：2026-09-07。依据官方仓库当前主分支、官方文档及部分源码；这是资料核实，不是本机兼容性实测。主分支能力可能领先已安装版本，部署时应核对 `--help` 并固定验证过的版本。

## 结论

针对“继续使用我已经登录的浏览器，分析网页请求，再把固定工作做成脚本”，优先试 **Microsoft Playwright CLI**；需要深入检查请求与响应时搭配 **Chrome DevTools MCP**。这两项分别覆盖操作固化和网络诊断。偏好直接编写 Playwright 代码时，可选 Playwriter；偏好 Shell 和 HAR 网络归档时，可选 agent-browser。

上述排序是根据功能与本需求的匹配度作出的判断，不是速度、稳定性或成功率跑分。

## 必须区分的登录态复用方式

| 方式 | 含义 | 对本需求的适配 |
|---|---|---|
| 附加到正在运行的浏览器 | 扩展授权或 CDP 连接，操作已有页面及会话 | 最直接；通常不必重新登录 |
| 自动化专用持久化 Profile | 单独浏览器首次登录，以后继续使用 | 适合固定任务，但首次不等于复用日常浏览器 |
| 导入 storage state | 将 Cookie、部分网页存储等载入另一会话 | 有效范围取决于网站认证机制，不等于完整浏览器克隆 |

Playwright 官方明确支持加载认证状态，也说明状态会过期，浏览器特定认证需要区别处理。来源：[认证文档](https://playwright.dev/docs/auth)。

Chrome 136 起，给默认日常配置目录简单加 `--remote-debugging-port=9222` 已不是通用可行方案；传统调试参数要求非默认 `--user-data-dir`。Chrome 144 提供了通过 `chrome://inspect/#remote-debugging` 开启、由用户允许连接的路径。两条路径不要混淆。来源：[Chrome 136 变更](https://developer.chrome.com/blog/remote-debugging-port)、[现有浏览器连接指南](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/advanced-usage.md)。

## 重点比较

| 工具 | 接入方式 | 复用现有浏览器 | 网络能力 | 脚本化与取舍 |
|---|---|---|---|---|
| Microsoft Playwright CLI | CLI + Skill | 扩展或 CDP attach | 请求列表与详情；可执行 Playwright 代码扩展处理 | 支持录制用户操作并输出 Playwright 代码、执行代码文件；优先候选 |
| Chrome DevTools MCP / 官方 CLI | MCP；实验性 CLI | `--autoConnect` 或调试地址 | 请求头、响应头、请求正文、响应正文，可保存正文文件 | MCP 适合探索；CLI 可进入 Shell 工作流，但官方仍标注实验性 |
| agent-browser | 以 CLI 为主 | `--auto-connect` 或 `connect` / `--cdp` | 请求列表、完整详情、HAR、请求拦截和 mock | 适合 Shell 串联、JSON 输出与流量归档 |
| Playwright MCP | MCP | `--extension` 或 `--cdp-endpoint` | 当前工具定义支持请求列表、单请求完整 headers/body 与保存文件 | 适合只提供 MCP 接口的 Agent；代码执行工具可扩展流程 |
| Playwriter | CLI + MCP + 浏览器扩展 | 授权现有 Chrome 标签页 | Playwright response 监听；可使用 Playwright 响应读取 API 与原始 CDP | 适合直接编写可复用 Playwright 逻辑；需安装扩展并启用目标页 |
| 原生 Playwright SDK | JS/TS 或 Python 库 | Chromium `connectOverCDP` | request/response 事件、等待响应、路由与 mock | 适合最终固定脚本；需要 Agent 编写连接、定位和错误处理 |

来源：[Playwright CLI](https://github.com/microsoft/playwright-cli)、[Chrome 工具参考](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md)、[Chrome CLI](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/cli.md)、[agent-browser 命令](https://github.com/vercel-labs/agent-browser/blob/main/skill-data/core/references/commands.md)、[agent-browser 连接说明](https://github.com/vercel-labs/agent-browser#cdp-mode)、[Playwright 网络 API](https://playwright.dev/docs/network)。

许可证：Playwright CLI、Chrome DevTools MCP、agent-browser 的官方仓库均标注 Apache-2.0。来源：[Playwright CLI LICENSE](https://github.com/microsoft/playwright-cli/blob/main/LICENSE)、[Chrome LICENSE](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/LICENSE)、[agent-browser LICENSE](https://github.com/vercel-labs/agent-browser/blob/main/LICENSE)。

补充来源：Playwright MCP 的当前 [工具定义原文](https://raw.githubusercontent.com/microsoft/playwright-mcp/main/README.md) 与 [官方扩展说明](https://github.com/microsoft/playwright/tree/main/packages/extension)；Playwriter 的 [README](https://github.com/remorses/playwriter) 与 [Playwright Response API](https://playwright.dev/docs/api/class-response)。Playwriter 的响应体能力判断基于其公开的 Playwright 接口，未做站点实测。许可证分别是 [Playwright MCP Apache-2.0](https://github.com/microsoft/playwright-mcp/blob/main/LICENSE)、[Playwriter MIT](https://github.com/remorses/playwriter/blob/main/LICENSE)。

Browser Use 作为备选：其 [真实浏览器文档](https://docs.browser-use.com/open-source/customize/browser/real-browser) 支持系统 Chrome Profile 复用，但提示可能需要关闭 Chrome，不能理解为保证原窗口无缝接管。同组织新的 [Browser Harness](https://github.com/browser-use/browser-harness) 提供现有浏览器 CDP、CLI 与 MCP；本次未完整核实其专用网络捕获与录制能力，因此不与上表主要候选给出相同确认等级。

资料冲突处理：Playwriter README 中对 Playwright CLI/MCP 的部分登录态比较，与 Microsoft 当前 attach/extension 官方说明不一致。本报告采用每个工具自己的官方能力描述，不沿用其他项目对竞争工具的旧结论。

## 推荐如何落地

### 1. 优先验证 Playwright CLI 的闭环

以下是官方命令构成的操作示意，本次没有执行安装、连接或录制。

```bash
npm install -g @playwright/cli@latest
playwright-cli --help

# 两种连接方式择一；扩展方式需先安装并授权官方扩展。
playwright-cli attach --extension=chrome
# 或：先在 chrome://inspect/#remote-debugging 开启调试，再执行：
# playwright-cli attach --cdp=chrome

playwright-cli snapshot
playwright-cli recording-start
# 在已连接页面完成一段固定操作。
playwright-cli recording-stop

playwright-cli requests
# 使用列表中真实的请求编号：playwright-cli request <index>

# 让 Agent 整理录制结果，保存成受支持的函数表达式文件后执行：
# playwright-cli run-code --filename=./my-script.js

playwright-cli detach
```

`recording-stop` 输出的是代码起点，还需参数化输入、增加结果断言、处理登录过期和异常。`run-code --filename` 接受单个函数表达式，不接受任意带 `import/export/require` 的 Node 程序；独立程序应改用原生 Playwright SDK 运行。`detach` 保留外部浏览器。来源：[CLI README](https://github.com/microsoft/playwright-cli)、[代码文件执行格式](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/references/running-code.md)。

不同连接方式的前提以 [官方会话管理参考](https://github.com/microsoft/playwright-cli/blob/main/skills/playwright-cli/references/session-management.md) 为准，默认 `open` 与 `attach` 的用途不同。

### 2. 请求分析采用 Chrome DevTools MCP

使用完整工具集连接现有 Chrome 后，先列出目标页面，再用 `list_network_requests` 查找请求、`get_network_request` 查看头部和正文。响应正文可通过 `responseFilePath` 单独保存；请求正文对应 `requestFilePath`。当前工具文档支持显式页面 ID，具体参数以安装版本为准。来源：[网络工具参数](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md#network)。

通用 MCP 配置示意：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect"]
    }
  }
}
```

要求 Chrome 144+ 已打开、开启远程调试并允许连接。默认启动配置使用独立 Profile，必须显式选择附加模式才能达到这里的目的。多 Profile 时需确认连接的是目标 Profile。来源：[官方自动连接指南](https://developer.chrome.com/docs/devtools/agents/use-cases/auto-connect)。

### 3. Shell 与 HAR 可以选 agent-browser

已连接并选定目标标签页后，官方提供以下命令：

```bash
agent-browser network har start
# 执行目标操作，使网络请求发生。
agent-browser network requests --filter api
# agent-browser network request <requestId>
agent-browser network har stop ./capture.har
```

HAR 默认嵌入文本响应正文，也可以设置正文记录策略。连接时可选 `--auto-connect` 或明确 CDP 地址。来源：[网络命令](https://github.com/vercel-labs/agent-browser/blob/main/skill-data/core/references/commands.md#network)、[连接方式](https://github.com/vercel-labs/agent-browser#cdp-mode)。

## 从抓请求到固定任务的工程建议

1. 连接正确的已登录会话，先启用监听，再触发目标操作。
2. 找出目标请求的 URL、方法、输入、分页、状态码与响应结构，并区分认证信息和业务参数。
3. 根据实测选择实现：依赖页面状态的步骤保留浏览器操作；可独立调用的接口再整理成请求脚本。
4. 把流程封装成有参数和成功判据的任务，处理超时、认证过期与业务错误。
5. 再次执行验证，而不是把录制成功当作自动化成功。

这部分是实施建议。捕获到一次请求并不能证明脱离浏览器可以重放：还可能依赖 CSRF、动态签名、临时令牌或页面上下文。应逐项验证，避免在脚本中硬编码抓到的认证值。

## 能力边界与试用判据

- 网络监听一般需要在请求发生前开始；不能承诺补回连接前所有请求。Chrome 工具的列表有导航记录范围，长期保存需主动导出。来源：[列表范围](https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md#list_network_requests)。
- HTTP 请求正文与响应正文不等于 WebSocket 帧或 SSE 持续事件流；若任务涉及实时流，需要另做专项验证。
- Playwright CDP 仅支持 Chromium 系，官方明确其兼容完整性低于 Playwright 原生协议连接，某些高级能力可能受影响。来源：[connectOverCDP](https://playwright.dev/docs/api/class-browsertype#browser-type-connect-over-cdp)。
- HAR、认证状态和请求日志可能携带凭证。产出业务脚本时应移除认证实值，日志按需脱敏；认证状态文件不要提交仓库。来源：[认证文件说明](https://playwright.dev/docs/auth)。
- CLI 并不意味着每次执行都需要 LLM。探索与生成可以由 Agent 完成，整理好的固定任务可由脚本直接运行；这正是本需求适合采用的工作方式。

建议第一次用一个只读任务验收：连接已有登录页 → 监听并触发一次查询 → 取得请求参数和响应 → 保存操作代码 → 用另一组查询参数重跑 → 检查结果正确 → 断开但保留用户浏览器。此闭环通过后，再扩大到批量任务。
