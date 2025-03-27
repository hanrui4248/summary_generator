import pandas as pd
import os
import logging
import json
from openai import OpenAI
from orgs import orgs
# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AffiliationAnalyzer:
    def __init__(self, model="gpt-4o"):
        """
        初始化机构分析器
        
        参数:
            model: 使用的OpenAI模型名称
        """
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请提供OpenAI API密钥或设置OPENAI_API_KEY环境变量")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def concatenate_affiliations(self, csv_path):
        """
        将CSV文件中的机构字段拼接成字符串
        
        参数:
            csv_path: CSV文件路径
            
        返回:
            拼接后的字符串
        """
        try:
            # 读取CSV文件
            df = pd.read_csv(csv_path)
            logging.info(f"成功读取CSV文件，共{len(df)}条记录")
            
            # 检查是否存在Affiliation列
            if "Affiliation" not in df.columns:
                raise ValueError("CSV文件中不存在Affiliation列")
            
            # 拼接机构字段
            result = ""
            for i, row in enumerate(df.itertuples()):
                affiliation = getattr(row, "Affiliation", "")
                if affiliation and affiliation != "Error":
                    result += f"{i}.{affiliation}\n"
            
            return result
        
        except Exception as e:
            logging.error(f"拼接机构字段失败: {str(e)}")
            raise
    
    def analyze_affiliations(self, concatenated_str, target_orgs):
        """
        分析拼接后的机构字符串，找出包含目标机构的索引
        
        参数:
            concatenated_str: 拼接后的机构字符串
            target_orgs: 目标机构列表
            
        返回:
            包含目标机构的索引列表
        """
        if not concatenated_str:
            logging.warning("拼接字符串为空")
            return []
        
        # 构建初始提示
        initial_prompt = f"""
        I have a list containing paper affiliation information in the following format:
        
        {concatenated_str}
        
        Please carefully analyze this list and identify the paper indices that contain any of the following organizations:
        {target_orgs}
        
        Please return the results in the following format:
        [index1, index2, ...]
        
        Return only the results in list format, without any additional text.
        """
        
        try:
            # 第一轮分析
            initial_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的数据分析助手，擅长从文本中提取和分析信息。"},
                    {"role": "user", "content": initial_prompt}
                ],
                temperature=0.0
            )
            
            initial_result = initial_response.choices[0].message.content.strip()
            
            # 构建验证提示
            verification_prompt = f"""
            I previously asked you to analyze the following affiliation information and identify indices containing specific organizations:
            
            {concatenated_str}
            
            Target organizations are:
            {target_orgs}
            
            Your response was:
            {initial_result}
            
            Please carefully verify your answer for correctness. Ensure you haven't missed any matches and haven't included any indices that shouldn't be in the list.
            If corrections are needed, provide an updated list of indices in the format [index1, index2, ...]
            Return only the final list of indices, without any additional text.
            """
            
            # 第二轮验证
            verification_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的数据分析助手，擅长从文本中提取和分析信息。"},
                    {"role": "user", "content": initial_prompt},
                    {"role": "assistant", "content": initial_result},
                    {"role": "user", "content": verification_prompt}
                ],
                temperature=0.0
            )
            
            final_result = verification_response.choices[0].message.content.strip()
            logging.info("完成两轮分析验证")
            
            # 解析结果字符串为数组
            try:
                indices = json.loads(final_result.replace("'", "\""))
                if not isinstance(indices, list):
                    raise ValueError("索引必须是列表格式")
                return indices
            except json.JSONDecodeError:
                # 尝试使用eval解析（不推荐，但作为备选）
                try:
                    indices = eval(final_result)
                    if isinstance(indices, list):
                        return indices
                    else:
                        logging.error("解析结果不是列表格式")
                        return []
                except:
                    logging.error(f"无法解析结果: {final_result}")
                    return []
        
        except Exception as e:
            logging.error(f"分析机构失败: {str(e)}")
            return []
    
    def process_csv(self, csv_path, target_orgs):
        """
        处理CSV文件，分析机构信息
        
        参数:
            csv_path: CSV文件路径
            target_orgs: 目标机构列表
            
        返回:
            分析结果（索引数组）
        """
        try:
            # 拼接机构字段
            concatenated_str = self.concatenate_affiliations(csv_path)
            logging.info("成功拼接机构字段")
            print(concatenated_str)
            # 分析机构
            result = self.analyze_affiliations(concatenated_str, target_orgs)
            logging.info("成功分析机构")
            print("分析结果:")
            print(result)
            return result
        
        except Exception as e:
            logging.error(f"处理CSV文件失败: {str(e)}")
            raise

def main():
    # 目标机构列表
    analyzer = AffiliationAnalyzer()
    result = analyzer.process_csv("test.csv", orgs)
    
    print("分析结果:")
    print(result)
    
    

if __name__ == "__main__":
    main() 