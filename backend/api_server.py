# api_server.py - FastAPI服务，将AI测试用例生成功能封装为RESTful API
import os
import sys
import json
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 设置基础路径
BASE_DIR = "E:/sm-ai"
DATA_DIR = os.path.join(BASE_DIR, "data")

# 创建所需目录
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "api_temp"), exist_ok=True)

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
from enum import Enum

# 导入后端模块
from backend.database import Database
from backend.knowledge_base import KnowledgeBase
from backend.testcase_generator import TestCaseGenerator
from backend.document_processor import DocumentProcessor
from backend.ai_client import AIClient

# 初始化应用
app = FastAPI(
    title="AI测试用例生成系统API",
    description="将AI测试用例生成功能封装为RESTful API",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库路径
DB_PATH = os.path.join(DATA_DIR, "testcase.db")

# 全局变量存储API状态
api_state = {
    "initialized": False,
    "db": None,
    "kb": None,
    "testcase_gen": None,
    "document_processor": None,
    "ai_client": None,
    "active_sessions": {}  # 存储活动会话
}

class GenerationStep(str, Enum):
    SUMMARY = "summary"
    TEST_POINTS = "test_points"
    TEST_CASES = "test_cases"
    FINAL = "final"

class GenerationRequest(BaseModel):
    """生成请求模型"""
    session_id: Optional[str] = Field(None, description="会话ID，如果为空则创建新会话")
    step: GenerationStep = Field(..., description="生成步骤")
    document_text: Optional[str] = Field(None, description="文档文本内容")
    previous_result: Optional[str] = Field(None, description="上一步的结果")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="配置参数")

class GenerationResponse(BaseModel):
    """生成响应模型"""
    session_id: str = Field(..., description="会话ID")
    step: GenerationStep = Field(..., description="当前步骤")
    status: str = Field(..., description="状态: success, error, processing")
    result: Optional[str] = Field(None, description="生成结果")
    error: Optional[str] = Field(None, description="错误信息")
    progress: Optional[float] = Field(None, description="进度0-1")
    next_step: Optional[GenerationStep] = Field(None, description="下一步骤")
    timestamp: str = Field(..., description="时间戳")

class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str = Field(..., description="会话ID")
    created_at: str = Field(..., description="创建时间")
    last_activity: str = Field(..., description="最后活动时间")
    current_step: Optional[GenerationStep] = Field(None, description="当前步骤")
    document_name: Optional[str] = Field(None, description="文档名称")
    status: str = Field(..., description="会话状态")

class QAResponse(BaseModel):
    """智能问答响应模型"""
    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    reference_count: int = Field(0, description="参考文档数量")
    session_id: Optional[str] = Field(None, description="会话ID")

# 初始化函数
def initialize_api():
    """初始化API服务"""
    try:
        print("正在初始化API服务...")
        
        # 初始化数据库
        api_state["db"] = Database(db_path=DB_PATH)
        
        # 初始化知识库
        kb_dir = os.path.join(DATA_DIR, "knowledge_base")
        api_state["kb"] = KnowledgeBase(kb_dir=kb_dir, db_path=DB_PATH)
        
        # 初始化测试用例生成器
        output_dir = os.path.join(DATA_DIR, "outputs")
        api_state["testcase_gen"] = TestCaseGenerator(output_dir=output_dir)
        
        # 初始化文档处理器
        api_state["document_processor"] = DocumentProcessor()
        
        # 初始化AI客户端
        api_state["ai_client"] = AIClient(knowledge_base=api_state["kb"])
        
        api_state["initialized"] = True
        print("API服务初始化完成")
        return True
    except Exception as e:
        print(f"API服务初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 在应用启动时初始化
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    initialize_api()

def generate_session_id() -> str:
    """生成唯一会话ID"""
    return f"session_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

def update_session(session_id: str, step: Optional[GenerationStep] = None, 
                   document_name: Optional[str] = None):
    """更新会话信息"""
    now = datetime.now().isoformat()
    
    if session_id not in api_state["active_sessions"]:
        api_state["active_sessions"][session_id] = {
            "session_id": session_id,
            "created_at": now,
            "last_activity": now,
            "current_step": step,
            "document_name": document_name,
            "status": "active",
            "data": {}  # 存储会话数据
        }
    else:
        api_state["active_sessions"][session_id]["last_activity"] = now
        if step:
            api_state["active_sessions"][session_id]["current_step"] = step
        if document_name:
            api_state["active_sessions"][session_id]["document_name"] = document_name

def cleanup_old_sessions():
    """清理过期会话（24小时未活动）"""
    now = datetime.now()
    expired_sessions = []
    
    for session_id, session in api_state["active_sessions"].items():
        last_activity = datetime.fromisoformat(session["last_activity"])
        if (now - last_activity).total_seconds() > 24 * 3600:  # 24小时
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del api_state["active_sessions"][session_id]
        print(f"已清理过期会话: {session_id}")

async def stream_generation(step: GenerationStep, document_text: str, session_id: str):
    """流式生成函数"""
    try:
        if not api_state["initialized"]:
            yield json.dumps({
                "session_id": session_id,
                "step": step,
                "status": "error",
                "error": "API服务未初始化",
                "timestamp": datetime.now().isoformat()
            }) + "\n"
            return
        
        # 更新会话
        update_session(session_id, step)
        
        if step == GenerationStep.SUMMARY:
            # 第一步：专业需求文档分析
            yield json.dumps({
                "session_id": session_id,
                "step": step,
                "status": "processing",
                "progress": 0.1,
                "message": "开始文档分析...",
                "timestamp": datetime.now().isoformat()
            }) + "\n"
            
            # 模拟流式输出
            steps = ["文档初步解析", "功能点识别", "问题识别", "测试关注点分析", "自我检查", "生成综合报告"]
            for i, step_name in enumerate(steps):
                await asyncio.sleep(0.5)  # 模拟处理时间
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "processing",
                    "progress": (i + 1) / len(steps) * 0.8,
                    "message": f"正在进行：{step_name}",
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
            
            # 实际生成
            try:
                summary = api_state["ai_client"].enhanced_generate_summary_step(document_text)
                
                # 存储结果到会话
                if session_id in api_state["active_sessions"]:
                    api_state["active_sessions"][session_id]["data"]["summary"] = summary
                
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "success",
                    "result": summary,
                    "progress": 1.0,
                    "next_step": GenerationStep.TEST_POINTS,
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
            except Exception as e:
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "error",
                    "error": f"文档分析失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
        
        elif step == GenerationStep.TEST_POINTS:
            # 第二步：基于功能点的测试点详细拆分
            yield json.dumps({
                "session_id": session_id,
                "step": step,
                "status": "processing",
                "progress": 0.1,
                "message": "开始测试点生成...",
                "timestamp": datetime.now().isoformat()
            }) + "\n"
            
            steps = ["提取功能点", "等价类划分", "边界值分析", "因果图分析", "场景分析", "生成测试点"]
            for i, step_name in enumerate(steps):
                await asyncio.sleep(0.5)  # 模拟处理时间
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "processing",
                    "progress": (i + 1) / len(steps) * 0.8,
                    "message": f"正在执行：{step_name}",
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
            
            # 实际生成
            try:
                analysis_report = api_state["active_sessions"][session_id]["data"].get("summary", "")
                test_points, analysis_report = api_state["ai_client"].enhanced_generate_test_points_step(analysis_report)
                
                # 存储结果到会话
                if session_id in api_state["active_sessions"]:
                    api_state["active_sessions"][session_id]["data"]["test_points"] = test_points
                    api_state["active_sessions"][session_id]["data"]["analysis_report"] = analysis_report
                
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "success",
                    "result": test_points,
                    "progress": 1.0,
                    "next_step": GenerationStep.TEST_CASES,
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
            except Exception as e:
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "error",
                    "error": f"测试点生成失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
        
        elif step == GenerationStep.TEST_CASES:
            # 第三步：智能问答生成测试用例
            yield json.dumps({
                "session_id": session_id,
                "step": step,
                "status": "processing",
                "progress": 0.1,
                "message": "开始测试用例生成...",
                "timestamp": datetime.now().isoformat()
            }) + "\n"
            
            steps = ["解析测试点", "准备智能问答", "生成测试用例", "进行完整性检查", "生成验证报告"]
            for i, step_name in enumerate(steps):
                await asyncio.sleep(0.5)  # 模拟处理时间
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "processing",
                    "progress": (i + 1) / len(steps) * 0.8,
                    "message": f"正在执行：{step_name}",
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
            
            # 实际生成
            try:
                test_points = api_state["active_sessions"][session_id]["data"].get("test_points", "")
                test_cases, validation_report, test_cases_details = api_state["ai_client"].enhanced_generate_test_cases_step(test_points)
                
                # 存储结果到会话
                if session_id in api_state["active_sessions"]:
                    api_state["active_sessions"][session_id]["data"]["test_cases"] = test_cases
                    api_state["active_sessions"][session_id]["data"]["validation_report"] = validation_report
                    api_state["active_sessions"][session_id]["data"]["test_cases_details"] = test_cases_details
                
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "success",
                    "result": test_cases,
                    "progress": 1.0,
                    "next_step": GenerationStep.FINAL,
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
            except Exception as e:
                yield json.dumps({
                    "session_id": session_id,
                    "step": step,
                    "status": "error",
                    "error": f"测试用例生成失败: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }) + "\n"
        
        elif step == GenerationStep.FINAL:
            # 第四步：最终输出
            yield json.dumps({
                "session_id": session_id,
                "step": step,
                "status": "success",
                "message": "生成流程完成",
                "progress": 1.0,
                "timestamp": datetime.now().isoformat()
            }) + "\n"
    
    except Exception as e:
        yield json.dumps({
            "session_id": session_id,
            "step": step,
            "status": "error",
            "error": f"生成过程中发生错误: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }) + "\n"

# API路由定义
@app.get("/")
async def root():
    """API根端点"""
    return {
        "service": "AI测试用例生成系统API",
        "version": "1.0.0",
        "status": "running",
        "initialized": api_state["initialized"]
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy" if api_state["initialized"] else "unhealthy",
        "initialized": api_state["initialized"],
        "active_sessions": len(api_state["active_sessions"])
    }

@app.post("/sessions", response_model=Dict[str, str])
async def create_session():
    """创建新会话"""
    session_id = generate_session_id()
    update_session(session_id)
    
    return {
        "session_id": session_id,
        "message": "会话创建成功",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """获取所有活跃会话"""
    cleanup_old_sessions()
    
    sessions = []
    for session_id, session_data in api_state["active_sessions"].items():
        sessions.append(SessionInfo(**session_data))
    
    return sessions

@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """获取特定会话信息"""
    if session_id not in api_state["active_sessions"]:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return SessionInfo(**api_state["active_sessions"][session_id])

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    if session_id in api_state["active_sessions"]:
        del api_state["active_sessions"][session_id]
        return {"message": "会话已删除", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail="会话不存在")

@app.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None, description="会话ID，如果为空则创建新会话")
):
    """上传文档文件"""
    try:
        if not session_id:
            session_id = generate_session_id()
        
        # 保存上传的文件
        temp_dir = os.path.join(DATA_DIR, "api_temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, f"{session_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 读取文档内容
        document_text = api_state["document_processor"].read_file(file_path)
        
        # 更新会话
        update_session(session_id, GenerationStep.SUMMARY, file.filename)
        api_state["active_sessions"][session_id]["data"]["document_text"] = document_text
        api_state["active_sessions"][session_id]["data"]["file_path"] = file_path
        
        return {
            "session_id": session_id,
            "filename": file.filename,
            "file_size": len(content),
            "message": "文件上传成功",
            "next_step": "summary",
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@app.post("/generate/stream")
async def generate_stream(request: GenerationRequest):
    """流式生成测试用例（SSE）"""
    # 检查服务状态
    if not api_state["initialized"]:
        raise HTTPException(status_code=503, detail="API服务未初始化")
    
    # 获取或创建会话ID
    session_id = request.session_id or generate_session_id()
    
    # 获取文档文本
    document_text = request.document_text
    if not document_text and session_id in api_state["active_sessions"]:
        document_text = api_state["active_sessions"][session_id]["data"].get("document_text", "")
    
    if not document_text and request.step == GenerationStep.SUMMARY:
        raise HTTPException(status_code=400, detail="文档文本不能为空")
    
    # 返回流式响应
    return StreamingResponse(
        stream_generation(request.step, document_text, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/generate/sync")
async def generate_sync(request: GenerationRequest):
    """同步生成测试用例（一次性返回）"""
    # 检查服务状态
    if not api_state["initialized"]:
        raise HTTPException(status_code=503, detail="API服务未初始化")
    
    # 获取或创建会话ID
    session_id = request.session_id or generate_session_id()
    
    # 获取文档文本
    document_text = request.document_text
    if not document_text and session_id in api_state["active_sessions"]:
        document_text = api_state["active_sessions"][session_id]["data"].get("document_text", "")
    
    if not document_text and request.step == GenerationStep.SUMMARY:
        raise HTTPException(status_code=400, detail="文档文本不能为空")
    
    try:
        result = None
        next_step = None
        
        if request.step == GenerationStep.SUMMARY:
            # 第一步：专业需求文档分析
            result = api_state["ai_client"].enhanced_generate_summary_step(document_text)
            next_step = GenerationStep.TEST_POINTS
            
            # 存储结果到会话
            update_session(session_id, GenerationStep.SUMMARY)
            if session_id in api_state["active_sessions"]:
                api_state["active_sessions"][session_id]["data"]["summary"] = result
        
        elif request.step == GenerationStep.TEST_POINTS:
            # 第二步：基于功能点的测试点详细拆分
            analysis_report = request.previous_result or ""
            if not analysis_report and session_id in api_state["active_sessions"]:
                analysis_report = api_state["active_sessions"][session_id]["data"].get("summary", "")
            
            test_points, analysis_report = api_state["ai_client"].enhanced_generate_test_points_step(analysis_report)
            result = test_points
            next_step = GenerationStep.TEST_CASES
            
            # 存储结果到会话
            update_session(session_id, GenerationStep.TEST_POINTS)
            if session_id in api_state["active_sessions"]:
                api_state["active_sessions"][session_id]["data"]["test_points"] = test_points
                api_state["active_sessions"][session_id]["data"]["analysis_report"] = analysis_report
        
        elif request.step == GenerationStep.TEST_CASES:
            # 第三步：智能问答生成测试用例
            test_points = request.previous_result or ""
            if not test_points and session_id in api_state["active_sessions"]:
                test_points = api_state["active_sessions"][session_id]["data"].get("test_points", "")
            
            test_cases, validation_report, test_cases_details = api_state["ai_client"].enhanced_generate_test_cases_step(test_points)
            result = test_cases
            next_step = GenerationStep.FINAL
            
            # 存储结果到会话
            update_session(session_id, GenerationStep.TEST_CASES)
            if session_id in api_state["active_sessions"]:
                api_state["active_sessions"][session_id]["data"]["test_cases"] = test_cases
                api_state["active_sessions"][session_id]["data"]["validation_report"] = validation_report
                api_state["active_sessions"][session_id]["data"]["test_cases_details"] = test_cases_details
        
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

@app.post("/export/excel")
async def export_excel(
    session_id: str = Query(..., description="会话ID"),
    filename: Optional[str] = Query(None, description="输出文件名")
):
    """导出Excel测试用例文件"""
    if session_id not in api_state["active_sessions"]:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session_data = api_state["active_sessions"][session_id]
    test_cases = session_data["data"].get("test_cases", "")
    
    if not test_cases:
        raise HTTPException(status_code=400, detail="没有可导出的测试用例数据")
    
    try:
        # 使用原始文件名或自定义文件名
        original_filename = session_data.get("document_name", "test_cases")
        if filename:
            base_name = filename
        else:
            base_name = os.path.splitext(original_filename)[0]
        
        # 生成Excel文件
        output_path = api_state["testcase_gen"].generate_excel(test_cases, base_name)
        
        # 将文件内容读取为字节
        with open(output_path, "rb") as f:
            file_content = f.read()
        
        # 返回文件下载
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(output_path)}"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")

@app.post("/qa/ask", response_model=QAResponse)
async def ask_question(
    question: str = Query(..., description="问题内容"),
    reference_count: int = Query(10, description="参考文档数量"),
    session_id: Optional[str] = Query(None, description="会话ID")
):
    """智能问答"""
    try:
        # 使用知识库搜索
        search_k = min(50, reference_count * 2)
        knowledge_results = api_state["kb"].search_with_score(question, k=search_k)
        
        # 选择相关结果
        selected_contexts = []
        for content, metadata, distance in knowledge_results:
            similarity = api_state["kb"].get_similarity_percentage(distance)
            if similarity >= 65:  # 相似度阈值
                source = metadata.get('source', '未知来源')
                context_text = f"来源: {source}\n相似度: {similarity:.1f}%\n\n{content}"
                selected_contexts.append(context_text)
        
        # 限制上下文数量
        selected_contexts = selected_contexts[:reference_count]
        
        # 生成答案
        answer = api_state["ai_client"].answer_with_knowledge(question, selected_contexts)
        
        # 保存到数据库
        record_id = api_state["db"].add_qa_record(
            question=question,
            answer=answer,
            reference_count=len(selected_contexts)
        )
        
        return QAResponse(
            question=question,
            answer=answer,
            reference_count=len(selected_contexts),
            session_id=session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能问答失败: {str(e)}")

@app.get("/knowledge/search")
async def search_knowledge(
    query: str = Query(..., description="搜索查询"),
    limit: int = Query(10, description="结果数量"),
    min_similarity: float = Query(65.0, description="最小相似度")
):
    """搜索知识库"""
    try:
        search_k = min(50, limit * 2)
        knowledge_results = api_state["kb"].search_with_score(query, k=search_k)
        
        results = []
        for content, metadata, distance in knowledge_results:
            similarity = api_state["kb"].get_similarity_percentage(distance)
            if similarity >= min_similarity:
                results.append({
                    "content": content[:500] + "..." if len(content) > 500 else content,
                    "metadata": metadata,
                    "similarity": similarity,
                    "distance": distance
                })
        
        # 按相似度排序并限制数量
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:limit]
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"知识库搜索失败: {str(e)}")

# 启动脚本
if __name__ == "__main__":
    print("启动AI测试用例生成系统API服务...")
    print(f"API地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print(f"备用文档: http://localhost:8000/redoc")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )