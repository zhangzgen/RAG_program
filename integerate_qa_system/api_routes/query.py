import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .shared import get_current_user, qa_system


router = APIRouter()


@router.post("/query")
async def handle_query(request: Request, user: dict = Depends(get_current_user)):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的JSON数据")

    query = body.get("query", "").strip()
    source_filter = body.get("source_filter", None)
    session_id = body.get("session_id", None)

    if not query:
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    if not session_id:
        session_id = str(uuid.uuid4())

    valid_sources = qa_system.config.VALID_SOURCES
    if source_filter and source_filter not in valid_sources:
        raise HTTPException(status_code=400, detail=f"无效的学科类别。支持: {valid_sources}")

    def generate_response():
        try:
            for item in qa_system.query(
                query=query,
                source_filter=source_filter,
                session_id=session_id,
            ):
                if len(item) == 4:
                    token_type, token, is_complete, conversation_id = item
                elif len(item) == 3:
                    token_type, token, is_complete = item
                    conversation_id = None
                else:
                    token_type, token = "answer", item[0]
                    is_complete = item[1] if len(item) > 1 else False
                    conversation_id = None

                message = {
                    "token_type": token_type,
                    "token": token,
                    "is_complete": is_complete,
                    "session_id": session_id,
                }

                if is_complete and conversation_id:
                    message["conversation_id"] = conversation_id

                yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_msg = f"处理查询时发生错误: {str(e)}"
            qa_system.logger.error(error_msg)
            message = {
                "error": error_msg,
                "is_complete": True,
            }
            yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate_response(), media_type="text/event-stream")
