import base64
import json
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from .shared import (
    ChunkRequest,
    CreateCategoryRequest,
    DATA_BASE_PATH,
    UploadFileResponse,
    VectorIdRequest,
    VectorSearchRequest,
    get_current_user,
    qa_system,
)


router = APIRouter()


TEXT_EXTENSIONS = [
    ".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".xml",
    ".html", ".css", ".sql", ".java", ".c", ".cpp", ".h", ".hpp", ".sh",
    ".bash", ".yaml", ".yml", ".ini", ".cfg", ".log", ".toml", ".vue",
    ".svelte", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".r", ".ps1", ".scss", ".less",
]
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"]


@router.get("/knowledge/files")
async def get_knowledge_files(category_id: int = None, user: dict = Depends(get_current_user)):
    try:
        if category_id is None:
            categories = qa_system.mysql_client.get_all_categories()
            items = []
            for cat in categories:
                items.append(
                    {
                        "id": f"cat_{cat['id']}",
                        "name": cat["category"],
                        "path": cat["category"],
                        "is_dir": True,
                        "file_type": "",
                        "is_chunk": False,
                        "category_id": cat["id"],
                    }
                )

            return {
                "files": items,
                "current_path": "",
                "parent_path": None,
                "category_id": None,
                "category_name": None,
            }

        category = qa_system.mysql_client.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

        db_files = qa_system.mysql_client.get_files_by_category(category_id)

        items = []
        for f in db_files:
            file_name = os.path.basename(f["file_path"])
            file_ext = os.path.splitext(file_name)[1].lower() if not f["is_dir"] else ""
            items.append(
                {
                    "id": f["id"],
                    "name": file_name,
                    "path": f["file_path"],
                    "is_dir": f["is_dir"],
                    "file_type": file_ext,
                    "is_chunk": f["is_chunk"],
                    "category_id": category_id,
                }
            )

        folders = [item for item in items if item["is_dir"]]
        files = [item for item in items if not item["is_dir"]]
        sorted_items = folders + files

        return {
            "files": sorted_items,
            "current_path": category["category"],
            "parent_path": None,
            "category_id": category_id,
            "category_name": category["category"],
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.post("/knowledge/categories")
async def create_category(request: CreateCategoryRequest, user: dict = Depends(get_current_user)):
    try:
        category_name = request.category_name.strip()
        if not category_name:
            raise HTTPException(status_code=400, detail="分类名称不能为空")

        result = qa_system.mysql_client.create_category(category_name, DATA_BASE_PATH)
        return {
            "message": "分类创建成功",
            "category_id": result["category_id"],
            "folder_path": result["folder_path"],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        qa_system.logger.error(f"创建分类失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建分类失败: {str(e)}")


@router.get("/knowledge/categories")
async def get_categories(user: dict = Depends(get_current_user)):
    try:
        categories = qa_system.mysql_client.get_all_categories()
        return {"categories": categories}
    except Exception as e:
        qa_system.logger.error(f"获取分类列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@router.delete("/knowledge/categories/{category_id}")
async def delete_category(category_id: int, user: dict = Depends(get_current_user)):
    try:
        success = qa_system.mysql_client.delete_category(category_id)
        if success:
            return {"message": "分类删除成功"}
        raise HTTPException(status_code=404, detail="分类不存在")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除分类失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除分类失败: {str(e)}")


@router.get("/knowledge/categories/{category_id}/files")
async def get_category_files(category_id: int, user: dict = Depends(get_current_user)):
    try:
        files = qa_system.mysql_client.get_files_by_category(category_id)
        result_files = []
        for f in files:
            file_name = os.path.basename(f["file_path"])
            file_ext = os.path.splitext(file_name)[1].lower() if not f["is_dir"] else ""
            result_files.append(
                {
                    "id": f["id"],
                    "name": file_name,
                    "path": f["file_path"],
                    "is_dir": f["is_dir"],
                    "is_chunk": f["is_chunk"],
                    "category_id": f["category_id"],
                    "file_type": file_ext,
                }
            )

        return {"files": result_files}
    except Exception as e:
        qa_system.logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.get("/knowledge/files/{file_id}")
async def get_file_info(file_id: int, user: dict = Depends(get_current_user)):
    try:
        file_info = qa_system.mysql_client.get_file_by_id(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")

        file_name = os.path.basename(file_info["file_path"])
        file_ext = os.path.splitext(file_name)[1].lower() if not file_info["is_dir"] else ""

        return {
            "id": file_info["id"],
            "name": file_name,
            "path": file_info["file_path"],
            "is_dir": file_info["is_dir"],
            "is_chunk": file_info["is_chunk"],
            "category_id": file_info["category_id"],
            "file_type": file_ext,
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取文件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@router.get("/knowledge/files/{file_id}/preview")
async def preview_file(file_id: int, user: dict = Depends(get_current_user)):
    try:
        file_info = qa_system.mysql_client.get_file_by_id(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")

        if file_info["is_dir"]:
            raise HTTPException(status_code=400, detail="无法预览文件夹")

        file_path = file_info["file_path"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在于文件系统")

        file_ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)

        if file_ext in [".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".xml", ".html", ".css", ".sql", ".java", ".c", ".cpp", ".h", ".sh", ".yaml", ".yml", ".ini", ".cfg", ".log"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return {
                "file_name": file_name,
                "file_type": "text",
                "content": content,
            }
        if file_ext == ".pdf":
            return {
                "file_name": file_name,
                "file_type": "pdf",
                "content": None,
                "message": "PDF文件需要专用查看器",
            }
        if file_ext in [".doc", ".docx"]:
            return {
                "file_name": file_name,
                "file_type": "word",
                "content": None,
                "message": "Word文件需要专用查看器",
            }
        if file_ext in [".xls", ".xlsx"]:
            return {
                "file_name": file_name,
                "file_type": "excel",
                "content": None,
                "message": "Excel文件需要专用查看器",
            }
        if file_ext in [".ppt", ".pptx"]:
            return {
                "file_name": file_name,
                "file_type": "ppt",
                "content": None,
                "message": "PPT文件需要专用查看器",
            }
        if file_ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            with open(file_path, "rb") as f:
                file_content = f.read()
            base64_content = base64.b64encode(file_content).decode("utf-8")
            return {
                "file_name": file_name,
                "file_type": "image",
                "content": base64_content,
                "mime_type": f"image/{file_ext[1:]}",
            }
        return {
            "file_name": file_name,
            "file_type": "unknown",
            "content": None,
            "message": "不支持的文件类型",
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"预览文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")


@router.get("/knowledge/preview")
async def preview_file_by_path(path: str, user: dict = Depends(get_current_user)):
    try:
        file_path = os.path.join(DATA_BASE_PATH, path)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        if os.path.isdir(file_path):
            raise HTTPException(status_code=400, detail="无法预览文件夹")

        if not file_path.startswith(DATA_BASE_PATH):
            raise HTTPException(status_code=403, detail="无权访问此文件")

        file_ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        if file_ext in TEXT_EXTENSIONS:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if file_ext == ".md":
                file_type = "markdown"
            elif file_ext in [
                ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
                ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala", ".r", ".sql",
                ".sh", ".bash", ".ps1", ".vue", ".svelte", ".css", ".scss", ".less",
                ".html", ".json", ".xml", ".yaml", ".yml", ".toml",
            ]:
                file_type = "code"
            else:
                file_type = "text"

            return {
                "file_name": file_name,
                "file_type": file_type,
                "file_ext": file_ext,
                "content": content,
                "file_size": file_size,
            }

        if file_ext == ".pdf":
            with open(file_path, "rb") as f:
                file_content = f.read()
            base64_content = base64.b64encode(file_content).decode("utf-8")
            return {
                "file_name": file_name,
                "file_type": "pdf",
                "file_ext": file_ext,
                "content": base64_content,
                "file_size": file_size,
            }

        if file_ext in [".doc", ".docx"]:
            if file_ext == ".doc":
                return {
                    "file_name": file_name,
                    "file_type": "word",
                    "file_ext": file_ext,
                    "content": None,
                    "file_size": file_size,
                    "message": "旧版.doc格式不支持预览，请转换为.docx格式",
                }
            try:
                import mammoth

                with open(file_path, "rb") as f:
                    result = mammoth.convert_to_html(f)
                    html_content = result.value
                    messages = result.messages
                return {
                    "file_name": file_name,
                    "file_type": "word",
                    "file_ext": file_ext,
                    "content": html_content,
                    "file_size": file_size,
                    "warnings": [str(m) for m in messages] if messages else [],
                }
            except ImportError:
                return {
                    "file_name": file_name,
                    "file_type": "word",
                    "file_ext": file_ext,
                    "content": None,
                    "file_size": file_size,
                    "message": "服务器未安装mammoth库，无法预览Word文件",
                }
            except Exception as e:
                return {
                    "file_name": file_name,
                    "file_type": "word",
                    "file_ext": file_ext,
                    "content": None,
                    "file_size": file_size,
                    "message": f"Word文件解析失败: {str(e)}",
                }

        if file_ext in [".xls", ".xlsx"]:
            return {
                "file_name": file_name,
                "file_type": "excel",
                "file_ext": file_ext,
                "content": None,
                "file_size": file_size,
                "message": "Excel文件需要专用查看器",
            }

        if file_ext in [".ppt", ".pptx"]:
            return {
                "file_name": file_name,
                "file_type": "ppt",
                "file_ext": file_ext,
                "content": None,
                "file_size": file_size,
                "message": "PPT文件需要专用查看器",
            }

        if file_ext in IMAGE_EXTENSIONS:
            with open(file_path, "rb") as f:
                file_content = f.read()
            base64_content = base64.b64encode(file_content).decode("utf-8")
            mime_type = "image/svg+xml" if file_ext == ".svg" else f"image/{file_ext[1:]}"
            return {
                "file_name": file_name,
                "file_type": "image",
                "file_ext": file_ext,
                "content": base64_content,
                "mime_type": mime_type,
                "file_size": file_size,
            }

        return {
            "file_name": file_name,
            "file_type": "unknown",
            "file_ext": file_ext,
            "content": None,
            "file_size": file_size,
            "message": "不支持的文件类型",
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"预览文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")


@router.post("/knowledge/search")
async def vector_search(request: VectorSearchRequest, user: dict = Depends(get_current_user)):
    try:
        if not request.query or not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")

        query = request.query.strip()
        top_k = min(request.top_k, 20)

        results = qa_system.vector_store.hybrid_search_with_rerank(
            query=query,
            k=top_k,
            source_filter=request.source_filter,
        )

        search_results = []
        for doc in results:
            search_results.append(
                {
                    "id": doc.metadata.get("id", ""),
                    "content": doc.page_content,
                    "parent_content": doc.metadata.get("parent_content", ""),
                    "source": doc.metadata.get("source", "unknown"),
                    "timestamp": doc.metadata.get("timestamp", ""),
                    "file_path": doc.metadata.get("file_path", ""),
                    "parent_id": doc.metadata.get("parent_id", ""),
                    "score": doc.metadata.get("rerank_score", None),
                }
            )

        return {
            "query": query,
            "source_filter": request.source_filter,
            "total": len(search_results),
            "results": search_results,
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"向量检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"向量检索失败: {str(e)}")


@router.post("/knowledge/vector/detail")
async def get_vector_detail(request: VectorIdRequest, user: dict = Depends(get_current_user)):
    try:
        if not request.vector_id or not request.vector_id.strip():
            raise HTTPException(status_code=400, detail="向量ID不能为空")

        vector_info = qa_system.vector_store.get_vector_by_id(request.vector_id.strip())
        if not vector_info:
            raise HTTPException(status_code=404, detail="向量不存在")

        return {
            "success": True,
            "data": vector_info,
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"查询向量详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询向量详情失败: {str(e)}")


@router.get("/knowledge/sources")
async def get_knowledge_sources(user: dict = Depends(get_current_user)):
    try:
        sources = qa_system.mysql_client.get_all_categories()
        source_list = [{"id": cat["id"], "name": cat["category"]} for cat in sources]
        return {"sources": source_list}
    except Exception as e:
        qa_system.logger.error(f"获取知识库来源失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取知识库来源失败: {str(e)}")


@router.post("/knowledge/categories/{category_id}/upload", response_model=UploadFileResponse)
async def upload_file(
    category_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    try:
        category = qa_system.mysql_client.get_category_by_id(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

        category_folder = os.path.join(DATA_BASE_PATH, category["category"])
        os.makedirs(category_folder, exist_ok=True)

        file_path = os.path.join(category_folder, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_id = qa_system.mysql_client.add_file(
            file_path=file_path,
            is_dir=False,
            category_id=category_id,
            is_chunk=False,
        )

        return UploadFileResponse(
            file_id=file_id,
            file_name=file.filename,
            file_path=file_path,
            message="文件上传成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")


@router.delete("/knowledge/files/{file_id}")
async def delete_file(file_id: int, user: dict = Depends(get_current_user)):
    try:
        success = qa_system.mysql_client.delete_file(file_id)
        if success:
            return {"message": "文件删除成功"}
        raise HTTPException(status_code=404, detail="文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.post("/knowledge/chunk")
async def chunk_files(request: ChunkRequest, user: dict = Depends(get_current_user)):
    from rag_qa.core.document_process import process_single_file

    def collect_files_from_folder(folder_id, collected_files):
        folder_files = qa_system.mysql_client.get_files_by_parent_folder(folder_id)
        for f in folder_files:
            if f["is_dir"]:
                collect_files_from_folder(f["id"], collected_files)
            elif not f["is_chunk"]:
                collected_files.append(f)

    def generate():
        files_to_chunk = []

        if request.file_ids:
            for file_id in request.file_ids:
                file_info = qa_system.mysql_client.get_file_by_id(file_id)
                if file_info:
                    if file_info["is_dir"]:
                        collect_files_from_folder(file_id, files_to_chunk)
                    elif not file_info["is_chunk"]:
                        files_to_chunk.append(file_info)
        elif request.category_id:
            all_files = qa_system.mysql_client.get_files_by_category(request.category_id)
            for f in all_files:
                if not f["is_chunk"] and not f["is_dir"]:
                    files_to_chunk.append(f)

        if not files_to_chunk:
            yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': '没有需要切片的文件', 'total': 0, 'results': []}, ensure_ascii=False)}\n\n"
            return

        total = len(files_to_chunk)
        results = []
        completed = 0

        yield f"data: {json.dumps({'type': 'start', 'total': total, 'completed': 0}, ensure_ascii=False)}\n\n"

        for file_info in files_to_chunk:
            file_path = file_info["file_path"]
            file_id = file_info["id"]
            file_name = os.path.basename(file_path)

            try:
                category = qa_system.mysql_client.get_category_by_id(file_info["category_id"])
                source = category["category"] if category else "unknown"

                child_chunks = process_single_file(file_path, source=source)

                if child_chunks is None or len(child_chunks) == 0:
                    completed += 1
                    results.append(
                        {
                            "file_id": file_id,
                            "file_name": file_name,
                            "status": "failed",
                            "error": "文件加载或切分失败，未生成任何切片",
                        }
                    )
                    yield f"data: {json.dumps({'type': 'result', 'file_id': file_id, 'file_name': file_name, 'status': 'failed', 'error': '文件加载或切分失败', 'completed': completed, 'total': total}, ensure_ascii=False)}\n\n"
                    continue

                for chunk in child_chunks:
                    chunk.metadata["file_id"] = file_id

                qa_system.vector_store.add_documents(child_chunks)
                qa_system.mysql_client.update_file_chunk_status(file_id, True)

                completed += 1
                results.append(
                    {
                        "file_id": file_id,
                        "file_name": file_name,
                        "status": "success",
                        "chunks": len(child_chunks),
                    }
                )
                yield f"data: {json.dumps({'type': 'result', 'file_id': file_id, 'file_name': file_name, 'status': 'success', 'chunks': len(child_chunks), 'completed': completed, 'total': total}, ensure_ascii=False)}\n\n"
            except Exception as e:
                qa_system.logger.error(f"切片文件失败 {file_name}: {e}")
                completed += 1
                results.append(
                    {
                        "file_id": file_id,
                        "file_name": file_name,
                        "status": "failed",
                        "error": str(e),
                    }
                )
                yield f"data: {json.dumps({'type': 'result', 'file_id': file_id, 'file_name': file_name, 'status': 'failed', 'error': str(e), 'completed': completed, 'total': total}, ensure_ascii=False)}\n\n"

        success_count = sum(1 for r in results if r["status"] == "success")
        yield f"data: {json.dumps({'type': 'complete', 'success': True, 'message': f'切片完成，成功{success_count}/{total}', 'total': total, 'results': results}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/knowledge/files/unchunked")
async def get_unchunked_files(category_id: Optional[int] = None, user: dict = Depends(get_current_user)):
    try:
        if category_id:
            all_files = qa_system.mysql_client.get_files_by_category(category_id)
        else:
            all_files = qa_system.mysql_client.get_all_files()

        unchunked_files = [f for f in all_files if not f["is_chunk"] and not f["is_dir"]]
        return {
            "total": len(unchunked_files),
            "files": unchunked_files,
        }
    except Exception as e:
        qa_system.logger.error(f"获取未切片文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取未切片文件失败: {str(e)}")


@router.get("/knowledge/files/{file_id}/chunks")
async def get_file_chunks(file_id: int, user: dict = Depends(get_current_user)):
    try:
        file_info = qa_system.mysql_client.get_file_by_id(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="文件不存在")

        if not file_info["is_chunk"]:
            return {
                "file_id": file_id,
                "file_path": file_info["file_path"],
                "is_chunk": False,
                "total": 0,
                "chunks": [],
            }

        file_path = file_info["file_path"]
        chunks = qa_system.vector_store.get_chunks_by_file_path(file_path)

        return {
            "file_id": file_id,
            "file_path": file_path,
            "is_chunk": True,
            "total": len(chunks),
            "chunks": chunks,
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取文件切片失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件切片失败: {str(e)}")


@router.get("/knowledge/supported-types")
async def get_supported_file_types():
    from rag_qa.core.document_process import SUPPORTED_EXTENSIONS

    return {
        "supported_extensions": SUPPORTED_EXTENSIONS,
    }
