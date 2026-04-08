# 基于 Milvus 的 RAG 教育问答系统后端

本目录是教育问答系统的后端服务，基于 `FastAPI + MySQL + Redis + Milvus + OpenAI 兼容大模型接口` 实现。后端负责邮箱验证码登录、JWT 鉴权、会话问答、FQA 快速命中、RAG 检索生成、知识库文件管理、配置中心、Case 分析和 RAGAS 系统评估。

## 核心能力

- 邮箱验证码登录：通过 QQ 邮箱 SMTP 发送验证码，验证码写入 Redis，默认有效期 5 分钟。
- JWT 鉴权：登录成功后签发 JWT，前端通过 `Authorization: Bearer <token>` 访问受保护接口。
- 会话问答：`POST /query` 以 SSE 形式返回 `thinking` 和 `answer` token，并在完成后写入 MySQL 会话历史。
- FQA 快速问答：优先通过 `jpkb` 表问题集构建 BM25 索引，Redis 缓存常用命中结果。
- RAG 检索生成：专业问题进入 BERT 查询分类、策略选择、Milvus 混合检索、BGE Reranker 重排序和 LLM 流式生成链路。
- 知识库管理：支持分类、上传、预览、切片、向量入库、向量检索、切片查看和源文件追溯。
- 配置中心：支持查看、编辑、版本保存和回滚 `config.ini`，部分配置可热加载。
- Case 分析：支持将对话标记为 GoodCase 或 BadCase，并查看完整执行链路 `trace_data`。
- 系统评估：上传 JSON 评估集后调用 RAGAS 计算忠实度、答案相关性、上下文精确率和上下文召回率。

## 技术栈

- Web 框架：FastAPI、Uvicorn
- 数据库与缓存：MySQL、Redis
- 向量数据库：Milvus
- 检索与向量模型：BGE-M3、BGE-Reranker、BM25、jieba
- 文档处理：LangChain loaders、自定义 OCR PDF/DOC/PPT/图片加载器、中文递归切分器、Markdown 切分器
- 大模型接口：OpenAI SDK 兼容接口，支持 DeepSeek、DashScope/Qwen、Ollama 等兼容服务
- 评估：RAGAS、datasets、LangChain OpenAI/Ollama wrappers
- 认证与配置：PyJWT、configparser、SMTP

## 目录结构

```text
integerate_qa_system/
├── api.py                         # FastAPI 应用入口与 CORS 配置
├── api_routes/                    # 认证、问答、会话、知识库、配置、FAQ、Case、评估路由
├── base/                          # 配置、日志、trace 数据模型
├── login/                         # JWT 与邮件验证码服务
├── mysql_qa/                      # MySQL、Redis、BM25 快速检索
├── rag_qa/                        # RAG 核心、文档加载、文本切分、模型与评测数据
├── data/                          # 知识库原始文件目录
├── logs/                          # 运行日志
├── config.ini                     # 本地运行配置，包含敏感配置，勿提交真实密钥
└── requirements.txt               # Python 依赖清单
```

## 运行环境

建议使用 Python 3.10 或更高版本。当前依赖中包含较多机器学习和文档解析库，请优先使用虚拟环境或 Conda 环境隔离安装。

外部服务需要提前启动：

- MySQL：用于用户、会话、知识库元数据、配置版本、评估记录和 FAQ 数据。
- Redis：用于邮箱验证码、BM25 问题缓存和答案缓存。
- Milvus：用于存储 BGE-M3 稠密向量、稀疏向量和父子切片元数据。
- 大模型服务：提供 OpenAI 兼容 `base_url` 与 `api_key`，用于策略选择、问答生成和评估。
- SMTP 邮箱：用于验证码发送；开发环境发送失败时验证码会打印到控制台。

## 安装与启动

```bash
cd integerate_qa_system
pip install -r requirements.txt
python api.py
```

也可以使用 Uvicorn 启动：

```bash
cd integerate_qa_system
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

服务默认运行在 `http://localhost:8000`。接口文档可访问：

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

启动时会尝试初始化用户会话表、知识库表、配置版本表和评估表；如果 MySQL、Redis、Milvus 或模型文件未准备好，启动可能失败或部分功能不可用。

## 配置说明

配置文件位于 `config.ini`。README 仅给出字段说明，请不要把真实密钥写入文档、日志或提交记录。

```ini
[mysql]
host = localhost
user = root
password = <mysql-password>
database = subjects_kg

[redis]
host = localhost
port = 6379
password = <redis-password>
db = 0

[milvus]
host = localhost
port = 19530
database_name = itcast
collection_name = edurag_final

[llm]
model = <chat-model-name>
api_key = <llm-api-key>
base_url = <openai-compatible-base-url>
enable_thinking = true
thinking_budget_tokens = 10000

[assessment]
llm_model = <assessment-llm-model>
embedding_model = <assessment-embedding-model>
api_key = <assessment-api-key>
base_url = <assessment-openai-compatible-base-url>

[retrieval]
parent_chunk_size = 1200
child_chunk_size = 300
chunk_overlap = 50
retrieval_k = 8
candidate_m = 4

[logger]
log_file = logs/app.log

[app]
valid_sources = ["ai", "java", "test", "ops", "bigdata"]
customer_service_phone = 12345678

[email]
qq_email = <qq-email>
qq_auth_code = <qq-email-auth-code>
smtp_server = smtp.qq.com
smtp_port = 465

[jwt]
secret_key = <strong-random-secret>
algorithm = HS256
expire_days = 30
```

可热加载的配置段：`llm`、`assessment`、`retrieval`、`app`、`email`、`jwt`。

需要重启后端才会完全生效的配置段：`mysql`、`redis`、`milvus`、`logger`。

## 数据库表

后端会在启动时创建或补齐以下主要表：

- `user`：用户邮箱与用户 ID。
- `user_session`：用户会话，包含软删除状态。
- `conversations`：问答历史、`trace_data` 执行链路、GoodCase/BadCase 状态。
- `jpkb`：传统 FAQ/FQA 问答表，供 BM25 快速检索使用。
- `category`：知识库分类。
- `file_info`：知识库文件路径、分类、目录标记和切片状态。
- `config_version`：配置版本、变更描述、变更人和活跃状态。
- `assessment_file`：评估文件元数据和原始 JSON 内容。
- `assessment_result`：评估运行状态、指标结果和明细 JSON。

## 问答主链路

`POST /query` 的核心处理流程位于 `new_main.py` 的 `IntegratedQASystem.query`：

1. 校验 JWT 与请求参数，自动生成或使用传入的 `session_id`。
2. 使用 BM25 在 `jpkb` 中快速匹配 FQA，命中阈值默认为 `0.85`。
3. FQA 未命中时使用 BERT 分类器判断问题类别。
4. 如果属于通用知识，跳过向量检索并直接调用 LLM。
5. 如果属于专业咨询，调用策略选择器选择直接检索、HyDE、子查询或回溯问题检索。
6. 使用 Milvus 执行 BGE-M3 稠密和稀疏混合检索，再用 BGE-Reranker 重排序。
7. 拼接检索上下文、最近 5 轮会话历史和用户问题，调用 LLM 流式生成答案。
8. 将答案、`trace_data`、会话 ID 和状态写入 MySQL。
9. SSE 返回 `token_type`、`token`、`is_complete`、`session_id`，完成时附带 `conversation_id`。

## 知识库处理链路

支持的切片文件类型来自 `rag_qa/core/document_process.py`：

```text
.txt, .pdf, .docx, .ppt, .pptx, .jpg, .png, .md
```

处理流程：

1. 按知识库分类上传文件到 `data/<category>/`。
2. 文档加载器读取文本、PDF、Word、PPT、图片或 Markdown。
3. 普通文本使用中文递归切分器，Markdown 使用 Markdown 切分器。
4. 每个父块继续切成子块，子块写入 `parent_id`、`parent_content`、`source`、`file_path` 等元数据。
5. BGE-M3 生成稠密向量和稀疏向量，写入 Milvus。
6. `file_info.is_chunk` 更新为已切片。

## API 概览

认证：

- `POST /send-verification-code`：发送邮箱验证码。
- `POST /login`：校验验证码并返回 JWT。
- `GET /verify-token`：校验当前 JWT。

问答与会话：

- `POST /query`：SSE 流式问答。
- `POST /sessions/create`：创建会话。
- `GET /sessions?limit=20`：获取当前用户会话列表。
- `GET /sessions/{session_id}?limit=10`：获取会话历史。
- `DELETE /sessions/{session_id}`：软删除会话。
- `PATCH /conversations/{conversation_id}/status`：标记默认、GoodCase 或 BadCase。
- `PATCH /conversations/{conversation_id}/regenerate`：用重新生成答案覆盖原对话。

知识库：

- `GET /knowledge/categories`：获取分类。
- `POST /knowledge/categories`：创建分类。
- `DELETE /knowledge/categories/{category_id}`：删除分类。
- `GET /knowledge/files`：获取分类入口或分类内文件。
- `GET /knowledge/categories/{category_id}/files`：获取指定分类文件。
- `GET /knowledge/files/{file_id}`：获取文件元信息。
- `GET /knowledge/files/{file_id}/preview`：按文件 ID 预览。
- `GET /knowledge/preview?path=...`：按文件路径预览。
- `POST /knowledge/categories/{category_id}/upload`：上传文件。
- `DELETE /knowledge/files/{file_id}`：删除文件。
- `POST /knowledge/chunk`：按文件 ID 或分类执行切片并以 SSE 返回进度。
- `GET /knowledge/files/unchunked`：获取未切片文件。
- `GET /knowledge/files/{file_id}/chunks`：查看文件切片。
- `POST /knowledge/search`：向量检索。
- `POST /knowledge/vector/detail`：查询向量详情。
- `GET /knowledge/sources`：获取知识来源。
- `GET /knowledge/supported-types`：获取支持的切片文件类型。

配置中心：

- `GET /config`：获取脱敏后的结构化配置。
- `GET /config/raw`：获取原始配置文本。
- `POST /config`：保存配置并创建版本记录。
- `GET /config/versions`：获取配置版本列表。
- `GET /config/versions/{version_id}`：查看版本详情。
- `POST /config/rollback/{version_id}`：回滚配置版本。

FAQ/FQA：

- `GET /faq`：查询 FAQ，可带 `search` 参数。
- `GET /faq/{faq_id}`：查看单条 FAQ。
- `POST /faq`：新增 FAQ。
- `PUT /faq/{faq_id}`：更新 FAQ。
- `DELETE /faq/{faq_id}`：删除 FAQ。

Case 分析：

- `GET /cases?status=1&page=1&page_size=20`：分页获取 GoodCase 或 BadCase。
- `GET /cases/{conversation_id}`：获取单个 Case 详情。
- `GET /cases/download?status=1`：导出 GoodCase 或 BadCase JSON。

系统评估：

- `POST /assessment/upload`：上传 JSON 评估文件。
- `GET /assessment/files`：获取评估文件列表。
- `GET /assessment/files/{file_id}`：查看评估文件内容。
- `POST /assessment/run`：以 SSE 运行 RAGAS 评估。
- `GET /assessment/results`：获取评估结果列表。
- `GET /assessment/results/{result_id}`：查看评估结果详情。

## 常用请求示例

登录后访问受保护接口：

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/verify-token
```

发起流式问答：

```bash
curl -N -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "{\"query\":\"什么是 RAG？\",\"source_filter\":\"ai\",\"session_id\":\"<session-id>\"}"
```

按分类执行知识库切片：

```bash
curl -N -X POST http://localhost:8000/knowledge/chunk \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "{\"file_ids\":[],\"category_id\":1}"
```

## 常见问题

- 启动时 MySQL 连接失败：检查 `[mysql]` 主机、端口、账号、密码和数据库是否存在。
- 验证码收不到：检查 QQ 邮箱 SMTP 授权码；开发环境下也可查看后端控制台打印的验证码。
- 登录后 401：检查 JWT `secret_key` 是否被修改，或清除浏览器本地 token 后重新登录。
- 知识库切片失败：检查文件扩展名是否在支持列表中，OCR/文档解析依赖是否安装，源文件路径是否存在。
- Milvus 检索失败：确认 Milvus 服务已启动，`database_name` 和 `collection_name` 可访问，BGE 模型目录完整。
- 配置保存后不生效：确认配置项是否属于热加载范围；MySQL、Redis、Milvus 和日志配置需要重启后端。
- RAGAS 评估失败：检查评估 JSON 是否包含 `question`、`answer`、`context`、`ground_truth` 字段，并确认评估模型配置可用。

## 安全说明

- `config.ini` 可能包含数据库密码、Redis 密码、LLM API Key、邮箱授权码和 JWT 密钥，严禁提交真实生产密钥。
- `GET /config` 会对敏感字段脱敏，但 `GET /config/raw` 会返回原始配置文本，只应对可信用户开放。
- 知识库文件预览会读取本地文件，后端已限制在 `DATA_BASE_PATH` 下访问，部署时仍需关注目录权限。
