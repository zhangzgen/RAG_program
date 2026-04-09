import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from .shared import (
    Conversation,
    RegenerateConversationRequest,
    SessionDetail,
    SessionInfo,
    UpdateStatusRequest,
    get_current_admin,
    get_current_user,
    qa_system,
)


router = APIRouter()


@router.get("/sessions", response_model=List[SessionInfo])
async def get_sessions(limit: int = 20, user: dict = Depends(get_current_user)):
    try:
        user_id = user["user_id"]
        sessions = qa_system.mysql_client.get_user_sessions(user_id, limit=limit)
        return [
            SessionInfo(
                session_id=session[0],
                last_active=session[1].strftime("%Y-%m-%d %H:%M:%S") if session[1] else "无对话记录",
                first_query=session[2] if len(session) > 2 else None,
            )
            for session in sessions
        ]
    except Exception as e:
        qa_system.logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.post("/sessions/create")
async def create_session(user: dict = Depends(get_current_user)):
    try:
        user_id = user["user_id"]
        session_id = str(uuid.uuid4())
        success = qa_system.mysql_client.create_user_session(user_id, session_id)

        if success:
            return {"session_id": session_id, "message": "会话创建成功"}
        raise HTTPException(status_code=500, detail="会话创建失败")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session_conversations(
    session_id: str,
    limit: int = 10,
    user: dict = Depends(get_current_user),
):
    try:
        user_id = user["user_id"]

        if not qa_system.mysql_client.verify_session_owner(session_id, user_id):
            raise HTTPException(status_code=403, detail="无权访问此会话")

        conversations = qa_system.mysql_client.fetch_conversations(session_id, limit=limit)
        return SessionDetail(
            session_id=session_id,
            conversations=[
                Conversation(
                    id=conv[5],
                    query=conv[0],
                    answer=conv[1],
                    timestamp=conv[2].strftime("%Y-%m-%d %H:%M:%S"),
                    status=conv[3] if len(conv) > 3 else 0,
                    trace_data=conv[4] if len(conv) > 4 else None,
                )
                for conv in conversations[::-1]
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取会话对话历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话对话历史失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(get_current_user)):
    try:
        user_id = user["user_id"]
        success = qa_system.mysql_client.soft_delete_session(session_id, user_id)
        if success:
            return {"message": f"会话 {session_id} 已删除"}
        raise HTTPException(status_code=404, detail="会话不存在或无权删除")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.patch("/conversations/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: int,
    request: UpdateStatusRequest,
    user: dict = Depends(get_current_admin),
):
    try:
        if request.status not in [0, 1, 2]:
            raise HTTPException(status_code=400, detail="状态值必须为 0、1 或 2")

        success = qa_system.mysql_client.update_conversation_status(conversation_id, request.status)
        if success:
            status_text = {0: "默认", 1: "GoodCase", 2: "BadCase"}
            return {"message": f"对话状态已更新为 {status_text[request.status]}", "status": request.status}
        raise HTTPException(status_code=404, detail="对话不存在")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"更新对话状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新对话状态失败: {str(e)}")


@router.patch("/conversations/{conversation_id}/regenerate")
async def regenerate_conversation(
    conversation_id: int,
    request: RegenerateConversationRequest,
    user: dict = Depends(get_current_user),
):
    try:
        user_id = user["user_id"]

        if not request.answer or not request.answer.strip():
            raise HTTPException(status_code=400, detail="answer 不能为空")

        if not qa_system.mysql_client.verify_conversation_owner(conversation_id, user_id):
            raise HTTPException(status_code=403, detail="无权修改该对话")

        success = qa_system.mysql_client.update_conversation_content(
            conversation_id=conversation_id,
            answer=request.answer.strip(),
            trace_data=request.trace_data,
        )

        if not success:
            raise HTTPException(status_code=404, detail="对话不存在或更新失败")

        return {
            "message": "重新生成内容已覆盖原对话",
            "conversation_id": conversation_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"覆盖更新对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"覆盖更新对话失败: {str(e)}")


@router.post("/conversations/{conversation_id}/regenerate/stream")
async def regenerate_conversation_stream(
    conversation_id: int,
    user: dict = Depends(get_current_user),
):
    try:
        user_id = user["user_id"]

        if not qa_system.mysql_client.verify_conversation_owner(conversation_id, user_id):
            raise HTTPException(status_code=403, detail="无权修改该对话")

        conversation = qa_system.mysql_client.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")

        session_id = conversation["session_id"]
        query = conversation["query"]
        history = qa_system.mysql_client.get_history_before_conversation(conversation_id, limit=5)

        def generate_response():
            try:
                for item in qa_system.query(
                    query=query,
                    source_filter=None,
                    session_id=session_id,
                    history=history,
                    replace_conversation_id=conversation_id,
                ):
                    if len(item) == 4:
                        token_type, token, is_complete, updated_conversation_id = item
                    elif len(item) == 3:
                        token_type, token, is_complete = item
                        updated_conversation_id = conversation_id
                    else:
                        token_type, token = "answer", item[0]
                        is_complete = item[1] if len(item) > 1 else False
                        updated_conversation_id = conversation_id

                    message = {
                        "token_type": token_type,
                        "token": token,
                        "is_complete": is_complete,
                        "session_id": session_id,
                    }

                    if is_complete:
                        message["conversation_id"] = updated_conversation_id or conversation_id

                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
            except Exception as e:
                error_msg = f"重新生成时发生错误: {str(e)}"
                qa_system.logger.error(error_msg)
                message = {
                    "error": error_msg,
                    "is_complete": True,
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                }
                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

        return StreamingResponse(generate_response(), media_type="text/event-stream")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"重新生成对话流失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新生成对话流失败: {str(e)}")
