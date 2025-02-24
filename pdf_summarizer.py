import streamlit as st
import fitz
from openai import OpenAI
import argparse
import os
from datetime import datetime

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
    completion = client_openrouter.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "请为以下内容生成简洁明了的中文摘要，请你的摘要中包含以下几个关键点\n 1.整体内容, 2.主要贡献 3.实现方法 4.实验与评估结果\n 我只想让你输出摘要内容，不要回复我的任何话。"},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content

def generate_daily_report(pdf_folder, model_name):
    """生成每日论文快报"""
    summaries = []
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, filename)
            try:
                pdf_text = extract_text_from_pdf(pdf_path)
                summary = summarize_text(pdf_text, model_name)
                summaries.append((filename, summary))
            except Exception as e:
                st.error(f"处理文件 {filename} 时出错: {str(e)}")
    
    # 生成markdown格式的报告
    today = datetime.now().strftime("%Y%m%d")
    report = f"# 论文快报_{today}\n\n"
    
    for i, (filename, summary) in enumerate(summaries, 1):
        report += f"## {i}. {filename}\n\n{summary}\n\n---\n\n"
    
    return report

# Streamlit 界面
st.title("论文快报生成器")

folder_path = st.text_input("输入PDF文件夹路径", value="pdf_folder")
model_name = st.selectbox("选择模型", MODEL_OPTIONS)

# 显示文件夹状态
if os.path.isdir(folder_path):
    st.write("**文件夹已选择**：", folder_path)
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    st.write(f"发现 {len(pdf_files)} 个PDF文件")
    
    # 添加可滚动区域显示PDF文件列表
    with st.expander("查看PDF文件列表", expanded=True):
        pdf_files_text = "\n".join([f"{i+1}. {pdf}" for i, pdf in enumerate(pdf_files)])
        st.markdown(pdf_files_text)
else:
    st.error("请输入有效的文件夹路径")

# 生成按钮始终可见
if st.button("生成论文快报"):
    if not os.path.isdir(folder_path):
        st.error("请先选择有效的PDF文件夹")
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
