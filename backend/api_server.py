# ============================================================================
# api_server.py - AI测试用例生成系统 RESTful API
# 修正：/qa/ask 改为 POST + Body，支持选定参考；新增记录导出接口；新增会话数据重置接口
# 新增：根路径返回 index.html 实现单端口部署
# 修复：/feedback/export 文件名编码问题
# 优化：/generate/sync 使用 asyncio.to_thread 避免阻塞事件循环，支持并发访问
# ============================================================================

import os
import sys
import json
import uuid
import asyncio
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from urllib.parse import quote

BASE_DIR = "E:/sm-ai"
DATA_DIR = os.path.join(BASE_DIR, "data")
sys.path.append(BASE_DIR)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "api_temp"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "outputs"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "knowledge_base", "files"), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "knowledge_base", "faiss_index"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "log"), exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "testcase.db")

try:
    from backend.database import Database
    from backend.knowledge_base import KnowledgeBase
    from backend.testcase_generator import TestCaseGenerator
    from backend.document_processor import DocumentProcessor
    from backend.ai_client import AIClient
    from backend.qa_logger import QALogger
    print("✅ 成功导入后端模块")
except ImportError as e:
    print(f"❌ 导入后端模块失败: {e}")
    sys.exit(1)

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import StreamingResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import pandas as pd
import io

app = FastAPI(title="AI测试用例生成系统API", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

api_state = {
    "initialized": False,
    "db": None,
    "kb": None,
    "testcase_gen": None,
    "document_processor": None,
    "ai_client": None,
    "qa_logger": None,
    "active_sessions": {}
}

class GenerationStep(str, Enum):
    SUMMARY = "summary"
    TEST_POINTS = "test_points"
    TEST_CASES = "test_cases"
    FINAL = "final"

class GenerationRequest(BaseModel):
    session_id: Optional[str] = None
    step: GenerationStep
    document_text: Optional[str] = None
    previous_result: Optional[str] = None
    config: Optional[Dict[str, Any]] = {}

class GenerationResponse(BaseModel):
    session_id: str
    step: GenerationStep
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[float] = None
    next_step: Optional[GenerationStep] = None
    timestamp: str

class FeedbackCreate(BaseModel):
    record_id: int
    generator_name: str
    adoption_rate: int
    time_saved_hours: float
    problem_feedback: str

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    current_step: Optional[GenerationStep] = None
    document_name: Optional[str] = None
    status: str

class QaRequest(BaseModel):
    question: str
    contexts: Optional[List[str]] = None
    reference_count: int = 10
    session_id: Optional[str] = None

class QaResponse(BaseModel):
    question: str
    answer: str
    reference_count: int
    session_id: Optional[str] = None

def initialize_api():
    try:
        print("🔄 正在初始化 API 服务...")
        api_state["db"] = Database(db_path=DB_PATH)
        kb_dir = os.path.join(DATA_DIR, "knowledge_base")
        api_state["kb"] = KnowledgeBase(kb_dir=kb_dir, db_path=DB_PATH)
        output_dir = os.path.join(DATA_DIR, "outputs")
        api_state["testcase_gen"] = TestCaseGenerator(output_dir=output_dir)
        api_state["document_processor"] = DocumentProcessor()
        api_state["ai_client"] = AIClient(knowledge_base=api_state["kb"])
        log_dir = os.path.join(BASE_DIR, "log")
        api_state["qa_logger"] = QALogger(log_dir=log_dir)
        api_state["initialized"] = True
        print("✅ API 服务初始化完成")
        return True
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        traceback.print_exc()
        return False

@app.on_event("startup")
async def startup_event():
    initialize_api()

def generate_session_id():
    return f"session_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

def update_session(session_id: str, step: Optional[GenerationStep] = None,
                   document_name: Optional[str] = None):
    now = datetime.now().isoformat()
    if session_id not in api_state["active_sessions"]:
        api_state["active_sessions"][session_id] = {
            "session_id": session_id,
            "created_at": now,
            "last_activity": now,
            "current_step": step,
            "document_name": document_name,
            "status": "active",
            "data": {}
        }
    else:
        api_state["active_sessions"][session_id]["last_activity"] = now
        if step:
            api_state["active_sessions"][session_id]["current_step"] = step
        if document_name:
            api_state["active_sessions"][session_id]["document_name"] = document_name

def cleanup_old_sessions():
    now = datetime.now()
    expired = []
    for sid, sess in api_state["active_sessions"].items():
        last = datetime.fromisoformat(sess["last_activity"])
        if (now - last).total_seconds() > 86400:
            expired.append(sid)
    for sid in expired:
        del api_state["active_sessions"][sid]

# ---------------------------- API 路由 ----------------------------
@app.get("/")
async def root():
    # 读取 index.html 文件并返回
    try:
        html_path = os.path.join(os.path.dirname(__file__), "index.html")
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception as e:
        return {"error": f"无法加载前端页面: {e}"}

@app.get("/health")
async def health_check():
    return {"status": "healthy" if api_state["initialized"] else "unhealthy",
            "initialized": api_state["initialized"],
            "active_sessions": len(api_state["active_sessions"])}

# ---------- 会话管理 ----------
@app.post("/sessions")
async def create_session():
    session_id = generate_session_id()
    update_session(session_id)
    return {"session_id": session_id, "message": "会话创建成功", "timestamp": datetime.now().isoformat()}

@app.get("/sessions")
async def list_sessions():
    cleanup_old_sessions()
    return [SessionInfo(**sess) for sess in api_state["active_sessions"].values()]

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    if session_id not in api_state["active_sessions"]:
        raise HTTPException(404, "会话不存在")
    return SessionInfo(**api_state["active_sessions"][session_id])

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in api_state["active_sessions"]:
        del api_state["active_sessions"][session_id]
        return {"message": "会话已删除"}
    raise HTTPException(404, "会话不存在")

@app.delete("/sessions/{session_id}/data")
async def clear_session_data(session_id: str):
    """清空会话中的中间数据（供前端重置流程）"""
    if session_id not in api_state["active_sessions"]:
        raise HTTPException(404, "会话不存在")
    api_state["active_sessions"][session_id]["data"] = {}
    api_state["active_sessions"][session_id]["current_step"] = None
    return {"message": "会话数据已清空"}

@app.get("/sessions/{session_id}/data")
async def get_session_data(session_id: str):
    if session_id not in api_state["active_sessions"]:
        raise HTTPException(404, "会话不存在")
    return api_state["active_sessions"][session_id]["data"]

# ---------- 文档上传 ----------
@app.post("/upload/document")
async def upload_document(file: UploadFile = File(...), session_id: Optional[str] = Query(None)):
    try:
        if not session_id:
            session_id = generate_session_id()
        temp_dir = os.path.join(DATA_DIR, "api_temp")
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, f"{session_id}_{file.filename}")
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        doc_text = api_state["document_processor"].read_file(file_path)
        update_session(session_id, GenerationStep.SUMMARY, file.filename)
        api_state["active_sessions"][session_id]["data"]["document_text"] = doc_text
        api_state["active_sessions"][session_id]["data"]["file_path"] = file_path
        api_state["active_sessions"][session_id]["data"]["original_filename"] = file.filename
        return {
            "session_id": session_id,
            "filename": file.filename,
            "file_size": len(content),
            "message": "文件上传成功",
            "next_step": "summary",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"文件上传失败: {e}")

# ---------- 同步生成（已优化为异步非阻塞）----------
@app.post("/generate/sync", response_model=GenerationResponse)
async def generate_sync(request: GenerationRequest):
    if not api_state["initialized"]:
        raise HTTPException(503, "服务未初始化")
    session_id = request.session_id or generate_session_id()
    doc_text = request.document_text
    if not doc_text and session_id in api_state["active_sessions"]:
        doc_text = api_state["active_sessions"][session_id]["data"].get("document_text", "")
    try:
        result = None
        next_step = None
        if request.step == GenerationStep.SUMMARY:
            if not doc_text:
                raise HTTPException(400, "文档内容不能为空")
            # 放入线程池执行
            result = await asyncio.to_thread(
                api_state["ai_client"].enhanced_generate_summary_step, doc_text
            )
            next_step = GenerationStep.TEST_POINTS
            update_session(session_id, GenerationStep.SUMMARY)
            api_state["active_sessions"][session_id]["data"]["summary"] = result

        elif request.step == GenerationStep.TEST_POINTS:
            analysis = request.previous_result or api_state["active_sessions"][session_id]["data"].get("summary", "")
            # 封装多返回值函数
            def _run_test_points():
                return api_state["ai_client"].enhanced_generate_test_points_step(analysis)
            result, analysis_report = await asyncio.to_thread(_run_test_points)
            next_step = GenerationStep.TEST_CASES
            update_session(session_id, GenerationStep.TEST_POINTS)
            api_state["active_sessions"][session_id]["data"]["test_points"] = result
            api_state["active_sessions"][session_id]["data"]["analysis_report"] = analysis_report

        elif request.step == GenerationStep.TEST_CASES:
            test_points = request.previous_result or api_state["active_sessions"][session_id]["data"].get("test_points", "")
            def _run_test_cases():
                return api_state["ai_client"].enhanced_generate_test_cases_step(test_points)
            result, validation, details = await asyncio.to_thread(_run_test_cases)
            next_step = GenerationStep.FINAL
            update_session(session_id, GenerationStep.TEST_CASES)
            api_state["active_sessions"][session_id]["data"]["test_cases"] = result
            api_state["active_sessions"][session_id]["data"]["validation"] = validation
            api_state["active_sessions"][session_id]["data"]["details"] = details

        return GenerationResponse(
            session_id=session_id,
            step=request.step,
            status="success",
            result=result,
            next_step=next_step,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        return GenerationResponse(
            session_id=session_id,
            step=request.step,
            status="error",
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

# ---------- 导出Excel ----------
@app.get("/export/excel")
async def export_excel(session_id: str = Query(...)):
    if session_id not in api_state["active_sessions"]:
        raise HTTPException(404, "会话不存在")
    sess = api_state["active_sessions"][session_id]
    test_cases = sess["data"].get("test_cases", "")
    if not test_cases:
        raise HTTPException(400, "没有可导出的测试用例")
    original_name = sess.get("document_name", "test_cases")
    try:
        output_path = api_state["testcase_gen"].generate_excel(test_cases, original_name)
        with open(output_path, "rb") as f:
            content = f.read()
        filename = os.path.basename(output_path)
        encoded_filename = quote(filename)

        # ---------- 新增：保存记录到数据库 ----------
        if "record_id" not in sess["data"]:
            original_filename = sess["data"].get("original_filename", original_name)
            file_path = sess["data"].get("file_path", "")
            summary = sess["data"].get("summary", "")
            requirement_analysis = sess["data"].get("test_points", "")  # 对应数据库字段
            test_validation = sess["data"].get("validation", "")

            record_id = api_state["db"].add_record(
                original_filename=original_filename,
                file_path=file_path,
                output_filename=filename,
                output_path=output_path,
                summary=summary,
                requirement_analysis=requirement_analysis,
                decision_table="",  # 未使用
                test_cases=test_cases,
                test_validation=test_validation
            )
            sess["data"]["record_id"] = record_id  # 标记已保存，避免重复
            print(f"✅ 记录已保存，ID: {record_id}")

        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"导出失败: {e}")

# ---------- 根据记录ID导出Excel（历史记录下载）----------
@app.get("/records/{record_id}/export")
async def export_record_excel(record_id: int):
    try:
        records = api_state["db"].get_records()
        record = next((r for r in records if r["id"] == record_id), None)
        if not record:
            raise HTTPException(404, "记录不存在")
        test_cases = record.get("test_cases", "")
        if not test_cases:
            raise HTTPException(400, "该记录没有测试用例数据")
        original_filename = record.get("original_filename", "历史记录")
        output_path = api_state["testcase_gen"].generate_excel(test_cases, original_filename)
        with open(output_path, "rb") as f:
            content = f.read()
        filename = os.path.basename(output_path)
        encoded_filename = quote(filename)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"导出失败: {e}")

# ---------- 记录管理 ----------
@app.get("/records")
async def get_records():
    try:
        return api_state["db"].get_records()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/records/{record_id}")
async def get_record(record_id: int):
    try:
        records = api_state["db"].get_records()
        record = next((r for r in records if r["id"] == record_id), None)
        if not record:
            raise HTTPException(404, "记录不存在")
        return record
    except Exception as e:
        raise HTTPException(500, str(e))

# ---------- 反馈管理 ----------
@app.post("/feedback")
async def add_feedback(feedback: FeedbackCreate):
    try:
        fid = api_state["db"].add_feedback(
            record_id=feedback.record_id,
            generator_name=feedback.generator_name,
            adoption_rate=feedback.adoption_rate,
            time_saved_hours=feedback.time_saved_hours,
            problem_feedback=feedback.problem_feedback
        )
        if fid > 0:
            return {"id": fid, "message": "反馈提交成功"}
        raise HTTPException(500, "反馈保存失败")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/feedback")
async def get_all_feedback():
    try:
        return api_state["db"].get_all_feedback()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/feedback/export")
async def export_feedback(start_date: str, end_date: str):
    try:
        feedbacks = api_state["db"].get_feedback_by_date_range(start_date, end_date)
        if not feedbacks:
            return Response(content="无数据", media_type="text/plain", status_code=204)
        df = pd.DataFrame(feedbacks)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='反馈记录', index=False)
        output.seek(0)
        filename = f"反馈导出_{start_date}_{end_date}.xlsx"
        encoded_filename = quote(filename)
        return Response(
            content=output.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except Exception as e:
        raise HTTPException(500, f"导出失败: {e}")

# ---------- 知识库管理 ----------
@app.post("/knowledge/upload")
async def upload_knowledge_file(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(api_state["kb"].KB_FILES_DIR, file.filename)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        success = api_state["kb"].add_document(file_path)
        if not success:
            raise HTTPException(500, "索引失败")
        db_success = api_state["db"].add_knowledge_file(file.filename, file_path)
        return {"filename": file.filename, "path": file_path, "indexed": success, "db_recorded": db_success}
    except Exception as e:
        raise HTTPException(500, f"上传失败: {e}")

@app.get("/knowledge/files")
async def get_knowledge_files():
    try:
        return api_state["kb"].get_all_documents()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/knowledge/files/{file_id}")
async def delete_knowledge_file(file_id: int):
    try:
        files = api_state["db"].get_knowledge_documents()
        target = next((f for f in files if f["id"] == file_id), None)
        if not target:
            raise HTTPException(404, "文件不存在")
        file_path = target["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)
        api_state["db"].delete_knowledge_file(file_id)
        api_state["kb"].rebuild_index()
        return {"message": "删除成功", "file_id": file_id}
    except Exception as e:
        raise HTTPException(500, f"删除失败: {e}")

@app.post("/knowledge/rebuild")
async def rebuild_knowledge_index():
    try:
        success = api_state["kb"].rebuild_index()
        return {"success": success, "message": "索引重建完成" if success else "索引重建失败"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/knowledge/search")
async def search_knowledge(query: str = Query(...), limit: int = 10, min_similarity: float = 65.0):
    try:
        results = []
        search_k = min(50, limit * 2)
        raw_results = api_state["kb"].search_with_score(query, k=search_k)
        for content, metadata, distance in raw_results:
            similarity = api_state["kb"].get_similarity_percentage(distance)
            if similarity >= min_similarity:
                results.append({
                    "content": content[:500] + "..." if len(content) > 500 else content,
                    "metadata": metadata,
                    "similarity": similarity,
                    "distance": distance
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:limit]
        return {"query": query, "results": results, "total": len(results), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(500, f"搜索失败: {e}")

# ---------- 智能问答（POST，接收选中的参考）----------
@app.post("/qa/ask", response_model=QaResponse)
async def ask_question(request: QaRequest = Body(...)):
    """基于选定参考或知识库搜索生成答案"""
    try:
        if request.contexts and len(request.contexts) > 0:
            selected = request.contexts
            reference_count = len(selected)
        else:
            search_k = min(50, request.reference_count * 2)
            raw_results = api_state["kb"].search_with_score(request.question, k=search_k)
            selected = []
            for content, metadata, distance in raw_results:
                similarity = api_state["kb"].get_similarity_percentage(distance)
                if similarity >= 65:
                    source = metadata.get('source', '未知来源')
                    selected.append(f"来源: {source}\n相似度: {similarity:.1f}%\n\n{content}")
                if len(selected) >= request.reference_count:
                    break
            reference_count = len(selected)

        answer = api_state["ai_client"].answer_with_knowledge(request.question, selected)
        
        # 记录到数据库
        record_id = api_state["db"].add_qa_record(request.question, answer, reference_count)
        # 记录到日志
        if api_state["qa_logger"]:
            api_state["qa_logger"].log_qa(request.question, answer, reference_count)
        
        return QaResponse(
            question=request.question,
            answer=answer,
            reference_count=reference_count,
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(500, f"问答失败: {e}")

@app.get("/qa/history")
async def get_qa_history(limit: int = 50):
    try:
        return api_state["db"].get_qa_records(limit)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/qa/history/{record_id}")
async def delete_qa_record(record_id: int):
    try:
        success = api_state["db"].delete_qa_record(record_id)
        return {"success": success, "message": "删除成功" if success else "删除失败"}
    except Exception as e:
        raise HTTPException(500, str(e))

# ---------- favicon ----------
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 启动 AI测试用例生成系统 API 服务 (v2.1.0)")
    print(f"📁 数据目录: {DATA_DIR}")
    print(f"🔗 访问地址: http://你的IP:8000")
    print("=" * 60)
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)