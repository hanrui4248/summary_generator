import streamlit as st
import fitz
from openai import OpenAI
import argparse
import os
from datetime import datetime
import arxiv_pdf
import time
import pandas as pd

# 在最开始添加页面配置
st.set_page_config(
    page_title="论文快报生成器",
    layout="wide",  # 使用宽屏布局
    initial_sidebar_state="collapsed"  # 默认收起侧边栏
)

parser = argparse.ArgumentParser(description="PDF 摘要生成器")
parser.add_argument("--api_key", type=str, required=True, help="API Key")
args = parser.parse_args()

client_openrouter = OpenAI(
    api_key=args.api_key,
    base_url="https://openrouter.ai/api/v1"
)

# 可用模型列表
MODEL_OPTIONS = [
    "google/gemini-exp-1206:free", 
    "google/gemini-2.0-flash-thinking-exp:free", 
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "microsoft/phi-3-medium-128k-instruct:free",
]

def extract_text_from_pdf(pdf_path):
    """从 PDF 文件中提取文本"""
    text = ""
    with fitz.open(pdf_path) as pdf_doc:
        for page in pdf_doc:
            text += page.get_text("text") + "\n"
    return text

def summarize_text(text, model_name):
    """使用 OpenAI API 生成摘要"""
    try:
        # # 限制输入文本长度，避免超出模型限制
        # max_length = 14000  # 根据实际模型限制调整
        # text = text[:max_length]
        
        completion = client_openrouter.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "请为以下内容生成简洁明了的中文摘要，请你的摘要中包含以下几个关键点\n 1.整体内容, 2.主要贡献 3.实现方法 4.实验与评估结果\n 我只想让你输出摘要内容，不要回复我的任何话。"},
                {"role": "user", "content": text}
            ],
            timeout=60  # 设置超时时间
        )
        
        if completion and completion.choices and len(completion.choices) > 0:
            return completion.choices[0].message.content
        else:
            raise Exception("API 返回结果为空")
            
    except Exception as e:
        raise Exception(f"生成摘要时出错: {str(e)}")

def generate_daily_report(pdf_folder, model_name):
    """生成每日论文快报"""
    summaries = []
    errors = []
    
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, filename)
            try:
                # 添加PDF文本提取的错误处理
                pdf_text = extract_text_from_pdf(pdf_path)
                if not pdf_text or len(pdf_text.strip()) == 0:
                    raise Exception("PDF文本提取为空")
                
                # 尝试最多3次生成摘要
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        summary = summarize_text(pdf_text, model_name)
                        if summary:
                            summaries.append((filename, summary))
                            break
                    except Exception as e:
                        if attempt == max_retries - 1:  # 最后一次尝试
                            error_msg = f"处理文件 {filename} 失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
                            st.error(error_msg)
                            errors.append((filename, str(e)))
                        time.sleep(2)  # 失败后等待2秒再重试
                        
            except Exception as e:
                error_msg = f"处理文件 {filename} 时出错: {str(e)}"
                st.error(error_msg)
                errors.append((filename, str(e)))
    
    # 生成markdown格式的报告
    today = datetime.now().strftime("%Y%m%d")
    report = f"# 论文快报_{today}\n\n"
    
    if summaries:
        for i, (filename, summary) in enumerate(summaries, 1):
            report += f"## {i}. {filename}\n\n{summary}\n\n---\n\n"
    
    # 添加错误报告部分
    if errors:
        report += "\n## 处理失败的文件\n\n"
        for filename, error in errors:
            report += f"- {filename}: {error}\n"
    
    return report

# Streamlit 界面
st.title("论文快报生成器")

# 添加一个新的选项卡
tab1, tab2 = st.tabs(["论文总结", "论文抓取"])

with tab1:
    # 使用固定的文件夹路径
    folder_path = "pdf_folder"
    model_name = st.selectbox("选择模型", MODEL_OPTIONS)

    # 生成按钮
    if st.button("生成论文快报"):
        if not os.path.isdir(folder_path):
            st.error("请先创建pdf_folder文件夹")
        else:
            with st.spinner("正在生成论文快报..."):
                report = generate_daily_report(folder_path, model_name)
                
                # 显示报告
                st.markdown(report)
                
                # 添加下载按钮
                today = datetime.now().strftime("%Y%m%d")
                report_filename = f"论文快报_{today}.md"
                st.download_button(
                    label="下载论文快报",
                    data=report,
                    file_name=report_filename,
                    mime="text/markdown"
                )

with tab2:
    st.header("arxiv论文抓取")
    
    # 使用固定的CSV文件名
    csv_filename = "papers.csv"
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("开始抓取论文"):
            with st.spinner("正在从arxiv抓取论文..."):
                try:
                    downloaded_count = arxiv_pdf.fetch_papers(folder_path, csv_filename)
                    st.success(f"成功下载 {downloaded_count} 篇论文到 {folder_path} 文件夹")
                    st.info(f"论文信息已保存到 {csv_filename}")
                except Exception as e:
                    st.error(f"抓取论文时发生错误: {str(e)}")
    
    # 如果CSV文件存在，显示论文列表
    if os.path.exists(csv_filename):
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_filename)
            
            # 将Date列转换为datetime类型
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 获取所有可用的日期
            available_dates = df['Date'].dt.date.unique()
            
            with col2:
                # 添加日期选择器
                selected_date = st.selectbox(
                    "选择日期",
                    options=available_dates,
                    format_func=lambda x: x.strftime('%Y-%m-%d')
                )
            
            # 根据选择的日期筛选数据
            filtered_df = df[df['Date'].dt.date == selected_date]
            
            # 创建标题的超链接
            filtered_df['Title'] = filtered_df.apply(
                lambda x: f'<a href="{x["URL"]}" target="_blank">{x["Title"]}</a>', 
                axis=1
            )
            
            # 显示筛选后的数据表格，显示标题、作者、摘要和日期
            st.write(
                filtered_df[['Title', 'Authors', 'Abstract', 'Date']]
                .to_html(escape=False, index=False),
                unsafe_allow_html=True
            )
            
        except Exception as e:
            st.error(f"读取CSV文件时发生错误: {str(e)}")
