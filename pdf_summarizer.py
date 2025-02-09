import streamlit as st
import fitz
from openai import OpenAI
import argparse

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

def extract_text_from_pdf(pdf_file):
    """从 PDF 文件中提取文本"""
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            text += page.get_text("text") + "\n"
    return text

def summarize_text(text, model_name):
    """使用 OpenAI API 生成摘要"""
    completion = client_openrouter.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "你是一个专业的文档摘要助手，请为以下内容生成简洁明了的中文摘要，并且需要包括以下几个核心点:\n 1.整体内容, 2.主要贡献 3.实现方法 4.实验与评估结果"},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content

# Streamlit 界面
st.title("PDF 摘要生成器")

uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
model_name = st.selectbox("选择模型", MODEL_OPTIONS)

if uploaded_file is not None:
    st.write("**文件已上传**：", uploaded_file.name)
    if st.button("生成摘要"):
        with st.spinner("正在生成摘要..."):
            pdf_text = extract_text_from_pdf(uploaded_file)
            summary = summarize_text(pdf_text, model_name)
            st.subheader("📄 生成的摘要：")
            st.write(summary)
