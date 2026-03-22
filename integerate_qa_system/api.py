# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
import os
from typing import List, Optional
from pydantic import BaseModel
from new_main import IntegratedQASystem
from login import AuthService, EmailService
from mysql_qa import RedisClient
import asyncio


# 创建一个 FastAPI 应用实例
app = FastAPI(title="集成问答系统 API", description="基于 RAG + MySQL + Redis 的问答系统 FastAPI 接口")

# 添加 CORS 中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局初始化一个问答系统实例
qa_system = IntegratedQASystem()
# 初始化认证服务
auth_service = AuthService()
# 初始化邮箱服务
email_service = EmailService()
# 初始化Redis客户端用于存储验证码
redis_client = RedisClient()


# ==================== 数据模型定义 ====================

# 定义会话历史的数据模型
class Conversation(BaseModel):
    query: str
    answer: str
    timestamp: str


# 定义会话列表的数据模型
class SessionInfo(BaseModel):
    session_id: str
    last_active: str


# 定义会话详情的数据模型
class SessionDetail(BaseModel):
    session_id: str
    conversations: List[Conversation]


# 定义登录请求数据模型
class LoginRequest(BaseModel):
    email: str
    verification_code: str


# 定义发送验证码请求数据模型
class SendCodeRequest(BaseModel):
    email: str


# 定义登录响应数据模型
class LoginResponse(BaseModel):
    token: str
    user_id: int
    email: str
    message: str


# ==================== 认证依赖函数 ====================

async def get_current_user(request: Request):
    """
    从请求头中获取并验证JWT令牌，返回当前用户信息
    
    Returns:
        dict: 包含user_id和email的用户信息
        
    Raises:
        HTTPException: 令牌无效或过期时抛出401错误
    """
    # 从请求头获取Authorization字段
    authorization = request.headers.get("Authorization")
    
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="未提供认证令牌"
        )
    
    # 检查格式：Bearer <token>
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="认证方案无效，请使用Bearer"
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="认证头格式无效"
        )
    
    # 验证令牌
    payload = auth_service.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="令牌无效或已过期，请重新登录"
        )
    
    return payload


# ==================== 登录相关接口 ====================

@app.post("/send-verification-code")
async def send_verification_code(request: SendCodeRequest):
    """
    发送验证码到指定邮箱
    
    请求体示例：
    {
        "email": "user@example.com"
    }
    """
    email = request.email.strip()
    
    if not email:
        raise HTTPException(status_code=400, detail="邮箱地址不能为空")
    
    code = email_service.generate_verification_code()
    
    success = email_service.send_verification_code(email, code)
    
    if not success:
        print(f"\n{'='*50}")
        print(f"[开发模式] 验证码: {code} (邮箱: {email})")
        print(f"{'='*50}\n")
        qa_system.logger.warning(f"邮件发送失败，验证码已打印到控制台: {code}")
    
    redis_key = f"verification_code:{email}"
    redis_client.client.setex(redis_key, 300, code)
    
    return {"message": "验证码已发送，请查收邮件（如未收到请查看控制台）", "email": email}


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    用户登录接口，验证邮箱和验证码，返回JWT令牌
    
    请求体示例：
    {
        "email": "user@example.com",
        "verification_code": "123456"
    }
    """
    email = request.email.strip()
    code = request.verification_code.strip()
    
    if not email or not code:
        raise HTTPException(status_code=400, detail="邮箱和验证码不能为空")
    
    # 从Redis获取验证码
    redis_key = f"verification_code:{email}"
    stored_code = redis_client.client.get(redis_key)
    
    if not stored_code:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    
    # 验证码比对（Redis返回的是字符串，因为设置了decode_responses=True）
    if stored_code != code:
        raise HTTPException(status_code=400, detail="验证码错误")
    
    # 验证成功，删除Redis中的验证码
    redis_client.client.delete(redis_key)
    
    # 获取或创建用户
    user_id = qa_system.mysql_client.get_or_create_user(email)
    
    # 生成JWT令牌
    token = auth_service.generate_token(user_id, email)
    
    return LoginResponse(
        token=token,
        user_id=user_id,
        email=email,
        message="登录成功"
    )


@app.get("/verify-token")
async def verify_token(user: dict = Depends(get_current_user)):
    """
    验证令牌有效性
    
    需要在请求头中携带：Authorization: Bearer <token>
    """
    return {
        "valid": True,
        "user_id": user["user_id"],
        "email": user["email"]
    }


# ==================== 问答相关接口 ====================

# 使用 @app.post 装饰器，将下面的函数注册为 POST 请求接口，路径为 /query
@app.post("/query")
async def handle_query(request: Request, user: dict = Depends(get_current_user)):
    """
    接收客户端发送的 JSON 请求，支持流式返回答案。
    需要在请求头中携带：Authorization: Bearer <token>
    请求体示例：
    {
        "query": "什么是人工智能？",
        "source_filter": "ai",  // 可选，用于学科过滤
        "session_id": "a1b2c3d4-..."   // 可选，用于维护对话历史
    }
    响应为 SSE（Server-Sent Events）流式格式，前端可实时接收每个 token。
    """

    # 尝试解析请求体中的 JSON 数据
    try:
        body = await request.json()
    # 如果 JSON 格式不合法（如缺少引号、语法错误），抛出 400 错误
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON 数据")

    # 从 JSON 中获取用户问题，去除首尾空格，若无则为空字符串
    query = body.get("query", "").strip()
    # 获取学科过滤条件（可选），若未提供则为 None
    source_filter = body.get("source_filter", None)
    # 获取会话 ID（可选），用于维护多轮对话历史
    session_id = body.get("session_id", None)

    # 如果用户没有输入问题，返回 400 错误
    if not query:
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    # 如果客户端未提供 session_id，则自动生成一个全局唯一 ID
    if not session_id:
        session_id = str(uuid.uuid4())

    # 从配置中获取支持的学科类别列表（如 ['ai', 'java']）
    valid_sources = qa_system.config.VALID_SOURCES
    # 如果提供了 source_filter 但不在合法范围内，返回 400 错误
    if source_filter and source_filter not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"无效的学科类别。支持: {valid_sources}"
        )

    # 定义一个生成器函数，用于流式返回答案（逐 token 输出）
    def generate_response():
        try:
            # 调用问答系统的核心 query 方法，返回生成器（每次产出一个 token）
            for token, is_complete in qa_system.query(
                query=query,
                source_filter=source_filter,
                session_id=session_id
            ):
                # 构造要返回的 JSON 消息，包含当前文本片段和状态
                message = {
                    "token": token,           # 当前生成的文本（如一个字）
                    "is_complete": is_complete,     # 是否是最后一个 token
                    "session_id": session_id        # 返回会话 ID，便于前端维护
                }
                # 使用 SSE 格式：data: {json}\n\n
                # ensure_ascii=False 确保中文不被转义为 \uXXXX
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

        # 捕获问答系统内部任何异常（如数据库错误、LLM 调用失败）
        except Exception as e:
            # 记录错误日志
            error_msg = f"处理查询时发生错误: {str(e)}"
            qa_system.logger.error(error_msg)
            # 构造错误消息，标记流结束
            message = {
                "error": error_msg,          # 错误信息
                "is_complete": True          # 表示流已结束
            }
            # 同样以 SSE 格式返回错误
            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

    # 返回流式响应，媒体类型为 text/event-stream（SSE 标准）
    return StreamingResponse(
        generate_response(),           # 传入生成器函数
        media_type="text/event-stream" # 告诉浏览器这是流式数据
    )


@app.get("/sessions", response_model=List[SessionInfo])
async def get_sessions(limit: int = 20, user: dict = Depends(get_current_user)):
    """
    获取当前用户的会话列表
    需要在请求头中携带：Authorization: Bearer <token>
    参数：
        limit: 返回的会话数量，默认为 20
    返回：
        会话列表，包含 session_id 和最后活跃时间
    """
    try:
        user_id = user["user_id"]
        sessions = qa_system.mysql_client.get_user_sessions(user_id, limit=limit)
        return [
            SessionInfo(
                session_id=session[0], 
                last_active=session[1].strftime("%Y-%m-%d %H:%M:%S") if session[1] else "无对话记录"
            )
            for session in sessions
        ]
    except Exception as e:
        qa_system.logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@app.post("/sessions/create")
async def create_session(user: dict = Depends(get_current_user)):
    """
    创建新会话
    需要在请求头中携带：Authorization: Bearer <token>
    返回：
        新创建的session_id
    """
    try:
        user_id = user["user_id"]
        session_id = str(uuid.uuid4())
        
        # 在user_session表中创建会话记录
        success = qa_system.mysql_client.create_user_session(user_id, session_id)
        
        if success:
            return {"session_id": session_id, "message": "会话创建成功"}
        else:
            raise HTTPException(status_code=500, detail="会话创建失败")
    except Exception as e:
        qa_system.logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@app.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session_conversations(
    session_id: str, 
    limit: int = 10, 
    user: dict = Depends(get_current_user)
):
    """
    获取指定会话的对话历史
    需要在请求头中携带：Authorization: Bearer <token>
    参数：
        session_id: 会话 ID
        limit: 返回的对话数量，默认为 10
    返回：
        会话详情，包含 session_id 和对话列表
    """
    try:
        user_id = user["user_id"]
        
        # 验证会话是否属于当前用户
        if not qa_system.mysql_client.verify_session_owner(session_id, user_id):
            raise HTTPException(status_code=403, detail="无权访问此会话")
        
        conversations = qa_system.mysql_client.fetch_conversations(session_id, limit=limit)
        return SessionDetail(
            session_id=session_id,
            conversations=[
                Conversation(
                    query=conv[0],
                    answer=conv[1],
                    timestamp=conv[2].strftime("%Y-%m-%d %H:%M:%S")
                )
                # 反转结果，按时间正序返回
                for conv in conversations[::-1]
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取会话对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话对话历史失败: {str(e)}")


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    """
    软删除指定会话（将status设为0，不实际删除数据）
    需要在请求头中携带：Authorization: Bearer <token>
    参数：
        session_id: 会话 ID
    返回：
        成功消息
    """
    try:
        user_id = user["user_id"]
        
        success = qa_system.mysql_client.soft_delete_session(session_id, user_id)
        if success:
            return {"message": f"会话 {session_id} 已删除"}
        else:
            raise HTTPException(status_code=404, detail="会话不存在或无权删除")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


DATA_BASE_PATH = r"d:\WorkSpace\RAG_program\integerate_qa_system\data"


class CreateCategoryRequest(BaseModel):
    category_name: str


class UploadFileResponse(BaseModel):
    file_id: int
    file_name: str
    file_path: str
    message: str


@app.get("/knowledge/files")
async def get_knowledge_files(category_id: int = None, user: dict = Depends(get_current_user)):
    """
    获取知识库文件列表
    
    参数：
        category_id: 分类ID，为空时显示所有分类文件夹
    返回：
        当前分类下的文件夹和文件列表（从数据库获取）
    """
    try:
        if category_id is None:
            categories = qa_system.mysql_client.get_all_categories()
            items = []
            for cat in categories:
                items.append({
                    'id': f"cat_{cat['id']}",
                    'name': cat['category'],
                    'path': cat['category'],
                    'is_dir': True,
                    'file_type': '',
                    'is_chunk': False,
                    'category_id': cat['id']
                })
            
            return {
                "files": items,
                "current_path": "",
                "parent_path": None,
                "category_id": None,
                "category_name": None
            }
        else:
            category = qa_system.mysql_client.get_category_by_id(category_id)
            if not category:
                raise HTTPException(status_code=404, detail="分类不存在")
            
            db_files = qa_system.mysql_client.get_files_by_category(category_id)
            
            items = []
            for f in db_files:
                file_name = os.path.basename(f['file_path'])
                file_ext = os.path.splitext(file_name)[1].lower() if not f['is_dir'] else ''
                
                items.append({
                    'id': f['id'],
                    'name': file_name,
                    'path': f['file_path'],
                    'is_dir': f['is_dir'],
                    'file_type': file_ext,
                    'is_chunk': f['is_chunk'],
                    'category_id': category_id
                })
            
            folders = [item for item in items if item['is_dir']]
            files = [item for item in items if not item['is_dir']]
            sorted_items = folders + files
            
            return {
                "files": sorted_items,
                "current_path": category['category'],
                "parent_path": None,
                "category_id": category_id,
                "category_name": category['category']
            }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.post("/knowledge/categories")
async def create_category(request: CreateCategoryRequest, user: dict = Depends(get_current_user)):
    """
    创建知识库分类
    
    请求体示例：
    {
        "category_name": "人工智能"
    }
    """
    try:
        category_name = request.category_name.strip()
        if not category_name:
            raise HTTPException(status_code=400, detail="分类名称不能为空")
        
        result = qa_system.mysql_client.create_category(category_name, DATA_BASE_PATH)
        
        return {
            "message": "分类创建成功",
            "category_id": result['category_id'],
            "folder_path": result['folder_path']
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        qa_system.logger.error(f"创建分类失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建分类失败: {str(e)}")


@app.get("/knowledge/categories")
async def get_categories(user: dict = Depends(get_current_user)):
    """
    获取所有知识库分类
    """
    try:
        categories = qa_system.mysql_client.get_all_categories()
        return {"categories": categories}
    except Exception as e:
        qa_system.logger.error(f"获取分类列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@app.delete("/knowledge/categories/{category_id}")
async def delete_category(category_id: int, user: dict = Depends(get_current_user)):
    """
    删除知识库分类
    """
    try:
        success = qa_system.mysql_client.delete_category(category_id)
        if success:
            return {"message": "分类删除成功"}
        else:
            raise HTTPException(status_code=404, detail="分类不存在")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除分类失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除分类失败: {str(e)}")


@app.get("/knowledge/categories/{category_id}/files")
async def get_category_files(category_id: int, user: dict = Depends(get_current_user)):
    """
    获取指定分类下的所有文件和文件夹
    """
    try:
        files = qa_system.mysql_client.get_files_by_category(category_id)
        
        result_files = []
        for f in files:
            file_name = os.path.basename(f['file_path'])
            file_ext = os.path.splitext(file_name)[1].lower() if not f['is_dir'] else ''
            
            result_files.append({
                'id': f['id'],
                'name': file_name,
                'path': f['file_path'],
                'is_dir': f['is_dir'],
                'is_chunk': f['is_chunk'],
                'category_id': f['category_id'],
                'file_type': file_ext
            })
        
        return {"files": result_files}
    except Exception as e:
        qa_system.logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.get("/knowledge/files/{file_id}")
async def get_file_info(file_id: int, user: dict = Depends(get_current_user)):
    """
    获取文件详情
    """
    try:
        file_info = qa_system.mysql_client.get_file_by_id(file_id)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        file_name = os.path.basename(file_info['file_path'])
        file_ext = os.path.splitext(file_name)[1].lower() if not file_info['is_dir'] else ''
        
        return {
            'id': file_info['id'],
            'name': file_name,
            'path': file_info['file_path'],
            'is_dir': file_info['is_dir'],
            'is_chunk': file_info['is_chunk'],
            'category_id': file_info['category_id'],
            'file_type': file_ext
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取文件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@app.get("/knowledge/files/{file_id}/preview")
async def preview_file(file_id: int, user: dict = Depends(get_current_user)):
    """
    预览文件内容
    """
    try:
        file_info = qa_system.mysql_client.get_file_by_id(file_id)
        
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if file_info['is_dir']:
            raise HTTPException(status_code=400, detail="无法预览文件夹")
        
        file_path = file_info['file_path']
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在于文件系统")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        
        if file_ext in ['.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.xml', '.html', '.css', '.sql', '.java', '.c', '.cpp', '.h', '.sh', '.yaml', '.yml', '.ini', '.cfg', '.log']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return {
                'file_name': file_name,
                'file_type': 'text',
                'content': content
            }
        elif file_ext == '.pdf':
            return {
                'file_name': file_name,
                'file_type': 'pdf',
                'content': None,
                'message': 'PDF文件需要专用查看器'
            }
        elif file_ext in ['.doc', '.docx']:
            return {
                'file_name': file_name,
                'file_type': 'word',
                'content': None,
                'message': 'Word文件需要专用查看器'
            }
        elif file_ext in ['.xls', '.xlsx']:
            return {
                'file_name': file_name,
                'file_type': 'excel',
                'content': None,
                'message': 'Excel文件需要专用查看器'
            }
        elif file_ext in ['.ppt', '.pptx']:
            return {
                'file_name': file_name,
                'file_type': 'ppt',
                'content': None,
                'message': 'PPT文件需要专用查看器'
            }
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            import base64
            with open(file_path, 'rb') as f:
                file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
            return {
                'file_name': file_name,
                'file_type': 'image',
                'content': base64_content,
                'mime_type': f'image/{file_ext[1:]}'
            }
        else:
            return {
                'file_name': file_name,
                'file_type': 'unknown',
                'content': None,
                'message': '不支持的文件类型'
            }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"预览文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")


@app.get("/knowledge/preview")
async def preview_file_by_path(path: str, user: dict = Depends(get_current_user)):
    """
    根据路径预览文件内容
    """
    try:
        file_path = os.path.join(DATA_BASE_PATH, path)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if os.path.isdir(file_path):
            raise HTTPException(status_code=400, detail="无法预览文件夹")
        
        if not file_path.startswith(DATA_BASE_PATH):
            raise HTTPException(status_code=403, detail="无权访问此文件")
        
        import base64
        
        file_ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        TEXT_EXTENSIONS = ['.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.xml', '.html', '.css', '.sql', '.java', '.c', '.cpp', '.h', '.hpp', '.sh', '.bash', '.yaml', '.yml', '.ini', '.cfg', '.log', '.toml', '.vue', '.svelte', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.ps1', '.scss', '.less']
        IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
        
        if file_ext in TEXT_EXTENSIONS:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if file_ext == '.md':
                file_type = 'markdown'
            elif file_ext in ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.sql', '.sh', '.bash', '.ps1', '.vue', '.svelte', '.css', '.scss', '.less', '.html', '.json', '.xml', '.yaml', '.yml', '.toml']:
                file_type = 'code'
            else:
                file_type = 'text'
            
            return {
                'file_name': file_name,
                'file_type': file_type,
                'file_ext': file_ext,
                'content': content,
                'file_size': file_size
            }
        elif file_ext == '.pdf':
            with open(file_path, 'rb') as f:
                file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
            return {
                'file_name': file_name,
                'file_type': 'pdf',
                'file_ext': file_ext,
                'content': base64_content,
                'file_size': file_size
            }
        elif file_ext in ['.doc', '.docx']:
            if file_ext == '.doc':
                return {
                    'file_name': file_name,
                    'file_type': 'word',
                    'file_ext': file_ext,
                    'content': None,
                    'file_size': file_size,
                    'message': '旧版.doc格式不支持预览，请转换为.docx格式'
                }
            try:
                import mammoth
                with open(file_path, 'rb') as f:
                    result = mammoth.convert_to_html(f)
                    html_content = result.value
                    messages = result.messages
                return {
                    'file_name': file_name,
                    'file_type': 'word',
                    'file_ext': file_ext,
                    'content': html_content,
                    'file_size': file_size,
                    'warnings': [str(m) for m in messages] if messages else []
                }
            except ImportError:
                return {
                    'file_name': file_name,
                    'file_type': 'word',
                    'file_ext': file_ext,
                    'content': None,
                    'file_size': file_size,
                    'message': '服务器未安装mammoth库，无法预览Word文件'
                }
            except Exception as e:
                return {
                    'file_name': file_name,
                    'file_type': 'word',
                    'file_ext': file_ext,
                    'content': None,
                    'file_size': file_size,
                    'message': f'Word文件解析失败: {str(e)}'
                }
        elif file_ext in ['.xls', '.xlsx']:
            return {
                'file_name': file_name,
                'file_type': 'excel',
                'file_ext': file_ext,
                'content': None,
                'file_size': file_size,
                'message': 'Excel文件需要专用查看器'
            }
        elif file_ext in ['.ppt', '.pptx']:
            return {
                'file_name': file_name,
                'file_type': 'ppt',
                'file_ext': file_ext,
                'content': None,
                'file_size': file_size,
                'message': 'PPT文件需要专用查看器'
            }
        elif file_ext in IMAGE_EXTENSIONS:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
            mime_type = 'image/svg+xml' if file_ext == '.svg' else f'image/{file_ext[1:]}'
            return {
                'file_name': file_name,
                'file_type': 'image',
                'file_ext': file_ext,
                'content': base64_content,
                'mime_type': mime_type,
                'file_size': file_size
            }
        else:
            return {
                'file_name': file_name,
                'file_type': 'unknown',
                'file_ext': file_ext,
                'content': None,
                'file_size': file_size,
                'message': '不支持的文件类型'
            }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"预览文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")


class VectorSearchRequest(BaseModel):
    query: str
    source_filter: Optional[str] = None
    top_k: int = 5


@app.post("/knowledge/search")
async def vector_search(request: VectorSearchRequest, user: dict = Depends(get_current_user)):
    """
    向量检索接口 - 使用混合检索和重排序
    """
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")
        
        query = request.query.strip()
        top_k = min(request.top_k, 20)
        
        results = qa_system.vector_store.hybrid_search_with_rerank(
            query=query,
            k=top_k,
            source_filter=request.source_filter
        )
        
        search_results = []
        for i, doc in enumerate(results):
            search_results.append({
                'id': i + 1,
                'content': doc.page_content,
                'parent_content': doc.metadata.get('parent_content', ''),
                'source': doc.metadata.get('source', 'unknown'),
                'timestamp': doc.metadata.get('timestamp', ''),
                'file_path': doc.metadata.get('file_path', ''),
                'parent_id': doc.metadata.get('parent_id', ''),
            })
        
        return {
            'query': query,
            'source_filter': request.source_filter,
            'total': len(search_results),
            'results': search_results
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"向量检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"向量检索失败: {str(e)}")


@app.get("/knowledge/sources")
async def get_knowledge_sources(user: dict = Depends(get_current_user)):
    """
    获取知识库来源列表
    """
    try:
        sources = qa_system.mysql_client.get_all_categories()
        source_list = [{'id': cat['id'], 'name': cat['category']} for cat in sources]
        return {'sources': source_list}
    except Exception as e:
        qa_system.logger.error(f"获取知识库来源失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取知识库来源失败: {str(e)}")


from fastapi import UploadFile, File, Form


@app.post("/knowledge/categories/{category_id}/upload", response_model=UploadFileResponse)
async def upload_file(
    category_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user)
):
    """
    上传文件到指定分类
    """
    try:
        category = qa_system.mysql_client.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")
        
        category_folder = os.path.join(DATA_BASE_PATH, category['category'])
        os.makedirs(category_folder, exist_ok=True)
        
        file_path = os.path.join(category_folder, file.filename)
        
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        file_id = qa_system.mysql_client.add_file(
            file_path=file_path,
            is_dir=False,
            category_id=category_id,
            is_chunk=False
        )
        
        return UploadFileResponse(
            file_id=file_id,
            file_name=file.filename,
            file_path=file_path,
            message="文件上传成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@app.delete("/knowledge/files/{file_id}")
async def delete_file(file_id: int, user: dict = Depends(get_current_user)):
    """
    删除文件
    """
    try:
        success = qa_system.mysql_client.delete_file(file_id)
        if success:
            return {"message": "文件删除成功"}
        else:
            raise HTTPException(status_code=404, detail="文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


class ChunkRequest(BaseModel):
    file_ids: List[int] = []
    category_id: Optional[int] = None


@app.post("/knowledge/chunk")
async def chunk_files(request: ChunkRequest, user: dict = Depends(get_current_user)):
    """
    对文件进行切片处理（SSE流式返回进度）
    - file_ids: 指定文件ID列表（支持文件夹ID，会递归获取文件夹下所有文件）
    - category_id: 指定分类ID（切片该分类下所有未切片文件）
    """
    from rag_qa.core.document_process import process_single_file
    
    def collect_files_from_folder(folder_id, collected_files):
        folder_files = qa_system.mysql_client.get_files_by_parent_folder(folder_id)
        for f in folder_files:
            if f['is_dir']:
                collect_files_from_folder(f['id'], collected_files)
            elif not f['is_chunk']:
                collected_files.append(f)
    
    def generate():
        files_to_chunk = []
        
        if request.file_ids:
            for file_id in request.file_ids:
                file_info = qa_system.mysql_client.get_file_by_id(file_id)
                if file_info:
                    if file_info['is_dir']:
                        collect_files_from_folder(file_id, files_to_chunk)
                    elif not file_info['is_chunk']:
                        files_to_chunk.append(file_info)
        elif request.category_id:
            all_files = qa_system.mysql_client.get_files_by_category(request.category_id)
            for f in all_files:
                if not f['is_chunk'] and not f['is_dir']:
                    files_to_chunk.append(f)
        
        if not files_to_chunk:
            yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': '没有需要切片的文件', 'total': 0, 'results': []}, ensure_ascii=False)}\n\n"
            return
        
        total = len(files_to_chunk)
        results = []
        completed = 0
        
        yield f"data: {json.dumps({'type': 'start', 'total': total, 'completed': 0}, ensure_ascii=False)}\n\n"
        
        for i, file_info in enumerate(files_to_chunk):
            file_path = file_info['file_path']
            file_id = file_info['id']
            file_name = os.path.basename(file_path)
            
            try:
                category = qa_system.mysql_client.get_category_by_id(file_info['category_id'])
                source = category['category'] if category else 'unknown'
                
                child_chunks = process_single_file(file_path, source=source)
                
                if child_chunks is None or len(child_chunks) == 0:
                    completed += 1
                    results.append({
                        'file_id': file_id,
                        'file_name': file_name,
                        'status': 'failed',
                        'error': '文件加载或切分失败，未生成任何切片'
                    })
                    yield f"data: {json.dumps({'type': 'result', 'file_id': file_id, 'file_name': file_name, 'status': 'failed', 'error': '文件加载或切分失败', 'completed': completed, 'total': total}, ensure_ascii=False)}\n\n"
                    continue
                
                for chunk in child_chunks:
                    chunk.metadata['file_id'] = file_id
                
                qa_system.vector_store.add_documents(child_chunks)
                
                qa_system.mysql_client.update_file_chunk_status(file_id, True)
                
                completed += 1
                results.append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'status': 'success',
                    'chunks': len(child_chunks)
                })
                yield f"data: {json.dumps({'type': 'result', 'file_id': file_id, 'file_name': file_name, 'status': 'success', 'chunks': len(child_chunks), 'completed': completed, 'total': total}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                qa_system.logger.error(f"切片文件失败 {file_name}: {e}")
                completed += 1
                results.append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'status': 'failed',
                    'error': str(e)
                })
                yield f"data: {json.dumps({'type': 'result', 'file_id': file_id, 'file_name': file_name, 'status': 'failed', 'error': str(e), 'completed': completed, 'total': total}, ensure_ascii=False)}\n\n"
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': f'切片完成，成功 {success_count}/{total}', 'total': total, 'results': results}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/knowledge/files/unchunked")
async def get_unchunked_files(category_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    """
    获取未切片的文件列表
    """
    try:
        if category_id:
            all_files = qa_system.mysql_client.get_files_by_category(category_id)
        else:
            all_files = qa_system.mysql_client.get_all_files()
        
        unchunked_files = [f for f in all_files if not f['is_chunk'] and not f['is_dir']]
        
        return {
            'total': len(unchunked_files),
            'files': unchunked_files
        }
    except Exception as e:
        qa_system.logger.error(f"获取未切片文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取未切片文件失败: {str(e)}")


@app.get("/knowledge/files/{file_id}/chunks")
async def get_file_chunks(file_id: int, user: dict = Depends(get_current_user)):
    """
    获取文件的所有切片内容
    """
    try:
        file_info = qa_system.mysql_client.get_file_by_id(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_info['is_chunk']:
            return {
                'file_id': file_id,
                'file_path': file_info['file_path'],
                'is_chunk': False,
                'total': 0,
                'chunks': []
            }
        
        file_path = file_info['file_path']
        chunks = qa_system.vector_store.get_chunks_by_file_path(file_path)
        
        return {
            'file_id': file_id,
            'file_path': file_path,
            'is_chunk': True,
            'total': len(chunks),
            'chunks': chunks
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取文件切片失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件切片失败: {str(e)}")


@app.get("/knowledge/supported-types")
async def get_supported_file_types():
    """
    获取系统支持的文件类型列表
    """
    from rag_qa.core.document_process import SUPPORTED_EXTENSIONS
    return {
        'supported_extensions': SUPPORTED_EXTENSIONS
    }


@app.on_event("startup")
async def startup_event():
    try:
        qa_system.mysql_client.create_knowledge_tables()
        qa_system.logger.info("知识库表初始化完成")
        qa_system.mysql_client.create_config_version_table()
        qa_system.logger.info("配置版本表初始化完成")
    except Exception as e:
        qa_system.logger.error(f"知识库表初始化失败: {e}")


@app.get("/config")
async def get_config(user: dict = Depends(get_current_user)):
    """
    获取当前配置信息
    """
    try:
        from base import Config
        Config._config_cache = None
        config = Config()
        if hasattr(config, '_force_reload'):
            delattr(config, '_force_reload')
        
        config_data = {
            'mysql': {
                'host': config.MYSQL_HOST,
                'user': config.MYSQL_USER,
                'password': '******',
                'database': config.MYSQL_DATABASE
            },
            'redis': {
                'host': config.REDIS_HOST,
                'port': config.REDIS_PORT,
                'password': '******',
                'db': config.REDIS_DB
            },
            'milvus': {
                'host': config.MILVUS_HOST,
                'port': config.MILVUS_PORT,
                'database_name': config.MILVUS_DATABASE_NAME,
                'collection_name': config.MILVUS_COLLECTION_NAME
            },
            'llm': {
                'model': config.LLM_MODEL,
                'dashscope_api_key': '******',
                'dashscope_base_url': config.DASHSCOPE_BASE_URL
            },
            'retrieval': {
                'parent_chunk_size': config.PARENT_CHUNK_SIZE,
                'child_chunk_size': config.CHILD_CHUNK_SIZE,
                'chunk_overlap': config.CHUNK_OVERLAP,
                'retrieval_k': config.RETRIEVAL_K,
                'candidate_m': config.CANDIDATE_M
            },
            'logger': {
                'log_file': config.LOG_FILE
            },
            'app': {
                'valid_sources': config.VALID_SOURCES,
                'customer_service_phone': config.CUSTOMER_SERVICE_PHONE
            },
            'email': {
                'qq_email': config.QQ_EMAIL,
                'qq_auth_code': '******',
                'smtp_server': config.SMTP_SERVER,
                'smtp_port': config.SMTP_PORT
            },
            'jwt': {
                'secret_key': '******',
                'algorithm': config.JWT_ALGORITHM,
                'expire_days': config.JWT_EXPIRE_DAYS
            }
        }
        
        return {
            'success': True,
            'config': config_data
        }
    except Exception as e:
        qa_system.logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@app.get("/config/raw")
async def get_raw_config(user: dict = Depends(get_current_user)):
    """
    获取原始配置文件内容
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            'success': True,
            'content': content
        }
    except Exception as e:
        qa_system.logger.error(f"获取原始配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取原始配置失败: {str(e)}")


def parse_config_content(content):
    """解析配置文件内容为字典"""
    import re
    result = {}
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        section_match = re.match(r'^\[(\w+)\]$', line)
        if section_match:
            current_section = section_match.group(1)
            result[current_section] = {}
            continue
        
        if current_section:
            kv_match = re.match(r'^(.+?)\s*=\s*(.*)$', line)
            if kv_match:
                key = kv_match.group(1).strip()
                value = kv_match.group(2).strip()
                result[current_section][key] = value
    
    return result


def compare_configs(old_config, new_config):
    """比较两个配置，返回变更的配置项列表"""
    changed = []
    
    all_sections = set(old_config.keys()) | set(new_config.keys())
    
    for section in all_sections:
        old_section = old_config.get(section, {})
        new_section = new_config.get(section, {})
        
        all_keys = set(old_section.keys()) | set(new_section.keys())
        
        for key in all_keys:
            old_value = old_section.get(key)
            new_value = new_section.get(key)
            
            if old_value != new_value:
                changed.append((section, key))
    
    return changed


class ConfigUpdateRequest(BaseModel):
    config_content: str
    change_description: str = ""
    changed_by: str = "user"


@app.post("/config")
async def update_config(request: ConfigUpdateRequest, user: dict = Depends(get_current_user)):
    """
    更新配置文件并执行热加载
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        old_config = parse_config_content(old_content)
        new_config = parse_config_content(request.config_content)
        
        changed_items = compare_configs(old_config, new_config)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(request.config_content)
        
        import datetime
        version = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        qa_system.mysql_client.save_config_version(
            version=version,
            config_content=request.config_content,
            change_description=request.change_description,
            changed_by=request.changed_by
        )
        
        from base.config import Config
        Config.hot_reload()
        
        reloaded_items = []
        not_reloaded_items = []
        
        for section, key in changed_items:
            item_name = f"{section}.{key}"
            if section in ['llm', 'retrieval', 'app', 'email', 'jwt']:
                reloaded_items.append(item_name)
            else:
                not_reloaded_items.append(item_name)
        
        reload_messages = []
        if reloaded_items:
            reload_messages.append(f"以下 {len(reloaded_items)} 项配置已热加载成功")
        if not_reloaded_items:
            reload_messages.append(f"以下 {len(not_reloaded_items)} 项配置需要重启后端服务才能生效")
        
        return {
            'success': True,
            'message': '配置更新成功',
            'version': version,
            'hot_reload': {
                'reloaded': reloaded_items,
                'not_reloaded': not_reloaded_items,
                'reloaded_count': len(reloaded_items),
                'not_reloaded_count': len(not_reloaded_items),
                'messages': reload_messages
            }
        }
    except Exception as e:
        qa_system.logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@app.get("/config/versions")
async def get_config_versions(limit: int = 20, user: dict = Depends(get_current_user)):
    """
    获取配置版本列表
    """
    try:
        versions = qa_system.mysql_client.get_config_versions(limit)
        return {
            'success': True,
            'versions': versions,
            'total': len(versions)
        }
    except Exception as e:
        qa_system.logger.error(f"获取配置版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置版本列表失败: {str(e)}")


@app.get("/config/versions/{version_id}")
async def get_config_version_detail(version_id: int, user: dict = Depends(get_current_user)):
    """
    获取指定版本的配置详情
    """
    try:
        version = qa_system.mysql_client.get_config_by_id(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")
        return {
            'success': True,
            'version': version
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取配置版本详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置版本详情失败: {str(e)}")


@app.post("/config/rollback/{version_id}")
async def rollback_config(version_id: int, user: dict = Depends(get_current_user)):
    """
    回退到指定配置版本
    """
    try:
        version = qa_system.mysql_client.get_config_by_id(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            old_content = f.read()
        
        old_config = parse_config_content(old_content)
        new_config = parse_config_content(version['config_content'])
        
        changed_items = compare_configs(old_config, new_config)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(version['config_content'])
        
        rollback_result = qa_system.mysql_client.rollback_config(version_id)
        
        from base.config import Config
        Config.hot_reload()
        
        reloaded_items = []
        not_reloaded_items = []
        
        for section, key in changed_items:
            item_name = f"{section}.{key}"
            if section in ['llm', 'retrieval', 'app', 'email', 'jwt']:
                reloaded_items.append(item_name)
            else:
                not_reloaded_items.append(item_name)
        
        reload_messages = []
        if reloaded_items:
            reload_messages.append(f"以下 {len(reloaded_items)} 项配置已热加载成功")
        if not_reloaded_items:
            reload_messages.append(f"以下 {len(not_reloaded_items)} 项配置需要重启后端服务才能生效")
        
        return {
            'success': True,
            'message': f'已回退到版本 {rollback_result["original_version"]}',
            'rollback_version': rollback_result['version'],
            'hot_reload': {
                'reloaded': reloaded_items,
                'not_reloaded': not_reloaded_items,
                'reloaded_count': len(reloaded_items),
                'not_reloaded_count': len(not_reloaded_items),
                'messages': reload_messages
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"配置回退失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置回退失败: {str(e)}")


@app.get("/faq")
async def get_faqs(search: str = None, user: dict = Depends(get_current_user)):
    """获取所有FAQ，支持模糊搜索"""
    try:
        faqs = qa_system.mysql_client.get_all_faqs(search_keyword=search)
        return {'faqs': faqs}
    except Exception as e:
        qa_system.logger.error(f"获取FAQ列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取FAQ列表失败: {str(e)}")


@app.get("/faq/{faq_id}")
async def get_faq(faq_id: int, user: dict = Depends(get_current_user)):
    """获取单个FAQ"""
    try:
        faq = qa_system.mysql_client.get_faq_by_id(faq_id)
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        return faq
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取FAQ详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取FAQ详情失败: {str(e)}")


class FAQCreate(BaseModel):
    subject_name: str
    question: str
    answer: str


@app.post("/faq")
async def create_faq(faq: FAQCreate, user: dict = Depends(get_current_user)):
    """创建FAQ"""
    try:
        faq_id = qa_system.mysql_client.add_faq(
            faq.subject_name,
            faq.question,
            faq.answer
        )
        return {'success': True, 'id': faq_id, 'message': 'FAQ创建成功'}
    except Exception as e:
        qa_system.logger.error(f"创建FAQ失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建FAQ失败: {str(e)}")


@app.put("/faq/{faq_id}")
async def update_faq(faq_id: int, faq: FAQCreate, user: dict = Depends(get_current_user)):
    """更新FAQ"""
    try:
        success = qa_system.mysql_client.update_faq(
            faq_id,
            faq.subject_name,
            faq.question,
            faq.answer
        )
        if not success:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        return {'success': True, 'message': 'FAQ更新成功'}
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"更新FAQ失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新FAQ失败: {str(e)}")


@app.delete("/faq/{faq_id}")
async def delete_faq(faq_id: int, user: dict = Depends(get_current_user)):
    """删除FAQ"""
    try:
        success = qa_system.mysql_client.delete_faq(faq_id)
        if not success:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        return {'success': True, 'message': 'FAQ删除成功'}
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除FAQ失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除FAQ失败: {str(e)}")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




