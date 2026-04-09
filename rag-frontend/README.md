# RAG 教育问答系统前端

本目录是基于 `React + Vite` 的前端应用，用于访问后端问答服务，并提供问答模式、知识库管理、配置中心、FAQ 管理、Case 分析和系统评估等页面。

## 技术栈

- React 19
- Vite 7
- Axios
- fetch + ReadableStream
- React Markdown
- react-pdf

## 启动方式

```bash
cd rag-frontend
npm install
npm run dev
```

默认开发地址：

- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`

如需修改后端地址，创建或调整 `.env`：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 常用脚本

```bash
npm run dev
npm run build
npm run lint
npm run preview
```

## 主要页面

- 登录页：邮箱验证码登录
- 问答模式：创建会话、发送问题、查看历史、重新生成回答
- 专业模式
- 知识库
- 配置中心
- FQA 管理
- Case 分析
- 系统评估

## 管理员控制说明

前端已接入后端返回的 `is_admin` 字段：

- 登录成功后会把 `user_id`、`email`、`is_admin` 写入 `localStorage.user`
- 应用启动时会调用 `GET /verify-token`，并以服务端返回的 `is_admin` 为准刷新当前登录态
- 只有管理员才会看到“专业模式”入口
- 非管理员即使本地残留了 `appMode=professional`，也会在启动时自动切回问答模式
- 非管理员不会渲染专业模式页面
- 非管理员不会显示对话“点赞/点踩”状态标记按钮

## 本次更新

### 1. 修复流式输出渲染异常

已修复前端流式回答过程中可能出现的 React DOM 异常：

```text
Failed to execute 'removeChild' on 'Node'
```

本次处理方式：

- 将“流式输出中”的内容与“最终 Markdown 渲染”的内容分开处理
- 流式阶段仅渲染纯文本和思考过程
- 流结束后再切换为 `ReactMarkdown`
- 切换会话、清空消息、组件卸载时会主动重置当前流任务状态

这样可以避免流式更新期间节点被重复卸载。

### 2. 问答模式侧边栏展示

问答模式下，历史会话列表不再显示 `session_id`，而是显示该会话第一条用户问题：

- 后端 `GET /sessions` 返回 `first_query`
- 前端侧边栏优先展示 `first_query`
- 若该会话暂无提问，则回退显示“新对话”

### 3. 重新生成链路

重新生成按钮现在走新的后端流式接口：

- `POST /conversations/{conversation_id}/regenerate/stream`

行为变更如下：

- 前端点击重新生成后，不再自己覆盖数据库
- 后端会自动读取当前对话之前的历史问答作为补充上下文
- 后端生成完成后，会按原 `conversation_id` 直接覆盖数据库中的答案和 trace 数据
- 前端收到完成事件后，会继续使用原消息位置展示新结果

## 前端接口拦截

除了后端权限校验外，前端还增加了一层管理员拦截：

- 所有专业模式相关 Axios 请求会在发送前先检查 `is_admin`
- 非管理员在前端侧会被提前阻止调用专业模式相关接口
- 后端仍然保留最终权限校验作为兜底

## 本地存储说明

当前前端会使用以下本地存储键：

- `token`
- `user`
- `appMode`
- `sidebarCollapsed`
- `sidebarHidden`

如果需要排查登录态或权限展示问题，建议先清理这些键后重新登录。

## 开发说明

- 权限控制的真实安全边界始终在后端
- 若专业模式新增页面或接口，请同步补充管理员判断
- 若后端鉴权字段、会话结构或流式协议有变更，请同步更新本 README 与 `src/api.js`
