import pandas as pd
import os
import logging
import json
from openai import OpenAI
from tqdm import tqdm
import concurrent.futures

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AbstractMatcher:
    def __init__(self, model="gpt-4o"):
        """
        初始化摘要匹配器
        
        参数:
            model: 使用的OpenAI模型名称
        """
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请提供OpenAI API密钥或设置OPENAI_API_KEY环境变量")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def load_abstracts(self, csv_path):
        """
        从CSV文件中加载摘要
        
        参数:
            csv_path: CSV文件路径
            
        返回:
            包含索引和摘要的字典
        """
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_path)
            logging.info(f"成功读取CSV文件，共{len(df)}条记录")
            
            # 检查是否存在Abstract列
            if "Abstract" not in df.columns:
                raise ValueError("CSV文件中不存在Abstract列")
            
            # 创建索引-摘要字典
            abstracts_dict = {}
            for i, row in enumerate(df.itertuples()):
                abstract = getattr(row, "Abstract", "")
                if abstract and abstract != "Error":
                    abstracts_dict[i] = abstract
            
            logging.info(f"成功加载{len(abstracts_dict)}条有效摘要")
            return abstracts_dict
        
        except Exception as e:
            logging.error(f"加载摘要失败: {str(e)}")
            raise
    
    def match_single_abstract(self, index, abstract, query):
        """
        判断单个摘要是否与查询匹配
        
        参数:
            index: 摘要索引
            abstract: 摘要内容
            query: 用户查询
        返回:
            如果匹配返回索引，否则返回None
        """
        prompt = f"""
        请分析以下论文摘要是否与用户查询相关:
        
        摘要: {abstract}
        
        用户查询: "{query}"
        
        如果摘要与查询相关，请回答"是"；如果不相关，请回答"否"。
        只返回"是"或"否"，不要添加任何额外文本。
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            result = response.choices[0].message.content.strip().lower()
            
            if "是" in result or "yes" in result:
                return index
            else:
                return None
        
        except Exception as e:
            logging.error(f"匹配摘要 {index} 失败: {str(e)}")
            return None
    
    def process_csv(self, csv_path, query, max_workers=5):
        """
        处理CSV文件，匹配摘要信息
        
        参数:
            csv_path: CSV文件路径
            query: 用户查询
            max_workers: 并行处理的最大工作线程数
            
        返回:
            匹配结果（索引数组）
        """
        try:
            # 加载摘要
            abstracts_dict = self.load_abstracts(csv_path)
            
            # 使用线程池并行处理摘要
            matched_indices = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 创建未来任务
                future_to_index = {
                    executor.submit(
                        self.match_single_abstract, 
                        index, 
                        abstract, 
                        query
                    ): index 
                    for index, abstract in abstracts_dict.items()
                }
                
                # 处理完成的任务
                for future in tqdm(concurrent.futures.as_completed(future_to_index), 
                                  total=len(abstracts_dict), 
                                  desc="匹配摘要"):
                    result = future.result()
                    if result is not None:
                        matched_indices.append(result)
            
            logging.info(f"成功匹配摘要，找到{len(matched_indices)}条匹配结果")
            return sorted(matched_indices)
        
        except Exception as e:
            logging.error(f"处理CSV文件失败: {str(e)}")
            raise

def main():
    # 示例用法
    matcher = AbstractMatcher()
    
    # 用户查询
    query = "机器人"
    
    # CSV文件路径
    csv_path = "papers.csv"
    
    # 处理CSV文件
    result = matcher.process_csv(csv_path, query, max_workers=5)
    
    print("匹配结果索引:")
    print(result)
    
    # 读取原始CSV文件以获取匹配的摘要
    try:
        df = pd.read_csv(csv_path)
        print("\n匹配的摘要内容:")
        for idx in result:
            # 确保索引在DataFrame的范围内
            if 0 <= idx < len(df):
                print(f"\n索引 {idx}:")
                print(df.iloc[idx]["Abstract"])
            else:
                print(f"\n索引 {idx}: 超出范围，无法获取摘要")
    except Exception as e:
        print(f"读取摘要时出错: {str(e)}")

if __name__ == "__main__":
    main() 