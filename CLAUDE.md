# CLAUDE.md

本文档用于指导 Claude/Codex 在本仓库中进行安全、正确、高效的协作开发。

## 1. 项目概览

这是一个教育场景的全栈 RAG 问答系统：
- 后端：`FastAPI + MySQL + Redis + Milvus + OpenAI 兼容 LLM`
- 前端：`React + Vite`
- 能力模块：登录鉴权、会话问答、知识库管理、配置中心、FAQ 管理、Case 分析、RAGAS 评测

仓库主目录：
- `integerate_qa_system/` 后端（Python）
- `rag-frontend/` 前端（React）
- `CLAUDE.md` 本文档

## 2. 启动与开发命令

后端（在 `integerate_qa_system/`）：
```bash
uvicorn api:app --reload --port 8000
```

前端（在 `rag-frontend/`）：
```bash
npm run dev
npm run build
npm run lint
npm run preview
```

说明：
- 前端默认 `http://localhost:5173`
- 后端默认 `http://localhost:8000`
- 前端 API 地址通过 `rag-frontend/.env` 的 `VITE_API_BASE_URL` 配置（示例见 `.env.example`）
- 目前仓库没有标准化自动化测试套件

## 3. 后端核心结构与调用链

核心文件：
- `integerate_qa_system/api.py` FastAPI 路由入口（几乎全部业务接口）
- `integerate_qa_system/new_main.py` `IntegratedQASystem` 总调度
- `integerate_qa_system/base/config.py` 配置单例与热更新机制
- `integerate_qa_system/mysql_qa/db/mysql_client.py` 主要数据库访问层
- `integerate_qa_system/rag_qa/core/vector_store.py` Milvus 混合检索 + rerank
- `integerate_qa_system/rag_qa/core/new_rag_system.py` RAG 策略与生成流程
- `integerate_qa_system/base/trace_models.py` 链路追踪模型

问答主链路（`POST /query`）：
1. JWT 鉴权（`get_current_user`）
2. `IntegratedQASystem.query(...)`
3. 先走 BM25/FQA 快速命中（`BM25Search`）
4. 未命中时走 RAG：分类 -> 策略选择 -> 向量检索 -> LLM 流式生成
5. 结果按 SSE 流式返回（`token_type`: `thinking`/`answer`）
6. 结束时写入 `conversations`，并把 `trace_data`（JSON）入库

重要行为：
- SSE 完成事件是 `is_complete=true`，并可能带 `conversation_id`
- 前端“重新生成”逻辑会用 `session_id=null` 请求，默认不落会话历史

## 4. 后端 API 分组（高频）

鉴权与会话：
- `/send-verification-code`, `/login`, `/verify-token`
- `/sessions/create`, `/sessions`, `/sessions/{session_id}`, `DELETE /sessions/{session_id}`

问答与标注：
- `/query`（SSE）
- `/conversations/{conversation_id}/status`（0 默认, 1 GoodCase, 2 BadCase）
- `/cases`, `/cases/{conversation_id}`, `/cases/download`

知识库：
- 分类：`/knowledge/categories`（GET/POST/DELETE）
- 文件：`/knowledge/files`, `/knowledge/categories/{id}/files`, `/knowledge/files/{id}`
- 预览：`/knowledge/files/{id}/preview`, `/knowledge/preview`
- 上传：`/knowledge/categories/{category_id}/upload`
- 向量：`/knowledge/search`, `/knowledge/vector/detail`, `/knowledge/sources`
- 切片：`/knowledge/chunk`（SSE）, `/knowledge/files/unchunked`, `/knowledge/files/{id}/chunks`
- 类型：`/knowledge/supported-types`

配置中心：
- `/config`, `/config/raw`, `/config/versions`, `/config/versions/{version_id}`, `/config/rollback/{version_id}`

FAQ：
- `/faq`（GET/POST）, `/faq/{faq_id}`（GET/PUT/DELETE）

评测（RAGAS）：
- `/assessment/upload`, `/assessment/files`, `/assessment/files/{file_id}`
- `/assessment/run`（SSE）
- `/assessment/results`, `/assessment/results/{result_id}`

## 5. 配置系统（`config.ini`）

配置文件位置：
- `integerate_qa_system/config.ini`

关键 section：
- `[mysql] [redis] [milvus] [llm] [assessment] [retrieval] [logger] [app] [email] [jwt]`

热更新规则（`Config.hot_reload()`）：
- 可热更新：`llm`, `assessment`, `retrieval`, `app`, `email`, `jwt`
- 不可热更新（需重启后端）：`mysql`, `redis`, `milvus`, `logger`

注意：
- 代码中对“思考模型”通过模型名关键字自动判断（如 `deepseek-reasoner`, `qwen3`）
- `api.py` 中知识库根路径目前写死为：
  `d:\WorkSpace\RAG_program\integerate_qa_system\data`

## 6. 数据与存储

MySQL 主要表（由 `MysqlClient` 初始化）：
- `user`, `user_session`, `conversations`
- `category`, `file_info`
- `config_version`
- `assessment_file`, `assessment_result`
- 传统 FAQ 表：`jpkb`

Milvus：
- 集合名来自 `config.ini` 的 `[milvus].collection_name`
- 存储字段包含 `text/dense_vector/sparse_vector/parent_id/parent_content/source/file_path`

Redis：
- 验证码缓存（`verification_code:{email}`，5 分钟）
- BM25/FQA 相关缓存

## 7. 前端结构与行为

主要文件：
- `rag-frontend/src/App.jsx` 全局模式切换与鉴权入口
- `rag-frontend/src/api.js` 全部接口封装
- `rag-frontend/src/components/ChatAreaModern.jsx` 聊天与 SSE 解析
- `rag-frontend/src/components/SidebarModern.jsx` 会话与专业模式菜单
- `rag-frontend/src/components/KnowledgePage.jsx` 知识库页面
- `rag-frontend/src/components/ConfigPage.jsx` 配置管理与版本回滚
- `rag-frontend/src/components/FqaPage.jsx` FAQ CRUD
- `rag-frontend/src/components/CasePage.jsx` Case 查看与 trace 展示
- `rag-frontend/src/components/AssessmentPage.jsx` 评测上传/执行/历史

前端关键点：
- JWT 和用户信息保存在 `localStorage`
- 401 会自动清理本地 token 并回到登录页
- 流式问答使用 `fetch + ReadableStream`（不是 axios）

## 8. Claude/Codex 协作约束

1. 变更优先级：
- 优先改“入口与核心链路”文件（`api.py`, `new_main.py`, `vector_store.py`, `new_rag_system.py`, `src/api.js`, `src/components/*`）
- 尽量避免无意义改动 `node_modules/`, `dist/`, 大模型文件、数据文件

2. 修改前后必须关注：
- SSE 消息结构是否兼容前端解析
- 会话归属与鉴权逻辑是否破坏
- `trace_data` 是否仍可被 `CasePage` 解析
- 热更新配置项是否与 `Config.hot_reload` 规则一致

3. 运行验证最小清单：
- 后端可启动、`/verify-token` 正常
- 前端可登录并新建会话
- `/query` 流式返回正常结束
- 知识库上传+切片可跑通（至少单文件）

## 9. 已知风险与坑位

- `requirements.txt` 偏简，实际代码依赖较多（如 `torch/pymilvus/langchain/rank_bm25/jieba/sentence-transformers/ragas` 等），新环境部署前需补齐。
- `config.ini` 可能包含真实密钥/密码，严禁在提交或日志中泄漏。
- 问答入库依赖 `session_id` 与 `user_session` 关系，绕过创建会话直接请求可能导致落库异常。
- 代码与注释含中文，终端编码不一致时可能出现乱码显示；编辑时统一使用 UTF-8。

## 10. 推荐排错路径

1. 登录问题：先查 Redis 验证码键与 `email_service` SMTP 连接日志  
2. 无回答/慢回答：查 `conversations.trace_data` 与后端日志（分类、策略、检索结果数、LLM 调用）  
3. 检索不到知识：查 `file_info.is_chunk`、Milvus collection、`source_filter` 是否有效  
4. 配置改了不生效：核对是否属于“不可热更新”配置项
