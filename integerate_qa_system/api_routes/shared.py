from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from base import Config
from login import AuthService, EmailService
from mysql_qa import RedisClient
from new_main import IntegratedQASystem


qa_system = IntegratedQASystem()
auth_service = AuthService()
email_service = EmailService()
redis_client = RedisClient()


DATA_BASE_PATH = r"d:\WorkSpace\RAG_program\integerate_qa_system\data"
ASSESSMENT_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "rag_qa",
    "rag_accessment",
    "uploads",
)
os.makedirs(ASSESSMENT_UPLOAD_DIR, exist_ok=True)


class Conversation(BaseModel):
    id: Optional[int] = None
    query: str
    answer: str
    timestamp: str
    status: int = 0
    trace_data: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    last_active: str
    first_query: Optional[str] = None


class SessionDetail(BaseModel):
    session_id: str
    conversations: List[Conversation]


class LoginRequest(BaseModel):
    email: str
    verification_code: str


class SendCodeRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    token: str
    user_id: int
    email: str
    is_admin: int
    message: str


class UpdateStatusRequest(BaseModel):
    status: int


class RegenerateConversationRequest(BaseModel):
    answer: str
    trace_data: Optional[str] = None


class CaseDetail(BaseModel):
    id: int
    session_id: str
    query: str
    answer: str
    trace_data: Optional[str] = None
    status: int
    created_at: str


class CaseListResponse(BaseModel):
    cases: List[CaseDetail]
    total: int
    page: int
    page_size: int


class CreateCategoryRequest(BaseModel):
    category_name: str


class UploadFileResponse(BaseModel):
    file_id: int
    file_name: str
    file_path: str
    message: str


class VectorSearchRequest(BaseModel):
    query: str
    source_filter: Optional[str] = None
    top_k: int = 5


class VectorIdRequest(BaseModel):
    vector_id: str


class ChunkRequest(BaseModel):
    file_ids: List[int] = []
    category_id: Optional[int] = None


class ConfigUpdateRequest(BaseModel):
    config_content: str
    change_description: str = ""
    changed_by: str = "user"


class FAQCreate(BaseModel):
    subject_name: str
    question: str
    answer: str


class AssessmentRunRequest(BaseModel):
    file_id: str


async def get_current_user(request: Request):
    authorization = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="认证方案无效，请使用Bearer")
    except ValueError:
        raise HTTPException(status_code=401, detail="认证头格式无效")

    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期，请重新登录")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="令牌缺少用户信息")

    user = qa_system.mysql_client.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在，请重新登录")

    return {
        **payload,
        "user_id": user["id"],
        "email": user["email"],
        "is_admin": int(user.get("is_admin", 0)),
    }


async def get_current_admin(user: dict = Depends(get_current_user)):
    if int(user.get("is_admin", 0)) != 1:
        raise HTTPException(status_code=403, detail="仅管理员可访问该接口")

    return user


def parse_config_content(content):
    result = {}
    current_section = None

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        section_match = re.match(r"^\[(\w+)\]$", line)
        if section_match:
            current_section = section_match.group(1)
            result[current_section] = {}
            continue

        if current_section:
            kv_match = re.match(r"^(.+?)\s*=\s*(.*)$", line)
            if kv_match:
                key = kv_match.group(1).strip()
                value = kv_match.group(2).strip()
                result[current_section][key] = value

    return result


def compare_configs(old_config, new_config):
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
