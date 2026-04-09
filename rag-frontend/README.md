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
- 只有管理员才会看到“专业模式”按钮
- 非管理员即使本地保留了旧的 `appMode=professional`，也会在启动时自动切回问答模式
- 非管理员不会渲染专业模式页面
- 非管理员不会显示对话“点赞/点踩”状态标记按钮

## 前端接口拦截

除后端权限校验外，前端还增加了一层管理员拦截：

- 所有专业模式相关 Axios 请求会在发送前先检查 `is_admin`
- 以下 fetch/SSE 接口也会在调用前做管理员校验：
  - `POST /knowledge/chunk`
  - `POST /assessment/run`

因此普通用户即使在控制台手动调用相关方法，也会先被前端阻止，再由后端兜底拦截。

## 本地存储说明

当前前端会使用以下本地存储键：

- `token`
- `user`
- `appMode`
- `sidebarCollapsed`
- `sidebarHidden`

如果需要排查登录态或权限显示问题，建议先清理这些键后重新登录。

## 开发说明

- 管理员权限的真正安全边界仍在后端，前端拦截只用于减少误操作
- 专业模式新增页面或接口时，请同步补充管理员判断
- 后端权限字段或鉴权返回结构变更后，请同步更新本 README 与 `src/api.js`、`src/App.jsx`
