from bs4 import BeautifulSoup
from typing import Dict
import mcp

@mcp.tool()
def find_keyword(
    html_uri: str,
    keyword: str,
    max_results: int = 5
) -> Dict:
    """
    HTML 콘텐츠에서 기후 변화 관련 질문에 응답할 수 있는 문단을 탐색하여 추출합니다.
    
    Parameters:
    -----------
    html_uri : str
        분석할 HTML 내용 문자열
    keyword : str
        응답하려는 질문의 핵심 키워드
    max_results : int
        반환할 최대 태그뭉치 개수수
    
    Returns:
    --------
    Dict
        탐색한 웹페이지의 제목과, 키워드를 포함한 내용을 담은 Dictionary
        - 'title': 웹페이지의 제목
        - 'evidence_paragraphs': 키워드를 포함하는 태그
        - 'query': 사용된 질문/키워드
    """
    result = {
        "title": "",
        "evidence_paragraphs": [],
        "keyword": keyword
    }
    with open(html_uri, 'r', encoding='utf-8') as docs:
        soup = BeautifulSoup(docs, "lxml")
        
        #탐색 웹 제목
        page_title = soup.title.string if soup.title else ""
        result["title"] = page_title

        keywords = keyword.lower().split()
        paragraphs = soup.find_all("title")
        
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text and any(keyword in text.lower() for keyword in keywords):
                if len(result["evidence_paragraphs"]) < max_results:
                    result["evidence_paragraphs"].append(text)
    
    return result