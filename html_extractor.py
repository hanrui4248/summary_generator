from bs4 import BeautifulSoup
import requests


def get_image(short_id, image_dir="./images"):
    try:
        url = f"https://arxiv.org/html/{short_id}"
        response = requests.get(url)
        print(url)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 用于跟踪已下载的图片数量
        downloaded_count = 0
        
        for img in soup.find_all('img'):
            src = img.get("src")
            if src:
                try:
                    # resolve any relative urls to absolute urls using base URL
                    src = requests.compat.urljoin(url, src)
                    src = src.replace("/html", f"/html/{short_id}")
                    if src.endswith((".png", ".jpg")):
                        suffix = src.split(".")[-1]
                        file_path = f"{image_dir}/{short_id}_{downloaded_count}.{suffix}"
                        
                        # 检查图片是否已经存在
                        import os
                        if os.path.exists(file_path):
                            print(f"图片已存在: {file_path}")
                        else:
                            try:
                                with open(file_path, "wb") as f:
                                    img_response = requests.get(src)
                                    img_response.raise_for_status()
                                    f.write(img_response.content)
                                print(f"已下载图片: {file_path}")
                            except IOError as e:
                                print(f"保存图片时出错: {e}")
                                continue
                            except requests.exceptions.RequestException as e:
                                print(f"获取图片内容时出错: {e}")
                                continue
                        
                        downloaded_count += 1
                        
                        # 如果已经下载了两张图片，则返回
                        if downloaded_count >= 2:
                            return downloaded_count
                except Exception as e:
                    print(f"处理图片URL时出错: {e}")
                    continue
        
        return downloaded_count
    except requests.exceptions.RequestException as e:
        print(f"请求URL时出错: {e}")
        return 0
    except Exception as e:
        print(f"获取图片过程中出错: {e}")
        return 0


# def get_text_content(url, short_id=None, output_file=None):
#     """
#     从指定URL提取HTML页面的文本内容
    
#     参数:
#         url (str): 要提取内容的网页URL
#         short_id (str, 可选): 文章ID，用于处理相对URL
#         output_file (str, 可选): 保存提取文本的文件名，如果为None则只返回文本
        
#     返回:
#         str: 提取的文本内容
#     """
#     try:
#         response = requests.get(url)
#         response.raise_for_status()  # 检查请求是否成功
        
#         soup = BeautifulSoup(response.content, "html.parser")
        
#         # 移除脚本和样式元素
#         for script_or_style in soup(["script", "style"]):
#             script_or_style.extract()
            
#         # 获取文本内容
#         text = soup.get_text()
        
#         # 处理文本（去除多余空白行和空格）
#         lines = (line.strip() for line in text.splitlines())
#         chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
#         text = '\n'.join(chunk for chunk in chunks if chunk)
        
#         # 如果提供了输出文件名，则保存到文件
#         if output_file:
#             with open(output_file, "w", encoding="utf-8") as f:
#                 f.write(text)
                
#         return text
        
#     except Exception as e:
#         print(f"提取文本时出错: {e}")
#         return None


if __name__ == "__main__":
    get_image("2503.16203v1")
    #https://arxiv.org/abs/2503.16203v1
    #测试文本提取函数
    # text = get_text_content("https://arxiv.org/html/2502.04463v2", "2502.04463v2", "article_text.txt")
    # print(f"提取的文本长度: {len(text) if text else 0} 字符")


