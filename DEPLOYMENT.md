# 部署指南

本文说明如何在一台新机器上部署并运行当前项目。当前仓库的 Docker Compose 只负责部署基础依赖服务：MySQL、Redis、Milvus、etcd 和 MinIO。后端 FastAPI 与前端 React 目前没有容器化配置，需要在宿主机上启动。

如果目标是让别人克隆后执行一次 `docker compose up -d` 就启动完整系统，还需要额外补充后端 Dockerfile、前端 Dockerfile/Nginx 配置，以及 compose 中的 backend/frontend 服务。

## 1. 部署方式概览

当前支持的部署方式：

```text
Docker Compose
├── MySQL
├── Redis
├── etcd
├── MinIO
└── Milvus

宿主机进程
├── FastAPI 后端: http://localhost:8000
└── React 前端:  http://localhost:5173
```

适合场景：

- 本地开发
- 演示环境
- 单机部署
- 课程设计或毕业设计验收环境

不适合直接作为生产环境：

- 后端和前端没有容器编排
- 示例密码需要替换
- 没有 HTTPS、反向代理和统一日志采集
- 没有服务健康检查和自动重启策略

## 2. 机器要求

建议配置：

- CPU：4 核或更高
- 内存：16 GB 或更高，Milvus 和本地模型加载会占用较多内存
- 磁盘：至少 20 GB 可用空间，模型文件通过 Git LFS 拉取，体积较大
- 系统：macOS、Linux 或 Windows + WSL2

必需软件：

- Git
- Git LFS
- Docker
- Docker Compose
- Python 3.10+
- Node.js 18+
- npm

检查命令：

```bash
git --version
git lfs version
docker --version
docker compose version
python3 --version
node --version
npm --version
```

初始化 Git LFS：

```bash
git lfs install
```

## 3. 克隆项目与拉取模型

```bash
git clone https://github.com/zhangzgen/RAG_program.git
cd RAG_program
git lfs pull
```

确认模型权重已拉取：

```bash
git lfs ls-files
ls -lh integerate_qa_system/rag_qa/models/bge-m3
ls -lh integerate_qa_system/rag_qa/models/bge-reranker-large
```

如果模型文件只有几 KB，说明还只是 LFS 指针文件，需要重新执行：

```bash
git lfs pull
```

## 4. 启动 Docker 基础服务

在仓库根目录执行：

```bash
docker compose up -d
```

查看状态：

```bash
docker compose ps
```

正常情况下应看到以下服务：

- `rag-mysql`
- `rag-redis`
- `rag-etcd`
- `rag-minio`
- `rag-milvus`

默认端口：

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| MySQL | `3306` | 关系数据库 |
| Redis | `6379` | 缓存 |
| Milvus | `19530` | 向量数据库 |
| Milvus metrics | `9091` | Milvus 监控端口 |
| MinIO API | `9000` | Milvus 对象存储依赖 |
| MinIO Console | `9001` | MinIO 控制台 |

查看日志：

```bash
docker compose logs -f mysql
docker compose logs -f redis
docker compose logs -f milvus-standalone
```

停止服务：

```bash
docker compose down
```

停止并删除数据卷：

```bash
docker compose down -v
```

删除数据卷会清空 MySQL、Redis、Milvus、MinIO、etcd 数据，谨慎执行。

## 5. 配置后端

复制后端配置模板：

```bash
cd integerate_qa_system
cp config.example.ini config.ini
```

编辑 `config.ini`。本机运行后端、Docker 运行基础服务时，默认连接地址使用 `localhost`：

```ini
[mysql]
host = localhost
user = root
password = 123456
database = subjects_kg

[redis]
host = localhost
port = 6379
password = 1234
db = 0

[milvus]
host = localhost
port = 19530
database_name = itcast
collection_name = edurag_final
```

必须按自己的环境修改：

```ini
[llm]
model = qwen-plus
api_key = your_openai_compatible_api_key
base_url = https://dashscope.aliyuncs.com/compatible-mode/v1

[email]
qq_email = your_qq_email@qq.com
qq_auth_code = your_qq_email_auth_code
smtp_server = smtp.qq.com
smtp_port = 465

[jwt]
secret_key = change_this_to_a_random_secret
```

注意：

- `config.ini` 是本地配置文件，不应提交到 Git。
- `llm.api_key` 必须是真实可用的 OpenAI 兼容接口密钥。
- 邮箱验证码依赖 SMTP 授权码，不是邮箱登录密码。
- 生产环境必须修改 MySQL、Redis 和 JWT 的默认密码/密钥。

## 6. 安装并启动后端

进入后端目录：

```bash
cd integerate_qa_system
```

创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动后端：

```bash
python api.py
```

也可以使用 Uvicorn：

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

验证后端：

```bash
curl http://localhost:8000/docs
```

浏览器访问：

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

后端启动时会自动初始化或补齐核心数据库表。

## 7. 配置并启动前端

打开新的终端，进入前端目录：

```bash
cd rag-frontend
cp .env.example .env
```

确认 `.env` 指向后端：

```env
VITE_API_BASE_URL=http://localhost:8000
```

安装依赖：

```bash
npm install
```

启动开发服务：

```bash
npm run dev
```

浏览器访问：

```text
http://localhost:5173
```

如果需要构建静态文件：

```bash
npm run build
npm run preview
```

## 8. 首次登录和管理员授权

1. 打开前端登录页。
2. 输入邮箱并获取验证码。
3. 使用验证码登录。
4. 新用户默认是普通用户，只能使用问答模式。
5. 如需进入专业模式，需要在数据库中把该用户设为管理员。

进入 MySQL：

```bash
docker exec -it rag-mysql mysql -uroot -p123456 subjects_kg
```

授权管理员：

```sql
UPDATE user
SET is_admin = 1
WHERE email = 'admin@example.com';
```

退出后重新登录前端。

## 9. 知识库初始化流程

管理员进入专业模式后：

1. 进入知识库页面。
2. 创建知识分类。
3. 上传 PDF、Word、PPT、TXT 或 Markdown 文件。
4. 预览文件，确认内容可读取。
5. 执行文档切片。
6. 等待切片写入 Milvus。
7. 回到问答模式提问，系统会基于向量检索增强回答。

上传文件和向量库数据属于运行数据，不会提交到 GitHub。

## 10. 验证部署是否正常

检查基础服务：

```bash
docker compose ps
```

检查后端接口：

```bash
curl http://localhost:8000/docs
```

检查前端：

```text
http://localhost:5173
```

检查模型文件：

```bash
git lfs ls-files
```

检查端口占用：

```bash
lsof -i :8000
lsof -i :5173
lsof -i :3306
lsof -i :6379
lsof -i :19530
```

## 11. 如果未来要改成全 Docker 部署

当前项目还缺少应用容器化配置。要实现完整 Docker 部署，需要新增：

```text
integerate_qa_system/Dockerfile
integerate_qa_system/.dockerignore
rag-frontend/Dockerfile
rag-frontend/.dockerignore
rag-frontend/nginx.conf
docker-compose.yml 中的 backend 服务
docker-compose.yml 中的 frontend 服务
```

同时后端容器内不能继续用 `localhost` 访问 MySQL、Redis 和 Milvus，需要改为 Docker Compose 服务名：

```ini
[mysql]
host = mysql

[redis]
host = redis

[milvus]
host = milvus-standalone
```

前端容器如果通过 Nginx 提供静态文件，推荐使用反向代理把 `/api` 转发到后端，避免浏览器跨域问题。

## 12. 常见问题

### Docker 服务启动后后端仍然连不上数据库

先确认容器状态：

```bash
docker compose ps
```

再检查 `config.ini` 是否和 `docker-compose.yml` 中的密码一致。

### Milvus 启动较慢

Milvus 依赖 etcd 和 MinIO，首次启动可能需要等待。查看日志：

```bash
docker compose logs -f milvus-standalone
```

### 登录验证码发送失败

检查邮箱配置：

- SMTP 服务器是否正确
- SMTP 授权码是否正确
- 邮箱服务是否开启 SMTP
- 后端日志中是否有邮件发送异常

### 前端无法访问后端

检查 `rag-frontend/.env`：

```env
VITE_API_BASE_URL=http://localhost:8000
```

修改后需要重启前端开发服务。

### 模型加载失败

确认 LFS 文件已拉取：

```bash
git lfs pull
git lfs ls-files
```

确认模型目录下的权重文件不是几 KB 的指针文件。

### 端口冲突

如果本机已有 MySQL、Redis 或其他服务占用端口，需要修改 `docker-compose.yml` 的端口映射，并同步修改 `config.ini`。

## 13. 部署检查清单

- 已安装 Git LFS 并执行 `git lfs pull`
- Docker Compose 基础服务全部启动
- `integerate_qa_system/config.ini` 已从模板复制并填写真实配置
- 后端依赖已安装
- 后端 `http://localhost:8000/docs` 可访问
- 前端 `.env` 指向正确后端地址
- 前端 `http://localhost:5173` 可访问
- 首个管理员用户已设置 `is_admin = 1`
- 已上传知识文件并成功切片
- 问答模式能返回检索增强回答
