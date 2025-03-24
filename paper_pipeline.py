import os
import datetime as dt
import arxiv_pdf
import paper_affiliation_classifier
import affiliation_analyzer
import paper_assistant

def run_pipeline(csv_filename="papers.csv",
                pdf_folder="pdf_folder",
                query="cat:cs.AI", 
                author_filter=False,
                days_back=3,
                target_orgs=None):
    """
    运行完整的论文处理流水线
    
    参数:
        csv_filename: CSV文件名（保存在当前目录）
        pdf_folder: PDF文件保存文件夹
        query: arXiv查询字符串
        author_filter: 是否使用作者过滤
        days_back: 往前查询的天数
        target_orgs: 目标机构列表
        
    返回:
        下载的论文数量
    """
    try:
        # 创建PDF文件夹
        os.makedirs(pdf_folder, exist_ok=True)
        
        # 设置默认目标机构
        if target_orgs is None:
            target_orgs = [
                "Google", "Meta", "Microsoft", "OpenAI", 
                "Anthropic", "DeepMind", "Stanford", 
                "Alibaba", "Huawei", "Baidu", "Peking University"
            ]
        
        # 1. 设置日期范围
        end_date = dt.datetime.today()
        start_date = end_date - dt.timedelta(days=days_back)
        print(f"使用日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
        
        # 2. 使用arxiv_pdf模块获取论文列表
        print("第1步: 从arXiv获取论文列表...")
        papers_count = arxiv_pdf.fetch_papers(
            pdf_folder, 
            csv_filename=csv_filename,
            query=query,
            author_filter=author_filter,
            start_date=start_date,
            end_date=end_date
        )
        
        if papers_count == 0:
            print("没有找到符合条件的论文，流程终止")
            return 0
        
        print(f"成功获取{papers_count}篇论文信息")
        
        # 3. 使用paper_affiliation_classifier模块分类论文机构
        print("第2步: 模型分类论文机构...")
        classifier = paper_affiliation_classifier.PaperAffiliationClassifier()
        classifier.process_csv(csv_filename)
        print("论文机构分类完成")
        
        # 4. 使用affiliation_analyzer模块分析机构
        print("第3步: 模型筛选目标机构论文...")
        analyzer = affiliation_analyzer.AffiliationAnalyzer()
        indices_result = analyzer.process_csv(csv_filename, target_orgs)
        print(f"机构分析完成，找到的索引: {indices_result}")
        
        # 注意：我们不在这里下载论文，而是在Streamlit应用中处理
        # 这样可以避免重复下载
        
        # 6. 输出结果摘要
        print("=== 论文处理流水线完成 ===")
        print(f"- 获取论文数量: {papers_count}")
        
        return papers_count
        
    except Exception as e:
        print(f"论文处理流水线运行失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0

def main():
    """主函数"""
    # 直接调用流水线函数，使用默认参数
    run_pipeline()

if __name__ == "__main__":
    main() 