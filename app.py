import streamlit as st
import datetime as dt
import pandas as pd
from arxiv_pdf import fetch_papers
from paper_affiliation_classifier import PaperAffiliationClassifier
from paper_assistant import PaperAssistant
import affiliation_analyzer
from abstract_matcher import AbstractMatcher
from orgs import orgs
from tools import clean_folder, is_pipeline_running, start_pipeline_background
from output_file_format_manager import (
    get_download_link, get_binary_file_downloader_html, 
    display_markdown_with_images, markdown_to_docx, load_default_markdown
)
import os
def provide_download_links(markdown_content, docx_content, filename_prefix="AI生成_每日arXiv精选论文"):
    """提供markdown和docx格式的下载链接"""
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            get_download_link(markdown_content, f"{filename_prefix}.md", "点击下载Markdown文件"),
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            get_binary_file_downloader_html(docx_content, "点击下载Word文件", f"{filename_prefix}.md.docx"),
            unsafe_allow_html=True
        )

def main():
    st.set_page_config(page_title="每日arXiv论文快报", page_icon="📚")
    
    st.title("AI4Paper")

    if os.path.exists("paper_pipeline.log"):
        print("paper_pipeline.log存在")
    
    # 检查并启动paper_pipeline.py
    if not is_pipeline_running():
        st.info("流水线未启动，现在启动论文处理流水线")
        start_pipeline_background(st)
    else:
        st.info("论文处理流水线正在后台运行中")
    
    # 加载默认的markdown文件
    default_markdown = load_default_markdown()
    
    
    st.write("点击下方按钮生成自定义论文快报")
    
    # 添加一些配置选项
    with st.expander("高级配置"):
        days_back = st.slider("查询过去几天的论文", 1, 7, 1)
        
        # 目标机构多选
        default_orgs = orgs
        target_orgs = st.multiselect(
            "目标机构", 
            options=default_orgs,
            default=default_orgs
        )
        
        # 添加关键词查询选项
        use_keyword_filter = st.checkbox("使用自然语言过滤论文", value=False)
        keyword_query = ""
        if use_keyword_filter:
            keyword_query = st.text_input("请输入提示词", placeholder="例如：强化学习、机器人、大模型等")
        
    
    is_refresh = st.button("生成自定义论文快报", type="primary")
    
    # 生成按钮
    if is_refresh:
        # 清空pdf_folder和images文件夹
        clean_folder("pdf_folder")
        clean_folder("images")

        with st.spinner("正在获取和处理论文，请稍候..."):
            # 创建进度条
            progress_bar = st.progress(0)
            
            # 第一步：运行pipeline获取论文,并打上分类标签
            st.info("步骤1/4: 从arXiv获取论文...")
            progress_bar.progress(10)
            
            csv_filename = "papers.csv"
            pdf_folder = "pdf_folder"
            
            # 使用默认的查询字符串 "cat:cs.AI"
            query = "cat:cs.AI"
            
            end_date = dt.datetime.today()
            start_date = end_date - dt.timedelta(days=days_back)
            papers_count = fetch_papers(
                pdf_folder, 
                csv_filename=csv_filename,
                query=query,
                author_filter=False,
                start_date=start_date,
                end_date=end_date
            )
            
            if papers_count == 0:
                st.error("没有找到符合条件的论文，请调整查询参数后重试。")
                return
            
            classifier = PaperAffiliationClassifier()
            classifier.process_csv(csv_filename)
            
            progress_bar.progress(30)
            
            # 第二步：获取目标机构的论文索引
            indices_result = []
            if target_orgs:
                st.info("步骤2/4: 模型筛选目标机构论文...")
                analyzer = affiliation_analyzer.AffiliationAnalyzer()
                indices_result = analyzer.process_csv(csv_filename, target_orgs)
                progress_bar.progress(50)
            
            # 第三步：根据关键词过滤论文
            keyword_indices = []
            if use_keyword_filter and keyword_query:
                st.info("步骤3/4: 根据关键词过滤论文...")
                matcher = AbstractMatcher()
                keyword_indices = matcher.process_csv(csv_filename, keyword_query)
                progress_bar.progress(70)
            else:
                st.info("步骤3/4: 跳过关键词过滤...")
                progress_bar.progress(70)
            
            # 合并过滤结果
            final_indices = []
            if target_orgs and use_keyword_filter and keyword_query:
                # 两种过滤器都启用，取交集
                final_indices = list(set(indices_result).intersection(set(keyword_indices)))
                if not final_indices:
                    st.warning("没有同时满足机构和关键词条件的论文，将显示所有满足机构条件的论文")
                    final_indices = indices_result
            elif target_orgs:
                # 只使用机构过滤
                final_indices = indices_result
            elif use_keyword_filter and keyword_query:
                # 只使用关键词过滤
                final_indices = keyword_indices
            else:
                # 都不使用，获取所有论文索引
                df = pd.read_csv(csv_filename)
                final_indices = list(range(len(df)))
            
            if not final_indices:
                st.error("没有找到符合条件的论文，请调整过滤条件后重试。")
                return
            
            # 第四步：下载论文并生成摘要
            st.info("步骤4/4: 生成论文摘要...")
            assistant = PaperAssistant(output_dir=pdf_folder)
            markdown_content = assistant.process_and_download(csv_filename, final_indices)
            
            progress_bar.progress(100)
            
            # 显示结果
            st.success(f"成功生成论文快报，共包含 {len(final_indices)} 篇论文（从 {papers_count} 篇论文中筛选）")
            # 使用新的display_markdown_with_images函数显示markdown内容
            display_markdown_with_images(markdown_content)
            
            # 生成Word文档
            docx_content = markdown_to_docx(markdown_content)
            
            # 提供下载链接
            provide_download_links(markdown_content, docx_content)
    
    # 只有在没有点击刷新按钮时才显示默认markdown
    elif default_markdown:
        st.info("已生成默认的论文快报（按机构筛选，每12小时刷新一次），以下为预加载内容：")
        display_markdown_with_images(default_markdown)
        # 生成Word文档
        docx_content = markdown_to_docx(default_markdown)
        # 提供下载链接
        provide_download_links(default_markdown, docx_content)

if __name__ == "__main__":
    main() 