import requests
try: 
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup


def get_image(url, short_id, image_name):
    response = requests.get(url)
    print(url)
    soup = BeautifulSoup(response.content, "html.parser")
    for img in soup.find_all('img'):
        src = img.get("src")
        if src:
            # resolve any relative urls to absolute urls using base URL
            src = requests.compat.urljoin(url, src)
            src = src.replace("/html", f"/html/{short_id}")
            if src.endswith((".png", ".jpg")):
                suffix = src.split(".")[-1]
                with open(f"./images/{image_name}.{suffix}", "wb") as f:
                    f.write(requests.get(src).content)
                return True
    return False

if __name__ == "__main__":
    get_image("https://arxiv.org/html/2502.06786v2", "2502.06786v2")

