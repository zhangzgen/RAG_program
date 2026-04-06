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
    title="闆嗘垚闂瓟绯荤粺 API",
    description="鍩轰簬 RAG + MySQL + Redis 鐨勯棶绛旂郴缁熺殑 FastAPI 鎺ュ彛",
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
        qa_system.logger.info("鐭ヨ瘑搴撹〃鍒濆鍖栧畬鎴�")
        qa_system.mysql_client.create_config_version_table()
        qa_system.logger.info("閰嶇疆鐗堟湰琛ㄥ垵濮嬪寲瀹屾垚")
        qa_system.mysql_client.create_assessment_tables()
        qa_system.logger.info("璇勪及鐩稿叧琛ㄥ垵濮嬪鍖栧畬鎴�")
    except Exception as e:
        qa_system.logger.error(f"鐭ヨ瘑搴撹〃鍒濆鍖栧け璐� {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
