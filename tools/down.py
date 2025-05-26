import requests
from urllib.parse import urlparse
from datetime import datetime

def download_html(url: str) -> str:
    response = requests.get(url)

    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{domain}_{timestamp}.html"

    if response.status_code == 200:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        return filename; # 성공
    else:
        return '0'; # 실패\

if __name__ == "__main__":
    url = "https://www.reuters.com/site-search/?query=technology"
    download_html(url)
