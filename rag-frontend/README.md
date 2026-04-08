# RAG 教育问答系统前端

本目录是基于 `React + Vite` 的前端应用，用于访问后端的 RAG 教育问答能力。当前界面包含邮箱验证码登录、问答模式、历史会话、专业模式、知识库管理、配置中心、FQA 管理、Case 分析和系统评估。

## 技术栈

- React 19
- Vite 7
- Axios
- fetch + ReadableStream，用于解析问答和评估 SSE
- React Markdown、remark-gfm，用于 Markdown 答案渲染
- react-pdf，用于 PDF 预览
- react-syntax-highlighter，用于代码文件预览

## 目录结构

```text
rag-frontend/
├── public/                         # 静态资源
├── src/
│   ├── api.js                      # 后端接口封装与 Axios 拦截器
│   ├── App.jsx                     # 鉴权入口、模式切换和页面路由
│   ├── AppModern.css               # 主布局样式
│   ├── components/                 # 登录、侧边栏、问答、知识库、配置、FAQ、Case、评估页面
│   └── assets/                     # 图标资源
├── .env.example                    # API 地址示例
├── package.json                    # npm 脚本与依赖
├── vite.config.js                  # Vite 配置
├── UI_DESIGN.md                    # UI 设计说明
└── OPTIMIZATION_GUIDE.md           # 性能优化说明
```

## 安装与启动

```bash
cd rag-frontend
npm install
npm run dev
```

开发服务默认运行在 `http://localhost:5173`。

后端默认地址为 `http://localhost:8000`，可通过 `.env` 修改：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## npm 脚本

```bash
npm run dev       # 启动 Vite 开发服务器
npm run build     # 生产构建
npm run lint      # ESLint 检查
npm run preview   # 本地预览构建结果
```

## 页面与功能

### 登录页

组件：`src/components/Login.jsx`

- 输入邮箱并请求验证码。
- 调用 `POST /send-verification-code` 发送验证码。
- 输入验证码后调用 `POST /login`。
- 登录成功后把 `token` 和用户信息写入 `localStorage`。
- 后续请求由 Axios 拦截器自动追加 `Authorization` 头。

### 应用入口

组件：`src/App.jsx`

- 启动时读取 `localStorage` 中的 token 和用户信息。
- 调用 `GET /verify-token` 校验登录态。
- 支持问答模式和专业模式切换。
- 侧边栏折叠、隐藏和当前模式会持久化到 `localStorage`。

### 侧边栏

组件：`src/components/SidebarModern.jsx`

- 问答模式：展示历史会话，支持选择、加载和删除会话。
- 专业模式：展示配置、知识库、FQA 管理、Case 分析、系统评估菜单。
- 知识库菜单下会加载分类列表和分类文件。
- 底部展示当前登录邮箱并支持退出登录。

### 问答模式

组件：`src/components/ChatAreaModern.jsx`

- 首次提问前调用 `POST /sessions/create` 创建会话。
- 调用 `POST /query` 获取 SSE 流式响应。
- 按 `token_type` 区分思考过程 `thinking` 和正式回答 `answer`。
- 使用 `requestAnimationFrame` 缓冲 token，减少流式渲染时的频繁状态更新。
- 支持复制答案、复制代码块、重新生成答案。
- 支持把回答标记为默认、GoodCase 或 BadCase。
- 加载历史会话时会解析后端 `trace_data` 中的模型思考内容。

### 知识库管理

组件：`src/components/KnowledgePage.jsx`

- 支持创建和删除知识库分类。
- 支持按分类上传文件。
- 支持预览文本、Markdown、代码、图片、PDF 和 Word HTML 内容。
- 支持按后端返回的支持类型校验上传文件类型。
- 支持选择单个文件、多个文件或分类执行知识库切片。
- 切片调用 `POST /knowledge/chunk`，通过 ReadableStream 解析 SSE 进度。
- 支持查询未切片文件、查看文件切片、执行向量检索和查看向量详情。
- 向量检索界面基于 BGE-M3 混合检索和 BGE-Reranker 重排序结果展示。

### 配置中心

组件：`src/components/ConfigPage.jsx`

- 调用 `GET /config` 展示脱敏后的结构化配置。
- 调用 `GET /config/raw` 获取原始 INI 内容并转换为表单。
- 保存配置时调用 `POST /config`，必须填写变更描述。
- 支持查看配置版本、查看版本详情和回滚版本。
- 保存或回滚后展示热加载结果，提示哪些配置需要重启后端。

### FQA 管理

组件：`src/components/FqaPage.jsx`

- 支持按学科或问题关键字搜索 FQA。
- 支持新增、编辑、删除和查看 FQA。
- 对应后端 `GET /faq`、`POST /faq`、`PUT /faq/{faq_id}`、`DELETE /faq/{faq_id}`。

### Case 分析

组件：`src/components/CasePage.jsx`

- 支持 GoodCase 和 BadCase 两类列表切换。
- 支持分页查询和下载 JSON 数据。
- 支持查看单条 Case 的问答内容与完整 `trace_data`。
- trace 展示包括 FQA 搜索、查询分类、策略选择、向量检索和 LLM 生成。
- 向量检索结果可继续展开父文档、完整内容和源文件预览。

### 系统评估

组件：`src/components/AssessmentPage.jsx`

- 支持上传 JSON 评估文件。
- 支持查看评估文件内容和历史评估结果。
- 调用 `POST /assessment/run` 以 SSE 方式执行 RAGAS 评估。
- 前端展示进度、耗时、最新单条结果和汇总指标。
- 指标包括忠实度、答案相关性、上下文精确率和上下文召回率。

### 文件预览

组件：`src/components/FilePreview.jsx`

- 文本、Markdown 和代码文件直接渲染或高亮。
- PDF 通过 `react-pdf` 渲染，支持翻页和缩放。
- 图片通过 base64 数据渲染。
- Word 文件依赖后端 `mammoth` 转换出的 HTML。
- Excel、PPT 和未知类型会展示不支持预览提示。

## API 封装

所有接口集中在 `src/api.js`：

- `api`：Axios 实例，默认 `baseURL` 来自 `VITE_API_BASE_URL`。
- 请求拦截器：从 `localStorage.token` 注入 JWT。
- 响应拦截器：统一处理超时、400、401、403、404、500，并在 401 时清理登录态。
- 问答、知识库切片和评估运行使用原生 `fetch`，因为这些接口需要流式读取响应体。

主要接口分组：

- 认证：`sendVerificationCode`、`login`、`verifyToken`
- 会话问答：`createSession`、`queryAPI`、`getSessions`、`getSessionConversations`、`deleteSession`
- 知识库：`getCategories`、`createCategory`、`uploadFileToCategory`、`chunkFilesPost`、`vectorSearch`、`getVectorDetail`
- 配置：`getConfig`、`getRawConfig`、`updateConfig`、`getConfigVersions`、`rollbackConfig`
- FQA：`getFaqs`、`createFaq`、`updateFaq`、`deleteFaq`
- Case：`updateConversationStatus`、`getCases`、`getCaseDetail`、`downloadCases`
- 评估：`uploadAssessmentFile`、`getAssessmentFiles`、`runAssessment`、`getAssessmentResults`

## 与后端联调

1. 启动后端：

```bash
cd ../integerate_qa_system
python api.py
```

2. 启动前端：

```bash
cd ../rag-frontend
npm run dev
```

3. 浏览器访问 `http://localhost:5173`。

4. 输入邮箱获取验证码并登录。

5. 若验证码邮件发送失败，可查看后端控制台输出的开发模式验证码。

6. 登录后先测试问答模式，再进入专业模式测试知识库、配置、FQA、Case 和评估。

## 常见问题

- 页面一直停留在登录页：检查 `VITE_API_BASE_URL` 是否指向后端服务，并确认 `GET /verify-token` 可访问。
- 401 后自动回到登录页：token 过期、后端 JWT 密钥变化或本地 token 无效，重新登录即可。
- 问答没有流式输出：确认后端 `POST /query` 返回 `text/event-stream`，并检查浏览器 Network 面板中的 SSE 数据。
- 知识库上传失败：确认已进入具体分类，文件扩展名在后端支持列表中。
- PDF 预览失败：检查浏览器是否能访问 `pdfjs` worker，或改用本地 worker 配置。
- 配置保存后提示需要重启：MySQL、Redis、Milvus 和 logger 配置不支持完整热加载，需要重启后端。
- 评估运行失败：确认上传 JSON 字段与后端评估接口要求一致，并检查评估模型配置。

## 开发注意事项

- 不要把真实 token、API Key、邮箱授权码或数据库密码写入前端代码。
- `localStorage` 中保存了 `token`、`user`、侧边栏状态和模式状态，调试登录问题时可先清理这些键。
- 问答流式解析依赖后端返回的 `data: <json>\n\n` 格式，修改后端 SSE 结构时需要同步更新 `ChatAreaModern.jsx`。
- Case 分析依赖后端 `trace_data` 字段结构，修改 trace 模型时需要同步检查 `CasePage.jsx`。
- 知识库切片当前使用 `chunkFilesPost` 对接 `POST /knowledge/chunk`，不要误用旧的 `/knowledge/chunk/stream` 调用。
