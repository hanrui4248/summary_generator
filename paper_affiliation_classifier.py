import pandas as pd
import os
import logging
from openai import OpenAI
from tqdm import tqdm

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PaperAffiliationClassifier:
    def __init__(self, model="gpt-4o"):
        """
        初始化论文机构分类器
        
        参数:
            api_key: OpenAI API密钥，如果为None则从环境变量获取
            model: 使用的OpenAI模型名称
        """
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请提供OpenAI API密钥或设置OPENAI_API_KEY环境变量")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def classify_paper(self, content):
        """
        使用OpenAI模型判断论文属于哪个机构
        
        参数:
            content: 论文内容（第一页）
            
        返回:
            机构名称
        """
        # 构建提示
        prompt = f"""
        Based on the following paper content, determine the author affiliation(s) strictly from the listed author information, such as university, company, or research institution. Do not infer affiliations based on the models, tools, or datasets used in the paper (e.g., mentioning OpenAI or GPT does not mean OpenAI is an author affiliation).
        Please respond with only the organization name(s) from the author list, without any additional text. If author affiliations are not listed or are ambiguous, respond with "Unknown".
        Format your response as follows:
        ["Organization1", "Organization2", "Organization3", ...]
        """
        
        if not content:
            return "Error: No content provided"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"{content}"},
                ],       
                temperature=0.0
            )
            
            affiliation = response.choices[0].message.content.strip()
            return affiliation
        
        except Exception as e:
            logging.error(f"API调用失败: {str(e)}")
            return "Error"
    
    def process_csv(self, input_csv):
        """
        处理CSV文件，为每篇论文添加机构信息
        
        参数:
            input_csv: 输入CSV文件路径
            batch_size: 每次处理的批次大小，用于控制API请求频率
        """
        try:
            # 读取CSV文件
            df = pd.read_csv(input_csv)
            logging.info(f"成功读取CSV文件，共{len(df)}条记录")
            
            # 添加机构列
            if "Affiliation" not in df.columns:
                df["Affiliation"] = ""
            
            # 处理每篇论文
            for i in tqdm(range(0, len(df)), desc="处理论文"):
                # 如果已经有机构信息，跳过
                if df.at[i, "Affiliation"] and df.at[i, "Affiliation"] != "Error":
                    continue
                
                # 获取论文信息
                content = df.at[i, "Content"]
                
                # 分类论文
                affiliation = self.classify_paper(content)
                df.at[i, "Affiliation"] = affiliation
                
                # 直接保存到原文件
                df.to_csv(input_csv, index=False)
            
            # # 统计各机构论文数量
            # affiliation_counts = df["Affiliation"].value_counts()
            # logging.info("各机构论文数量统计:")
            # for affiliation, count in affiliation_counts.items():
            #     logging.info(f"{affiliation}: {count}篇")
            
            return input_csv
            
        except Exception as e:
            logging.error(f"处理CSV文件失败: {str(e)}")
            raise

def main():
    classifier = PaperAffiliationClassifier()
    classifier.process_csv("test.csv")

if __name__ == "__main__":
    main() 