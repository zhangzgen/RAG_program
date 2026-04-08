from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_routes import register_routers
from api_routes.shared import (
    ASSESSMENT_UPLOAD_DIR,
    DATA_BASE_PATH,
    AssessmentRunRequest,
    CaseDetail,
    CaseListResponse,
    ChunkRequest,
    ConfigUpdateRequest,
    Conversation,
    CreateCategoryRequest,
    FAQCreate,
    LoginRequest,
    LoginResponse,
    RegenerateConversationRequest,
    SendCodeRequest,
    SessionDetail,
    SessionInfo,
    UpdateStatusRequest,
    UploadFileResponse,
    VectorIdRequest,
    VectorSearchRequest,
    auth_service,
    compare_configs,
    email_service,
    get_current_user,
    parse_config_content,
    qa_system,
    redis_client,
)

app = FastAPI(
    title="集成问答系统 API",
    description="基于 RAG + MySQL + Redis 的问答系统的 FastAPI 接口",
)

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

register_routers(app)


@app.on_event("startup")
async def startup_event():
    try:
        qa_system.mysql_client.create_knowledge_tables()
        qa_system.logger.info("知识库表初始化完成")
        qa_system.mysql_client.create_config_version_table()
        qa_system.logger.info("配置版本表初始化完成")
        qa_system.mysql_client.create_assessment_tables()
        qa_system.logger.info("评估相关表初始化完成")
    except Exception as e:
        qa_system.logger.error(f"知识库表初始化失败: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
