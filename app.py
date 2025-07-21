# streamlit_app.py
# 禁用文件监视器避免错误
import os
os.environ['STREAMLIT_SERVER_FILE_WATCHER'] = 'none'
os.environ['STREAMLIT_DISABLE_LOGGING'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # 避免huggingface的并行错误

import sys
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 必须是第一个Streamlit命令
import streamlit as st
st.set_page_config(page_title="AI 测试用例生成系统", layout="wide")
try:
    import torch
    # 防止 Streamlit 监视 torch 模块
    from streamlit import cli as stcli
    stcli._get_command_line = lambda: None
    stcli._get_command_line_as_string = lambda: ""
except ImportError:
    pass
# 移除所有关于torch的设置
# 继续其他导入
import time
from datetime import datetime
from typing import List, Dict

# 导入后端模块
from backend.database import Database
from backend.knowledge_base import KnowledgeBase
from backend.testcase_generator import TestCaseGenerator
from backend.document_processor import DocumentProcessor
from backend.ai_client import AIClient

# 初始化会话状态
if 'initialized' not in st.session_state:
    try:
        # 初始化数据库实例
        st.session_state.db = Database()
        
        # 其他组件初始化
        st.session_state.kb = KnowledgeBase()
        st.session_state.ai_client = AIClient(knowledge_base=st.session_state.kb)
        st.session_state.testcase_gen = TestCaseGenerator()
        st.session_state.document_processor = DocumentProcessor()
        
        st.session_state.initialized = True
        st.toast("系统初始化完成", icon="✅")
    except Exception as e:
        st.error(f"初始化失败: {str(e)}")
        st.error("请检查配置文件或依赖项安装情况")
        st.stop()

# 侧边栏导航
st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["生成测试用例", "历史记录", "知识库管理"])

if page == "生成测试用例":
    st.title("AI 测试用例生成系统")
    
    # 文件上传
    uploaded_file = st.file_uploader("上传 Word 或 PDF 文档", type=["docx", "pdf"])
    
    # 提示词输入
    summary_prompt = st.text_area("总结提示词", value="请总结文档的主要内容，提取关键功能点和业务规则。")
    decision_prompt = st.text_area("决策表提示词", value="根据文档总结，生成测试决策表，包含所有可能的输入组合和预期输出。")
    testcase_prompt = st.text_area("测试用例提示词", value="根据决策表生成详细的测试用例，包含测试步骤、预期结果和优先级。")
    
    if st.button("生成测试用例") and uploaded_file:
        with st.spinner("正在处理文档..."):
            # 保存上传的文件
            upload_dir = "data/uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 读取文档内容
            try:
                doc_text = st.session_state.document_processor.read_file(file_path)
            except Exception as e:
                st.error(f"读取文件失败: {str(e)}")
                st.stop()
            
            # 生成总结
            try:
                summary = st.session_state.ai_client.generate_summary(doc_text, summary_prompt)
            except Exception as e:
                st.error(f"生成总结失败: {str(e)}")
                st.stop()
            
            # 生成决策表
            try:
                decision_table = st.session_state.ai_client.generate_decision_table(summary, decision_prompt)
            except Exception as e:
                st.error(f"生成决策表失败: {str(e)}")
                st.stop()
            
            # 生成测试用例
            try:
                test_cases = st.session_state.ai_client.generate_test_cases(decision_table, testcase_prompt)
            except Exception as e:
                st.error(f"生成测试用例失败: {str(e)}")
                st.stop()
            
            # 生成 Excel 文件
            try:
                output_path = st.session_state.testcase_gen.generate_excel(test_cases, uploaded_file.name)
            except Exception as e:
                st.error(f"生成 Excel 文件失败: {str(e)}")
                st.stop()
            
            # 保存记录
            record_id = st.session_state.db.add_record(
                original_filename=uploaded_file.name,
                file_path=file_path,
                output_filename=os.path.basename(output_path),
                output_path=output_path,
                summary=summary,
                decision_table=decision_table
            )
            
            # 显示结果
            st.success("测试用例生成完成！")
            
            # 显示生成的各个阶段结果
            st.subheader("文档总结")
            st.write(summary)
            
            st.subheader("决策表")
            st.write(decision_table)
            
            st.subheader("生成的测试用例")
            st.write(test_cases)
            
            # 提供下载链接
            with open(output_path, "rb") as f:
                st.download_button(
                    label="下载 Excel 测试用例",
                    data=f,
                    file_name=os.path.basename(output_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

elif page == "历史记录":
    st.title("历史生成记录")
    
    records = st.session_state.db.get_records()
    if not records:
        st.info("暂无历史记录")
    else:
        for record in records:
            with st.expander(f"{record['original_filename']} - {record['created_at']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**原始文件:**", record['original_filename'])
                    st.write("**生成时间:**", record['created_at'])
                    
                    with open(record['output_path'], "rb") as f:
                        st.download_button(
                            label="下载测试用例",
                            data=f,
                            file_name=record['output_filename'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{record['id']}"
                        )
                
                with col2:
                    if st.button(f"查看详情", key=f"detail_{record['id']}"):
                        st.subheader("文档总结")
                        st.write(record['summary'])
                        
                        st.subheader("决策表")
                        st.write(record['decision_table'])

elif page == "知识库管理":
    st.title("知识库管理")
    
    st.subheader("知识库状态")
    if hasattr(st.session_state.kb, 'vectorstore') and st.session_state.kb.vectorstore:
        st.success("知识库已成功加载")
        try:
            doc_count = len(st.session_state.kb.vectorstore.docstore._dict)
            st.write(f"包含文档数: {doc_count}")
        except:
            st.info("无法获取文档数量")
    else:
        st.warning("知识库未完全初始化")
    st.subheader("决策表生成测试")
    test_summary = st.text_area("输入测试摘要", "用户登录功能，包含管理员和普通用户角色")
    if st.button("测试知识库引用"):
        try:
            # 模拟决策表生成流程
            knowledge_context = st.session_state.kb.search(test_summary, k=3, full_content=True)
            st.write("### 知识库引用内容")
            for i, content in enumerate(knowledge_context):
                st.text_area(f"知识库结果 {i+1}", content, height=150)
        except Exception as e:
            st.error(f"测试失败: {str(e)}")
    # 上传知识文件
    st.subheader("上传知识文件")
    knowledge_file = st.file_uploader(
        "上传 Excel、CSV 或文本文件到知识库", 
        type=["csv", "xlsx", "xls", "txt", "docx", "pdf"]
    )
    
    if knowledge_file and st.button("上传到知识库"):
        with st.spinner("上传并处理文件中..."):
            try:
                # 创建上传目录
                kb_dir = os.path.normpath("data/knowledge_base/files")
                os.makedirs(kb_dir, exist_ok=True)
                
                # 保存文件
                file_path = os.path.join(kb_dir, knowledge_file.name)
                with open(file_path, "wb") as f:
                    f.write(knowledge_file.getbuffer())
                
                # 添加到知识库
                st.session_state.kb.add_document(file_path)
                st.session_state.db.add_knowledge_file(knowledge_file.name, file_path)
                st.success("文件已成功添加到知识库")
            except Exception as e:
                error_msg = f"添加文件到知识库失败: {str(e)}"
                st.error(error_msg)
    
    # 显示知识库文件列表
    st.subheader("知识库文件列表")
    if "knowledge_files" not in st.session_state:
        try:
            kb_files_dir = "data/knowledge_base/files"
            if os.path.exists(kb_files_dir):
                kb_files = os.listdir(kb_files_dir)
                st.session_state.knowledge_files = kb_files
            else:
                st.session_state.knowledge_files = []
        except Exception as e:
            st.error(f"加载知识库文件列表失败: {str(e)}")
            st.session_state.knowledge_files = []
    
    if not st.session_state.knowledge_files:
        st.info("知识库中暂无文件")
    else:
        for i, filename in enumerate(st.session_state.knowledge_files):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{i+1}. {filename}")
            with col2:
                if st.button(f"删除", key=f"del_{filename}"):
                    try:
                        file_path = os.path.join("data/knowledge_base/files", filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        st.success(f"已删除文件: {filename}")
                        
                        # 重新初始化知识库
                        kb = st.session_state.kb
                        kb._vectorstore = None
                        st.session_state.kb = kb
                        
                        # 刷新列表
                        del st.session_state.knowledge_files
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"删除文件失败: {str(e)}")
    
    # 知识库搜索
    st.subheader("知识库搜索")
    query = st.text_input("输入查询内容")
    if query and st.button("搜索"):
        results = st.session_state.kb.search(query)
        if results:
            st.write("搜索结果:")
            for i, result in enumerate(results, 1):
                with st.expander(f"结果 {i}"):
                    st.write(result)
        else:
            st.info("没有找到相关结果")
            
# 添加一些样式
st.markdown("""
<style>
    .stExpander {
        margin-bottom: 1rem;
        border: 1px solid #eee;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    .stDownloadButton button {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)