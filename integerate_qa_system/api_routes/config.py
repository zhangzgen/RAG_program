import os

from fastapi import APIRouter, Depends, HTTPException

from base import Config

from .shared import ConfigUpdateRequest, auth_service, compare_configs, email_service, get_current_admin, parse_config_content, qa_system


router = APIRouter()


def _apply_runtime_reload(changed_items):
    Config.hot_reload()
    changed_sections = {section for section, _ in changed_items}

    if "llm" in changed_sections:
        try:
            qa_system.config = Config()
            qa_system.reload_llm_client()
        except Exception as exc:
            qa_system.logger.warning(f"Failed to hot reload llm client: {exc}")

    if "jwt" in changed_sections:
        auth_service.reload_config()

    if "email" in changed_sections:
        email_service.reload_config()


@router.get("/config")
async def get_config(user: dict = Depends(get_current_admin)):
    try:
        Config._config_cache = None
        config = Config()
        if hasattr(config, "_force_reload"):
            delattr(config, "_force_reload")

        config_data = {
            "mysql": {
                "host": config.MYSQL_HOST,
                "user": config.MYSQL_USER,
                "password": "******",
                "database": config.MYSQL_DATABASE,
            },
            "redis": {
                "host": config.REDIS_HOST,
                "port": config.REDIS_PORT,
                "password": "******",
                "db": config.REDIS_DB,
            },
            "milvus": {
                "host": config.MILVUS_HOST,
                "port": config.MILVUS_PORT,
                "database_name": config.MILVUS_DATABASE_NAME,
                "collection_name": config.MILVUS_COLLECTION_NAME,
            },
            "llm": {
                "model": config.LLM_MODEL,
                "dashscope_api_key": "******",
                "dashscope_base_url": config.DASHSCOPE_BASE_URL,
            },
            "assessment": {
                "llm_model": config.ASSESSMENT_LLM_MODEL,
                "embedding_model": config.ASSESSMENT_EMBEDDING_MODEL,
                "api_key": "******",
                "base_url": config.ASSESSMENT_BASE_URL,
            },
            "retrieval": {
                "parent_chunk_size": config.PARENT_CHUNK_SIZE,
                "child_chunk_size": config.CHILD_CHUNK_SIZE,
                "chunk_overlap": config.CHUNK_OVERLAP,
                "retrieval_k": config.RETRIEVAL_K,
                "candidate_m": config.CANDIDATE_M,
            },
            "logger": {
                "log_file": config.LOG_FILE,
            },
            "app": {
                "valid_sources": config.VALID_SOURCES,
                "customer_service_phone": config.CUSTOMER_SERVICE_PHONE,
            },
            "email": {
                "qq_email": config.QQ_EMAIL,
                "qq_auth_code": "******",
                "smtp_server": config.SMTP_SERVER,
                "smtp_port": config.SMTP_PORT,
            },
            "jwt": {
                "secret_key": "******",
                "algorithm": config.JWT_ALGORITHM,
                "expire_days": config.JWT_EXPIRE_DAYS,
            },
        }

        return {
            "success": True,
            "config": config_data,
        }
    except Exception as e:
        qa_system.logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.get("/config/raw")
async def get_raw_config(user: dict = Depends(get_current_admin)):
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "success": True,
            "content": content,
        }
    except Exception as e:
        qa_system.logger.error(f"获取原始配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取原始配置失败: {str(e)}")


@router.post("/config")
async def update_config(request: ConfigUpdateRequest, user: dict = Depends(get_current_admin)):
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")

        with open(config_path, "r", encoding="utf-8") as f:
            old_content = f.read()

        old_config = parse_config_content(old_content)
        new_config = parse_config_content(request.config_content)
        changed_items = compare_configs(old_config, new_config)

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(request.config_content)

        import datetime

        version = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        qa_system.mysql_client.save_config_version(
            version=version,
            config_content=request.config_content,
            change_description=request.change_description,
            changed_by=request.changed_by,
        )

        _apply_runtime_reload(changed_items)

        reloaded_items = []
        not_reloaded_items = []

        for section, key in changed_items:
            item_name = f"{section}.{key}"
            if section in ["llm", "assessment", "retrieval", "app", "email", "jwt"]:
                reloaded_items.append(item_name)
            else:
                not_reloaded_items.append(item_name)

        reload_messages = []
        if reloaded_items:
            reload_messages.append(f"以下 {len(reloaded_items)} 项配置已热加载成功")
        if not_reloaded_items:
            reload_messages.append(f"以下 {len(not_reloaded_items)} 项配置需要重启后端服务才生效")

        return {
            "success": True,
            "message": "配置更新成功",
            "version": version,
            "hot_reload": {
                "reloaded": reloaded_items,
                "not_reloaded": not_reloaded_items,
                "reloaded_count": len(reloaded_items),
                "not_reloaded_count": len(not_reloaded_items),
                "messages": reload_messages,
            },
        }
    except Exception as e:
        qa_system.logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/config/versions")
async def get_config_versions(limit: int = 20, user: dict = Depends(get_current_admin)):
    try:
        versions = qa_system.mysql_client.get_config_versions(limit)
        return {
            "success": True,
            "versions": versions,
            "total": len(versions),
        }
    except Exception as e:
        qa_system.logger.error(f"获取配置版本列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置版本列表失败: {str(e)}")


@router.get("/config/versions/{version_id}")
async def get_config_version_detail(version_id: int, user: dict = Depends(get_current_admin)):
    try:
        version = qa_system.mysql_client.get_config_by_id(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")
        return {
            "success": True,
            "version": version,
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"获取配置版本详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置版本详情失败: {str(e)}")


@router.post("/config/rollback/{version_id}")
async def rollback_config(version_id: int, user: dict = Depends(get_current_admin)):
    try:
        version = qa_system.mysql_client.get_config_by_id(version_id)
        if not version:
            raise HTTPException(status_code=404, detail="版本不存在")

        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")

        with open(config_path, "r", encoding="utf-8") as f:
            old_content = f.read()

        old_config = parse_config_content(old_content)
        new_config = parse_config_content(version["config_content"])
        changed_items = compare_configs(old_config, new_config)

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(version["config_content"])

        rollback_result = qa_system.mysql_client.rollback_config(version_id)
        _apply_runtime_reload(changed_items)

        reloaded_items = []
        not_reloaded_items = []

        for section, key in changed_items:
            item_name = f"{section}.{key}"
            if section in ["llm", "assessment", "retrieval", "app", "email", "jwt"]:
                reloaded_items.append(item_name)
            else:
                not_reloaded_items.append(item_name)

        reload_messages = []
        if reloaded_items:
            reload_messages.append(f"以下 {len(reloaded_items)} 项配置已热加载成功")
        if not_reloaded_items:
            reload_messages.append(f"以下 {len(not_reloaded_items)} 项配置需要重启后端服务才生效")

        return {
            "success": True,
            "message": f'已回退到版本 {rollback_result["original_version"]}',
            "rollback_version": rollback_result["version"],
            "hot_reload": {
                "reloaded": reloaded_items,
                "not_reloaded": not_reloaded_items,
                "reloaded_count": len(reloaded_items),
                "not_reloaded_count": len(not_reloaded_items),
                "messages": reload_messages,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        qa_system.logger.error(f"配置回退失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置回退失败: {str(e)}")
