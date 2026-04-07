import os
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from .shared import ASSESSMENT_UPLOAD_DIR, AssessmentRunRequest, get_current_user, qa_system


router = APIRouter()


@router.post("/assessment/upload")
async def upload_assessment_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="仅支持.json 格式的评估数据文件")

    file_id = str(uuid.uuid4())
    save_path = os.path.join(ASSESSMENT_UPLOAD_DIR, f"{file_id}_{file.filename}")
    content = await file.read()
    content_text = content.decode("utf-8")

    with open(save_path, "wb") as f:
        f.write(content)

    qa_system.mysql_client.save_assessment_file(
        file_id=file_id,
        file_name=file.filename,
        file_path=save_path,
        file_content=content_text,
        uploaded_by=user.get("email"),
    )

    file_record = qa_system.mysql_client.get_assessment_file_by_id(file_id)
    return {
        "file_id": file_record["file_id"],
        "file_name": file_record["file_name"],
        "uploaded_at": file_record["uploaded_at"],
    }


@router.get("/assessment/files")
async def list_assessment_files(user: dict = Depends(get_current_user)):
    files = qa_system.mysql_client.get_assessment_files()
    return [
        {
            "file_id": item["file_id"],
            "file_name": item["file_name"],
            "uploaded_at": item["uploaded_at"],
            "uploaded_by": item.get("uploaded_by"),
        }
        for item in files
    ]


@router.get("/assessment/files/{file_id}")
async def get_assessment_file(file_id: str, user: dict = Depends(get_current_user)):
    file_info = qa_system.mysql_client.get_assessment_file_by_id(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="评估文件不存在")

    parsed_content = None
    try:
        parsed_content = json.loads(file_info["file_content"]) if file_info.get("file_content") else None
    except Exception:
        parsed_content = None

    return {
        "file_id": file_info["file_id"],
        "file_name": file_info["file_name"],
        "uploaded_at": file_info["uploaded_at"],
        "uploaded_by": file_info.get("uploaded_by"),
        "content": parsed_content,
        "raw_content": file_info.get("file_content"),
    }


@router.get("/assessment/results")
async def list_assessment_results(limit: int = 50, user: dict = Depends(get_current_user)):
    return qa_system.mysql_client.get_assessment_results(limit)


@router.get("/assessment/results/{result_id}")
async def get_assessment_result(result_id: str, user: dict = Depends(get_current_user)):
    result = qa_system.mysql_client.get_assessment_result_by_id(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="评估结果不存在")
    return result


@router.post("/assessment/run")
async def run_assessment(request: AssessmentRunRequest, user: dict = Depends(get_current_user)):
    file_info = qa_system.mysql_client.get_assessment_file_by_id(request.file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="评估文件不存在，请先上传")

    file_path = file_info["file_path"]
    result_id = str(uuid.uuid4())

    def generate():
        try:
            import json as _json
            import math as _math

            from datasets import Dataset
            from langchain_openai import ChatOpenAI, OpenAIEmbeddings
            from ragas import evaluate
            from ragas.embeddings import LangchainEmbeddingsWrapper
            from ragas.llms import LangchainLLMWrapper
            from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
            from base import Config

            with open(file_path, "r", encoding="utf-8") as f:
                data = _json.load(f)

            total = len(data)
            qa_system.mysql_client.create_assessment_result(
                result_id=result_id,
                file_id=file_info["file_id"],
                file_name=file_info["file_name"],
                total_questions=total,
                created_by=user.get("email"),
            )

            yield f"data: {_json.dumps({'type': 'start', 'result_id': result_id, 'total_questions': total, 'completed_questions': 0}, ensure_ascii=False)}\n\n"

            current_config = Config()
            if current_config.ASSESSMENT_EMBEDDING_PROVIDER == "ollama":
                from langchain_ollama import ChatOllama, OllamaEmbeddings

                llm = LangchainLLMWrapper(
                    ChatOllama(
                        model=current_config.ASSESSMENT_LLM_MODEL,
                        base_url=current_config.ASSESSMENT_BASE_URL,
                    )
                )
                embeddings = LangchainEmbeddingsWrapper(
                    OllamaEmbeddings(
                        model=current_config.ASSESSMENT_EMBEDDING_MODEL,
                        base_url=current_config.ASSESSMENT_EMBEDDING_BASE_URL,
                    )
                )
            else:
                if not current_config.ASSESSMENT_API_KEY:
                    raise ValueError("assessment.api_key 未配置")
                llm = LangchainLLMWrapper(
                    ChatOpenAI(
                        model=current_config.ASSESSMENT_LLM_MODEL,
                        api_key=current_config.ASSESSMENT_API_KEY,
                        base_url=current_config.ASSESSMENT_BASE_URL,
                        temperature=0,
                    )
                )
                embeddings = LangchainEmbeddingsWrapper(
                    OpenAIEmbeddings(
                        model=current_config.ASSESSMENT_EMBEDDING_MODEL,
                        api_key=current_config.ASSESSMENT_API_KEY,
                        base_url=current_config.ASSESSMENT_BASE_URL,
                    )
                )

            partial_results = []

            def safe_float(v):
                if v is None:
                    return None
                try:
                    f = float(v)
                    return None if _math.isnan(f) or _math.isinf(f) else f
                except (TypeError, ValueError):
                    return None

            for index, item in enumerate(data, start=1):
                eval_data = {
                    "question": [item["question"]],
                    "answer": [item["answer"]],
                    "contexts": [item["context"]],
                    "ground_truth": [item["ground_truth"]],
                }
                dataset = Dataset.from_dict(eval_data)

                result = evaluate(
                    dataset=dataset,
                    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
                    llm=llm,
                    embeddings=embeddings,
                )

                result_dict = {}
                if hasattr(result, "to_pandas"):
                    try:
                        result_df = result.to_pandas()
                        if len(result_df.index) > 0:
                            result_dict = result_df.iloc[0].to_dict()
                    except Exception:
                        result_dict = {}
                elif isinstance(result, dict):
                    result_dict = result

                partial = {
                    "faithfulness": safe_float(result_dict.get("faithfulness")),
                    "answer_relevancy": safe_float(result_dict.get("answer_relevancy")),
                    "context_precision": safe_float(result_dict.get("context_precision")),
                    "context_recall": safe_float(result_dict.get("context_recall")),
                }
                partial_results.append(partial)
                qa_system.mysql_client.update_assessment_result_progress(result_id, index)

                yield f"data: {_json.dumps({'type': 'progress', 'result_id': result_id, 'completed_questions': index, 'total_questions': total, 'current_item': index, 'latest_result': partial}, ensure_ascii=False)}\n\n"

            def average_metric(metric_name):
                values = [item[metric_name] for item in partial_results if item.get(metric_name) is not None]
                return round(sum(values) / len(values), 6) if values else None

            results = {
                "faithfulness": average_metric("faithfulness"),
                "answer_relevancy": average_metric("answer_relevancy"),
                "context_precision": average_metric("context_precision"),
                "context_recall": average_metric("context_recall"),
            }

            result_content = _json.dumps(
                {
                    "summary": results,
                    "items": partial_results,
                },
                ensure_ascii=False,
            )
            qa_system.mysql_client.complete_assessment_result(result_id, results, result_content)

            yield f"data: {_json.dumps({'type': 'complete', 'result_id': result_id, 'completed_questions': total, 'total_questions': total, 'results': results}, ensure_ascii=False)}\n\n"
        except Exception as e:
            qa_system.mysql_client.fail_assessment_result(result_id, str(e))
            yield f"data: {_json.dumps({'type': 'error', 'result_id': result_id, 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
