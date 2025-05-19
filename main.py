from fastmcp import FastMCP
from bs4 import BeautifulSoup
import requests
import json
import os
import hashlib
import datetime
from typing import List, Dict, Optional

import analyzer.keyword

# FastMCP 서버 초기화
mcp = FastMCP(
    name="ClimateChangeEvidenceFinder",
    instructions="""
    이 서버는 기후 변화에 관한 의문점을 해결하기 위한 웹 기반 증거를 찾는 도구를 제공합니다.
    다음 도구들을 사용하여 기후 변화에 관한 정보를 검색하고 분석할 수 있습니다:
    
    1. html_analyzer: HTML 파일을 분석하여 특정 태그나 텍스트를 추출
    2. climate_domain_crawler: 미리 정의된 기후 변화 관련 도메인에서 정보 크롤링
    3. custom_url_crawler: 직접 지정한 URL에서 정보 크롤링
    4. extract_climate_evidence: HTML 콘텐츠에서 기후 변화 관련 질문에 대한 증거를 추출
    5. search_based_crawler: 웹사이트의 검색 기능을 활용하여 키워드 검색 결과를 크롤링
    
    중요: crawler 도구나 extract_climate_evidence 도구를 사용할 때는 해당 웹페이지의 언어에 맞게 LLM이 키워드를 자동으로 번역해서 사용해야 합니다. search_based_crawler의 경우 language 파라미터를 통해 검색 언어를 지정할 수 있습니다.
    
    지원되는 기후 변화 분야: "탄소배출", "전기차", "해수면상승", "기온", "생태계"
    
    이 서비스는 기후 변화 관련 웹사이트에서 과학적 증거를 수집하고 분석하여 신뢰할 수 있는 정보를 제공합니다.
    """
)

# 리소스 저장 디렉토리 설정
RESOURCE_DIR = "./resource"
# 디렉토리가 없으면 생성
if not os.path.exists(RESOURCE_DIR):
    os.makedirs(RESOURCE_DIR)

# 기후 변화 관련 도메인을 정의
CLIMATE_DOMAINS = {
    "탄소배출": [
        "https://www.ipcc.ch/",
        "https://www.epa.gov/ghgemissions",
        "https://www.carbonbrief.org/"
    ],
    "전기차": [
        "https://www.iea.org/topics/transport",
        "https://www.ev-volumes.com/",
        "https://cleantechnica.com/"
    ],
    "해수면상승": [
        "https://sealevel.nasa.gov/",
        "https://www.climate.gov/news-features/understanding-climate/climate-change-global-sea-level",
        "https://ocean.si.edu/through-time/ancient-seas/sea-level-rise"
    ],
    "기온": [
        "https://climate.nasa.gov/vital-signs/global-temperature/",
        "https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-monthly",
        "https://data.giss.nasa.gov/gistemp/"
    ],
    "생태계": [
        "https://www.iucn.org/our-work/topic/climate-change",
        "https://www.worldwildlife.org/threats/effects-of-climate-change",
        "https://www.nationalgeographic.com/environment/article/climate-change"
    ]
}

@mcp.tool()
def html_analyzer(
    html_content: str,
    tag_name: Optional[str] = None,
    class_name: Optional[str] = None,
    id_name: Optional[str] = None,
    extract_links: bool = False,
    extract_text_only: bool = False
) -> Dict:
    """
    HTML 콘텐츠를 분석하여 특정 태그나 텍스트를 추출합니다.
    
    Parameters:
    -----------
    html_content : str
        분석할 HTML 내용 문자열
    tag_name : Optional[str]
        검색할 HTML 태그 이름 (예: 'div', 'p', 'a')
    class_name : Optional[str]
        검색할 HTML 클래스 이름
    id_name : Optional[str]
        검색할 HTML ID 이름
    extract_links : bool
        True인 경우 모든 링크(<a> 태그)를 추출합니다
    extract_text_only : bool
        True인 경우 HTML에서 텍스트만 추출합니다
    
    Returns:
    --------
    Dict
        분석 결과를 포함하는 사전
        - 'text': 전체 텍스트 (extract_text_only=True인 경우)
        - 'links': 모든 링크 목록 (extract_links=True인 경우)
        - 'elements': 검색 조건에 맞는 요소 목록
    """
    result = {}
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 텍스트만 추출
    if extract_text_only:
        result['text'] = soup.get_text(strip=True)
    
    # 링크 추출
    if extract_links:
        links = []
        for a in soup.find_all('a', href=True):
            links.append({
                'text': a.get_text(strip=True),
                'href': a['href']
            })
        result['links'] = links
    
    # 특정 태그 검색
    if any([tag_name, class_name, id_name]):
        elements = []
        kwargs = {}
        if class_name:
            kwargs['class_'] = class_name
        if id_name:
            kwargs['id'] = id_name
            
        for element in soup.find_all(tag_name, **kwargs):
            elements.append({
                'text': element.get_text(strip=True),
                'html': str(element)
            })
        result['elements'] = elements
    
    return result

@mcp.tool()
def climate_domain_crawler(
    category: str,
    keywords: List[str],
    max_pages: int = 5
) -> Dict:
    """
    미리 정의된 기후 변화 관련 도메인에서 정보를 크롤링합니다.
    
    Parameters:
    -----------
    category : str
        크롤링할 기후 변화 분야 ("탄소배출", "전기차", "해수면상승", "기온", "생태계" 중 하나)
    keywords : List[str]
        검색할 키워드 목록
    max_pages : int
        크롤링할 최대 페이지 수 (기본값: 5)
    
    Returns:
    --------
    Dict
        크롤링 결과를 포함하는 사전
        - 'urls': 크롤링된 URL 목록
        - 'file_paths': HTML이 저장된 파일 경로 목록
        - 'category': 사용된 카테고리
        - 'keywords': 사용된 키워드
    """
    if category not in CLIMATE_DOMAINS:
        return {
            "error": f"지원되지 않는 카테고리입니다. 지원되는 카테고리: {', '.join(CLIMATE_DOMAINS.keys())}"
        }
    
    results = {
        "urls": [],
        "file_paths": [],
        "category": category,
        "keywords": keywords
    }
    
    # 간단한 웹 크롤링 구현 (Scrapy 대신 requests 사용)
    domains = CLIMATE_DOMAINS[category]
    pages_crawled = 0
    
    for domain in domains:
        if pages_crawled >= max_pages:
            break
            
        try:
            response = requests.get(domain, timeout=10)
            if response.status_code == 200:
                html_content = response.text
                
                # 키워드 기반 필터링
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text().lower()
                
                # 키워드 매칭 확인
                if any(keyword.lower() in text_content for keyword in keywords):
                    # HTML 파일 저장
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    domain_hash = hashlib.md5(domain.encode()).hexdigest()[:8]
                    filename = f"{RESOURCE_DIR}/climate_{category}_{domain_hash}_{timestamp}.html"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    results["urls"].append(domain)
                    results["file_paths"].append(filename)
                    pages_crawled += 1
        except Exception as e:
            continue
    
    return results

@mcp.tool()
def custom_url_crawler(
    start_url: str,
    keywords: List[str],
    max_pages: int = 5,
    follow_links: bool = True
) -> Dict:
    """
    사용자가 지정한 URL에서 시작하여 정보를 크롤링합니다.
    
    Parameters:
    -----------
    start_url : str
        크롤링을 시작할 URL
    keywords : List[str]
        검색할 키워드 목록
    max_pages : int
        크롤링할 최대 페이지 수 (기본값: 5)
    follow_links : bool
        True인 경우 페이지 내 링크를 따라 크롤링합니다 (기본값: True)
    
    Returns:
    --------
    Dict
        크롤링 결과를 포함하는 사전
        - 'urls': 크롤링된 URL 목록
        - 'file_paths': HTML이 저장된 파일 경로 목록
        - 'keywords': 사용된 키워드
    """
    results = {
        "urls": [],
        "file_paths": [],
        "keywords": keywords
    }
    
    # 크롤링 구현 (Scrapy 대신 requests 사용)
    pages_crawled = 0
    urls_to_visit = [start_url]
    visited_urls = set()
    
    while urls_to_visit and pages_crawled < max_pages:
        current_url = urls_to_visit.pop(0)
        
        if current_url in visited_urls:
            continue
            
        visited_urls.add(current_url)
        
        try:
            response = requests.get(current_url, timeout=10)
            if response.status_code == 200:
                html_content = response.text
                
                # 키워드 기반 필터링
                soup = BeautifulSoup(html_content, 'html.parser')
                text_content = soup.get_text().lower()
                
                # 키워드 매칭 확인
                if any(keyword.lower() in text_content for keyword in keywords):
                    # HTML 파일 저장
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    url_hash = hashlib.md5(current_url.encode()).hexdigest()[:8]
                    filename = f"{RESOURCE_DIR}/custom_{url_hash}_{timestamp}.html"
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    results["urls"].append(current_url)
                    results["file_paths"].append(filename)
                    pages_crawled += 1
                
                # 다음 링크 추가
                if follow_links:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        # 상대 URL을 절대 URL로 변환
                        if href.startswith('/'):
                            from urllib.parse import urlparse
                            parsed_url = urlparse(current_url)
                            next_url = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
                        elif href.startswith('http'):
                            next_url = href
                        else:
                            continue
                            
                        if next_url not in visited_urls and next_url not in urls_to_visit:
                            urls_to_visit.append(next_url)
        except Exception as e:
            continue
    
    return results

@mcp.resource("resource://categories")
def get_supported_climate_categories() -> List[str]:
    """
    지원되는 기후 변화 카테고리 목록을 반환합니다.
    
    Returns:
    --------
    List[str]
        지원되는 모든 기후 변화 카테고리 목록
    """
    return list(CLIMATE_DOMAINS.keys())


@mcp.tool()
def search_based_crawler(
    base_url: str,
    keywords: List[str],
    max_results: int = 10,
    language: str = "ko"  # 기본값은 한국어
) -> Dict:
    """
    웹사이트의 검색 기능을 활용하여 키워드 검색 결과를 크롤링합니다.
    
    Parameters:
    -----------
    base_url : str
        검색할 웹사이트의 기본 URL (예: 'https://www.ipcc.ch')
    keywords : List[str]
        검색할 키워드 목록
    max_results : int
        수집할 최대 결과 수 (기본값: 10)
    language : str
        검색에 사용할 언어 코드 (기본값: 'ko', 'en'도 가능)
    
    Returns:
    --------
    Dict
        검색 결과를 포함하는 사전
        - 'search_results': 각 키워드별 검색 결과 목록 (URL, 제목, 저장된 파일 경로 포함)
        - 'base_url': 검색한 웹사이트
        - 'keywords': 사용된 키워드
        - 'search_method': 각 키워드별 사용된 검색 방법 ('exact': 정확한 검색 결과, 'fallback': 대체 방법)
    """
    results = {
        "search_results": {},
        "base_url": base_url,
        "keywords": keywords,
        "search_method": {}  # 검색 방법을 저장할 새 필드
    }
    
    # 웹사이트별 검색 URL 패턴 정의 (CLIMATE_DOMAINS에 있는 모든 도메인 포함)
    search_patterns = {
        # 일반적인 검색 패턴
        "default": "{base_url}/search?q={query}",
        
        # 사전 정의된 도메인별 검색 패턴
        # 탄소배출 관련 사이트
        "ipcc.ch": "{base_url}/search?query={query}",
        "epa.gov": "{base_url}/search/site/{query}",
        "carbonbrief.org": "{base_url}/?s={query}",
        
        # 전기차 관련 사이트
        "iea.org": "{base_url}/search?keywords={query}",
        "ev-volumes.com": "{base_url}/search/?q={query}",
        "cleantechnica.com": "{base_url}/?s={query}",
        
        # 해수면상승 관련 사이트
        "sealevel.nasa.gov": "{base_url}/search?search_api_fulltext={query}",
        "climate.gov": "{base_url}/search/content/{query}",
        "ocean.si.edu": "{base_url}/search?edan_q={query}",
        
        # 기온 관련 사이트
        "climate.nasa.gov": "{base_url}/search?q={query}",
        "ncei.noaa.gov": "{base_url}/search?q={query}",
        "data.giss.nasa.gov": "https://search.nasa.gov/search?query={query}&affiliate=nasa",
        
        # 생태계 관련 사이트
        "iucn.org": "{base_url}/search?key={query}",
        "worldwildlife.org": "{base_url}/search?query={query}",
        "nationalgeographic.com": "{base_url}/search?q={query}"
    }
    
    # 일부 사이트는 언어 파라미터를 지원합니다
    language_supported_sites = [
        "ipcc.ch", "iucn.org", "iea.org", "climate.gov"
    ]
    
    # 언어 코드 매핑
    lang_codes = {
        "ko": "ko",
        "en": "en",
        "fr": "fr",
        "es": "es",
        "zh": "zh",
        "ja": "ja"
    }
    
    lang = lang_codes.get(language, "en")
    
    for keyword in keywords:
        results["search_results"][keyword] = []
        
        # 웹사이트 도메인에 맞는 검색 패턴 선택
        domain = base_url.split("//")[-1].split("/")[0].replace("www.", "")
        pattern_key = next((k for k in search_patterns.keys() if k in domain), "default")
        search_pattern = search_patterns[pattern_key]
        
        # 검색 URL 생성
        query = keyword.replace(" ", "+")
        search_url = search_pattern.format(base_url=base_url, query=query)
        
        # 언어 지원 사이트인 경우 언어 파라미터 추가
        if any(site in domain for site in language_supported_sites):
            if "?" in search_url:
                search_url += f"&lang={lang}"
            else:
                search_url += f"?lang={lang}"
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 검색 결과 링크 추출 - 웹사이트마다 선택자가 다를 수 있음
                search_results = []
                
                # 일반적인 검색 결과 선택자들
                selectors = [
                    # 일반적인 검색 결과 컨테이너
                    "div.search-results a", ".search-result a", "article.search-result a",
                    "div.result a", "article.result a", "div.results a", "article.results a",
                    
                    # 검색 결과 리스트
                    "ul.search-results li a", "ol.search-results li a", 
                    "ul.results li a", "ol.results li a",
                    
                    # 특정 사이트별 선택자
                    ".ipcc-search-results a", ".nasa-search-results a", 
                    ".search-listing a", ".searchResults a", ".search-content a",
                    
                    # 폴백 선택자 - 컨텐츠 영역의 링크
                    "main a", "#content a", "#main-content a", ".content a", 
                    ".main-content a", "article a"
                ]
                
                # 각 선택자 시도
                for selector in selectors:
                    links = soup.select(selector)
                    if links:
                        for link in links[:max_results]:
                            href = link.get('href', '')
                            title = link.get_text(strip=True)
                            
                            # 빈 링크나 자바스크립트 링크 건너뛰기
                            if not href or href.startswith(('javascript:', '#')):
                                continue
                                
                            # 상대 URL을 절대 URL로 변환
                            if href.startswith('/'):
                                href = base_url.rstrip('/') + href
                            elif not href.startswith(('http://', 'https://')):
                                # 상대 경로를 base_url에 추가
                                href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                            
                            # 중복 방지
                            if any(r['url'] == href for r in search_results):
                                continue
                                
                            if title and len(title.strip()) > 0:
                                search_results.append({
                                    'title': title,
                                    'url': href
                                })
                        
                        # 충분한 결과를 찾았으면 선택자 루프 종료
                        if len(search_results) >= max_results:
                            # 정확한 검색 방법으로 찾았음을 표시
                            results["search_method"][keyword] = "exact"
                            break
                
                # 선택자로 찾지 못한 경우 대안 방법 - 키워드가 포함된 모든 링크 추출
                if not search_results:
                    # 폴백 방법으로 찾고 있음을 표시
                    results["search_method"][keyword] = "fallback"
                    
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # 빈 링크나 자바스크립트 링크 건너뛰기
                        if not href or href.startswith(('javascript:', '#')):
                            continue
                            
                        # 키워드가 링크 텍스트에 포함된 경우만 추출
                        if keyword.lower() in text.lower() and len(text) > 3:
                            # 상대 URL을 절대 URL로 변환
                            if href.startswith('/'):
                                href = base_url.rstrip('/') + href
                            elif not href.startswith(('http://', 'https://')):
                                href = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                            
                            # 중복 방지
                            if any(r['url'] == href for r in search_results):
                                continue
                                
                            search_results.append({
                                'title': text,
                                'url': href
                            })
                            
                            if len(search_results) >= max_results:
                                break
                
                # 결과에 검색 결과 추가
                # 검색 결과가 있는 페이지도 저장
                if search_results:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    domain_hash = hashlib.md5(base_url.encode()).hexdigest()[:8]
                    search_filename = f"{RESOURCE_DIR}/search_{domain_hash}_{keyword.replace(' ', '_')}_{timestamp}.html"
                    
                    with open(search_filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                
                    # 개별 검색 결과 페이지도 크롤링하여 저장
                    for result in search_results:
                        try:
                            result_url = result['url']
                            result_response = requests.get(result_url, headers=headers, timeout=10)
                            if result_response.status_code == 200:
                                # 파일 저장
                                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                                url_hash = hashlib.md5(result_url.encode()).hexdigest()[:8]
                                filename = f"{RESOURCE_DIR}/result_{domain_hash}_{url_hash}_{timestamp}.html"
                                
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(result_response.text)
                                
                                # 파일 경로 추가
                                result['file_path'] = filename
                        except Exception as e:
                            # 개별 결과 페이지 크롤링 실패시 무시
                            result['file_path'] = None
                            continue
                    
                    results["search_results"][keyword] = search_results
                    
                    # 검색 방법에 대한 설명 추가
                    search_method = results["search_method"].get(keyword, "unknown")
                    if search_method == "exact":
                        results.setdefault("descriptions", {})[keyword] = "웹사이트의 검색 결과 영역에서 정확하게 추출된 검색 결과입니다."
                    else:  # fallback
                        results.setdefault("descriptions", {})[keyword] = "웹사이트의 검색 결과 영역을 찾지 못해 페이지 내 키워드 관련 링크로 대체했습니다."
                else:
                    # 검색 결과가 없는 경우
                    results["search_results"][keyword] = []
                    results["search_method"][keyword] = "failed"
                    results.setdefault("descriptions", {})[keyword] = "검색 결과를 찾지 못했습니다."
                
                # 디버그 정보 추가 (실제 사용시 제거 가능)
                results["debug"] = {
                    "search_url": search_url,
                    "found_results": len(search_results)
                }
                
        except Exception as e:
            # 에러 정보 추가 (실제 사용시 제거 가능)
            if "search_results" not in results:
                results["search_results"] = {}
            if keyword not in results["search_results"]:
                results["search_results"][keyword] = []
            
            # 오류 발생 시 검색 방법 표시
            results["search_method"][keyword] = "error"
            results.setdefault("descriptions", {})[keyword] = f"검색 중 오류가 발생했습니다: {str(e)[:100]}"
            
            results["errors"] = {
                "message": str(e),
                "search_url": search_url
            }
            continue
    
    return results

if __name__ == "__main__":
    mcp.run()