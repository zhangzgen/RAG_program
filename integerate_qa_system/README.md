# 智能问答系统 - 登录功能说明

## 项目概述

本项目是一个基于 RAG + MySQL + Redis 的智能问答系统，现已集成用户登录功能，支持邮箱验证码登录和JWT令牌认证。

## 新功能特性

### 1. 用户认证系统
- **邮箱验证码登录**：使用QQ邮箱发送验证码，无需密码
- **JWT令牌认证**：登录后返回JWT令牌，有效期30天
- **自动用户创建**：首次登录自动创建用户账号

### 2. 数据库表结构

系统使用以下三张表管理用户和会话：

#### user 表（用户表）
```sql
CREATE TABLE `user` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID，主键',
    `email` VARCHAR(255) NOT NULL COMMENT '用户邮箱',
    `create_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
```

#### user_session 表（用户会话表）
```sql
CREATE TABLE `user_session` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID，关联 user 表',
    `session_id` VARCHAR(100) NOT NULL COMMENT '会话标识，唯一',
    PRIMARY KEY (`id`),
    UNIQUE INDEX `uk_session_id` (`session_id`),
    INDEX `idx_user_id` (`user_id`),
    CONSTRAINT `fk_user_session_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表';
```

#### conversations 表（对话记录表）
```sql
CREATE TABLE `conversations` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(100) NOT NULL COMMENT '会话ID，关联 user_session 表',
    `query` TEXT NOT NULL,
    `answer` TEXT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    INDEX `idx_session_id` (`session_id`),
    CONSTRAINT `fk_conversations_session_id` FOREIGN KEY (`session_id`) REFERENCES `user_session` (`session_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话记录表';
```

## 配置说明

### 1. 配置文件 (config.ini)

在 `config.ini` 文件中添加以下配置：

```ini
# 邮箱配置
[email]
qq_email = your_qq_email@qq.com
qq_auth_code = your_qq_auth_code
smtp_server = smtp.qq.com
smtp_port = 465

# JWT 配置
[jwt]
secret_key = your_jwt_secret_key_here_change_in_production
algorithm = HS256
expire_days = 30
```

### 2. 获取QQ邮箱授权码

1. 登录QQ邮箱
2. 进入"设置" -> "账户"
3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启"IMAP/SMTP服务"
5. 生成授权码（不是QQ密码）

### 3. JWT密钥配置

**重要**：在生产环境中，请务必修改 `secret_key` 为一个强随机字符串！

可以使用以下命令生成随机密钥：
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 安装和运行

### 1. 安装依赖

```bash
cd integerate_qa_system
pip install -r requirements.txt
```

### 2. 初始化数据库

运行以下命令创建数据库表：

```bash
python -c "from mysql_qa.db.mysql_client import MysqlClient; MysqlClient().create_conversation_table()"
```

### 3. 启动后端服务

```bash
python api.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 启动前端服务

```bash
cd ../rag-frontend
npm install
npm run dev
```

前端将在 `http://localhost:5173` 启动。

## API 接口说明

### 认证相关接口

#### 1. 发送验证码
- **URL**: `POST /send-verification-code`
- **请求体**:
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **响应**:
  ```json
  {
    "message": "验证码已发送，请查收邮件",
    "email": "user@example.com"
  }
  ```

#### 2. 登录
- **URL**: `POST /login`
- **请求体**:
  ```json
  {
    "email": "user@example.com",
    "verification_code": "123456"
  }
  ```
- **响应**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user_id": 1,
    "email": "user@example.com",
    "message": "登录成功"
  }
  ```

#### 3. 验证令牌
- **URL**: `GET /verify-token`
- **请求头**: `Authorization: Bearer <token>`
- **响应**:
  ```json
  {
    "valid": true,
    "user_id": 1,
    "email": "user@example.com"
  }
  ```

### 会话相关接口

所有会话相关接口都需要在请求头中携带JWT令牌：`Authorization: Bearer <token>`

#### 1. 创建会话
- **URL**: `POST /sessions/create`
- **响应**:
  ```json
  {
    "session_id": "a1b2c3d4-...",
    "message": "会话创建成功"
  }
  ```

#### 2. 获取用户会话列表
- **URL**: `GET /sessions?limit=20`
- **响应**: 会话列表

#### 3. 获取会话对话历史
- **URL**: `GET /sessions/{session_id}?limit=10`
- **响应**: 对话历史详情

#### 4. 删除会话
- **URL**: `DELETE /sessions/{session_id}`
- **响应**: 删除确认消息

### 查询接口

#### 查询问答
- **URL**: `POST /query`
- **请求头**: `Authorization: Bearer <token>`
- **请求体**:
  ```json
  {
    "query": "什么是人工智能？",
    "source_filter": "ai",
    "session_id": "a1b2c3d4-..."
  }
  ```
- **响应**: SSE流式响应

## 前端使用流程

1. **首次访问**：自动跳转到登录页面
2. **输入邮箱**：输入您的邮箱地址
3. **获取验证码**：点击"发送验证码"按钮
4. **输入验证码**：输入收到的6位验证码
5. **登录**：点击"登录"按钮
6. **开始对话**：登录成功后自动跳转到聊天界面

## 安全注意事项

1. **JWT密钥**：生产环境务必使用强随机密钥
2. **HTTPS**：生产环境建议使用HTTPS
3. **验证码有效期**：验证码5分钟内有效
4. **令牌过期**：JWT令牌30天后过期，需重新登录
5. **会话隔离**：每个用户只能访问自己的会话

## 故障排查

### 1. 验证码发送失败
- 检查QQ邮箱授权码是否正确
- 检查SMTP服务器配置
- 查看后端日志错误信息

### 2. 登录失败
- 检查验证码是否过期（5分钟）
- 检查验证码是否正确
- 检查Redis服务是否正常运行

### 3. JWT令牌验证失败
- 检查令牌是否过期
- 检查JWT密钥配置是否一致
- 清除浏览器localStorage重新登录

## 技术栈

### 后端
- FastAPI - Web框架
- PyJWT - JWT认证
- PyMySQL - MySQL数据库
- Redis - 缓存和验证码存储
- SMTP - 邮件发送

### 前端
- React - UI框架
- Axios - HTTP客户端
- localStorage - 令牌存储

## 更新日志

### v2.0.0 (2024-01-XX)
- ✨ 新增邮箱验证码登录功能
- ✨ 新增JWT令牌认证
- ✨ 新增用户会话管理
- 🔒 增强安全性，会话隔离
- 🎨 优化前端登录界面
- 📝 完善API文档

## 联系方式

如有问题，请联系客服电话：12345678
