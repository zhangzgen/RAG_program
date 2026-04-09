from fastapi import APIRouter, Depends, HTTPException

from .shared import FAQCreate, get_current_admin, qa_system


router = APIRouter()


@router.get("/faq")
async def get_faqs(search: str = None, user: dict = Depends(get_current_admin)):
    try:
        faqs = qa_system.mysql_client.get_all_faqs(search_keyword=search)
        return {"faqs": faqs}
    except Exception as e:
        qa_system.logger.error(f"获取FAQ列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取FAQ列表失败: {str(e)}")


@router.get("/faq/{faq_id}")
async def get_faq(faq_id: int, user: dict = Depends(get_current_admin)):
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


@router.post("/faq")
async def create_faq(faq: FAQCreate, user: dict = Depends(get_current_admin)):
    try:
        faq_id = qa_system.mysql_client.add_faq(
            faq.subject_name,
            faq.question,
            faq.answer,
        )
        return {"success": True, "id": faq_id, "message": "FAQ创建成功"}
    except Exception as e:
        qa_system.logger.error(f"创建FAQ失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建FAQ失败: {str(e)}")


@router.put("/faq/{faq_id}")
async def update_faq(faq_id: int, faq: FAQCreate, user: dict = Depends(get_current_admin)):
    try:
        success = qa_system.mysql_client.update_faq(
            faq_id,
            faq.subject_name,
            faq.question,
            faq.answer,
        )
        if not success:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        return {"success": True, "message": "FAQ更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"更新FAQ失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新FAQ失败: {str(e)}")


@router.delete("/faq/{faq_id}")
async def delete_faq(faq_id: int, user: dict = Depends(get_current_admin)):
    try:
        success = qa_system.mysql_client.delete_faq(faq_id)
        if not success:
            raise HTTPException(status_code=404, detail="FAQ不存在")
        return {"success": True, "message": "FAQ删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除FAQ失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除FAQ失败: {str(e)}")
