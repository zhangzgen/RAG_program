import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from .shared import CaseDetail, CaseListResponse, get_current_user, qa_system


router = APIRouter()


@router.get("/cases")
async def get_cases(
    status: int = 1,
    page: int = 1,
    page_size: int = 20,
    user: dict = Depends(get_current_user),
):
    try:
        if status not in [1, 2]:
            raise HTTPException(status_code=400, detail="状态值必须为1(GoodCase)或2(BadCase)")

        offset = (page - 1) * page_size
        cases = qa_system.mysql_client.get_conversations_by_status(status, limit=page_size, offset=offset)
        total = qa_system.mysql_client.get_conversations_count_by_status(status)

        return CaseListResponse(
            cases=[CaseDetail(**case) for case in cases],
            total=total,
            page=page,
            page_size=page_size,
        )
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取Case列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取Case列表失败: {str(e)}")


@router.get("/cases/download")
async def download_cases(status: int = 1, user: dict = Depends(get_current_user)):
    if status not in [1, 2]:
        raise HTTPException(status_code=400, detail="状态值必须为1(GoodCase)或2(BadCase)")

    try:
        total = qa_system.mysql_client.get_conversations_count_by_status(status)
        cases = qa_system.mysql_client.get_conversations_by_status(status, limit=total if total > 0 else 1)
        filename = "good_cases.json" if status == 1 else "bad_cases.json"
        content = json.dumps(cases, ensure_ascii=False, indent=2, default=str)
        return Response(
            content=content.encode("utf-8"),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        qa_system.logger.error(f"下载Case数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载Case数据失败: {str(e)}")


@router.get("/cases/{conversation_id}")
async def get_case_detail(conversation_id: int, user: dict = Depends(get_current_user)):
    try:
        case = qa_system.mysql_client.get_conversation_by_id(conversation_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case不存在")

        return CaseDetail(**case)
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取Case详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取Case详情失败: {str(e)}")
