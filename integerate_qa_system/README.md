# 基于 Milvus 的 RAG 教育问答系统后端

本目录是系统后端服务，基于 `FastAPI + MySQL + Redis + Milvus + OpenAI 兼容接口` 实现，负责登录鉴权、问答会话、知识库管理、配置管理、FAQ/FQA、Case 分析和系统评估。

## 核心功能

- 邮箱验证码登录
- JWT 鉴权
- 问答会话与历史记录
- FAQ/FQA 快速命中
- RAG 检索与流式回答
- 知识库分类、上传、预览、切片、向量检索
- 配置查看、版本保存与回滚
- Case 分析与导出
- RAGAS 系统评估

## 管理员权限说明

本次已接入 `user.is_admin` 字段：

- 字段含义：`0` 表示普通用户，`1` 表示管理员
- 后端启动时会自动确保 `user` 表存在 `is_admin` 字段；新用户默认值为 `0`
- `POST /login` 和 `GET /verify-token` 现在都会返回 `is_admin`
- `get_current_user` 会在每次鉴权时根据 `user_id` 回查数据库，实时带出最新管理员状态

只有管理员可访问以下“专业模式”相关接口：

- 知识库：`/knowledge/**`
- 配置中心：`/config/**`
- FAQ 管理：`/faq/**`
- Case 分析：`/cases/**`
- 系统评估：`/assessment/**`
- 对话状态标记：`PATCH /conversations/{conversation_id}/status`

普通登录用户仍可访问：

- `POST /query`
- `/sessions/**`
- `PATCH /conversations/{conversation_id}/regenerate`
- 登录与鉴权相关接口

## 目录结构

```text
integerate_qa_system/
├── api.py
├── api_routes/
├── base/
├── login/
├── mysql_qa/
├── rag_qa/
├── data/
├── logs/
├── config.ini
├── requirements.txt
└── README.md
```

## 环境要求

- Python 3.10+
- MySQL
- Redis
- Milvus
- 可用的 OpenAI 兼容大模型服务
- SMTP 邮箱服务

## 安装与启动

```bash
cd integerate_qa_system
pip install -r requirements.txt
python api.py
```

或使用：

```bash
cd integerate_qa_system
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

默认地址：

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 关键配置

配置文件位于 `config.ini`，常见配置包括：

- MySQL
- Redis
- Milvus
- LLM
- Assessment
- Retrieval
- Email
- JWT

请不要把真实密钥、密码、授权码提交到仓库。

## 数据库说明

系统启动时会自动初始化或补齐以下核心表：

- `user`
  - 用户邮箱
  - `is_admin` 管理员标记
- `user_session`
- `conversations`
- `category`
- `file_info`
- `config_version`
- `assessment_file`
- `assessment_result`
- `jpkb`

如果你需要手动授予管理员权限，可以直接更新 `user` 表：

```sql
UPDATE user
SET is_admin = 1
WHERE email = 'admin@example.com';
```

## 常用接口

### 鉴权

- `POST /send-verification-code`
- `POST /login`
- `GET /verify-token`

### 问答与会话

- `POST /query`
- `POST /sessions/create`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `DELETE /sessions/{session_id}`
- `PATCH /conversations/{conversation_id}/regenerate`

### 管理员接口

- `GET/POST/DELETE /knowledge/...`
- `GET/POST /config/...`
- `GET/POST/PUT/DELETE /faq/...`
- `GET /cases/...`
- `POST/GET /assessment/...`
- `PATCH /conversations/{conversation_id}/status`

## 开发说明

- 管理员权限由后端强校验，前端不可替代后端鉴权
- 修改用户管理员身份后，无需等 JWT 过期，下一次请求会按数据库最新状态生效
- 专业模式功能变更时，请同步更新前端 `README.md`
