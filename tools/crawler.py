import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from .sele_crawler import crawl_by_selenium
from typing import Annotated
from pydantic import Field


def log_message(message: str):
    """로그 메시지를 log.txt 파일에 기록"""
    log_file_path = os.path.join(os.path.dirname(__file__), 'log.txt')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")


def crawl_category(category: Annotated[str, Field(description="The category of the keyword to be searched, information on the category, can be obtained from 'resource://category'")],
                   keywords: Annotated[str, Field(description="Keywords to search for (space-separated for multiple keywords)")]
                   ) -> str:
    """
    카테고리 크롤링 구현 (URL + Selenium 비동기 지원)
    공백으로 구분된 키워드들을 각각 검색하여 결과를 합침
    """
    sites_file_path = os.path.join(os.path.dirname(__file__), 'sites.json')
    with open(sites_file_path, 'r', encoding='utf-8') as f:
        sites_data = json.load(f)
    
    if category not in sites_data:
        category = "General"
        log_message(f"입력된 카테고리가 존재하지 않음, General로 변경")
    
    keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]
    log_message(f"크롤링 시작 - 카테고리: {category}, 키워드: {keyword_list}")
    
    all_results = {}
    for keyword in keyword_list:
        log_message(f"키워드 '{keyword}' 검색 시작")
        keyword_results = asyncio.run(_async_crawl_all_sites_hybrid(sites_data[category], keyword))
        
        for title, link in keyword_results.items():
            if title not in all_results:
                all_results[title] = link
        
        log_message(f"키워드 '{keyword}' 검색 완료 - {len(keyword_results)}개 기사 수집")
    
    log_message(f"전체 크롤링 완료 - 총 {len(all_results)}개 기사 수집 (키워드: {len(keyword_list)}개)")
    return json.dumps(all_results, ensure_ascii=False, indent=2)


async def _async_crawl_all_sites_hybrid(category_sites: dict, keywords: str) -> dict:
    """URL/셀레니움 비동기(다른 타입 간은 순차적 실행) 크롤링 구성"""
    result = {}
    
    # 사이트 타입별로 구분해서 info 로드
    url_sites = {}
    selenium_sites = {}
    
    for site_url, site_config in category_sites.items():
        site_type = site_config.get('type', 'url')
        if site_type == 'selenium':
            selenium_sites[site_url] = site_config
        else:
            url_sites[site_url] = site_config
    
    # URL 타입
    if url_sites:
        async with aiohttp.ClientSession() as session:
            url_tasks = []
            for site_url, site_config in url_sites.items():
                task = _crawl_single_site(session, site_url, site_config, keywords)
                url_tasks.append((site_url, task))
            
            for site_url, task in url_tasks:
                try:
                    site_result = await task
                    result.update(site_result)
                    log_message(f"{site_url} (url) 크롤링 완료 - {len(site_result)}개 기사 수집")
                except Exception as e:
                    log_message(f"{site_url} (url) 크롤링 중 오류 발생: {str(e)}")
    
    # Selenium 타입
    if selenium_sites:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=2) as executor:  # 최대 2개 브라우저 동시 실행
            selenium_tasks = []
            for site_url, site_config in selenium_sites.items():
                task = loop.run_in_executor(
                    executor, 
                    crawl_by_selenium, 
                    site_url, 
                    site_config, 
                    keywords
                )
                selenium_tasks.append((site_url, task))
            
            for site_url, task in selenium_tasks:
                try:
                    site_result = await task
                    result.update(site_result)
                    log_message(f"{site_url} (selenium) 크롤링 완료 - {len(site_result)}개 기사 수집")
                except Exception as e:
                    log_message(f"{site_url} (selenium) 크롤링 중 오류 발생: {str(e)}")
    
    return result


async def _crawl_single_site(session: aiohttp.ClientSession, site_url: str, site_config: dict, keywords: str) -> dict:
    """URL 타입에서 호출하는 각 사이트 크롤링"""
    results = {}
    log_message(f"크롤링 시작: {site_url}")
    
    if site_url.startswith('www.'):
        base_url = f"https://{site_url}"
    else:
        base_url = f"https://www.{site_url}"
    
    search_path = site_config.get('t_how', '')
    
    page_tasks = []
    for page in range(1, 6): # 5페이지 크롤링
        if page == 1:
            search_url = f"{base_url}{search_path}{keywords}"
        else:
            next_how = site_config.get('n_how', '')
            search_url = f"{base_url}{search_path}{keywords}{next_how}{page}"
        
        task = _crawl_single_page(session, site_url, search_url, site_config, page, base_url)
        page_tasks.append(task)
    
    page_results = await asyncio.gather(*page_tasks, return_exceptions=True)
    
    for page_result in page_results:
        if not isinstance(page_result, Exception):
            results.update(page_result)
    
    return results


async def _crawl_single_page(session: aiohttp.ClientSession, site_url: str, search_url: str, site_config: dict, page: int, base_url: str) -> dict:
    """사이트에서 개별 페이지 크롤링"""
    results = {}
    
    try:
        log_message(f"  {site_url} 페이지 {page}: {search_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        async with session.get(search_url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            content = await response.text()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        elem_config = site_config.get('elem', [])
        link_attr = site_config.get('link', 'href')
        
        if len(elem_config) >= 3:
            tag_name, attr_name, attr_value = elem_config[0], elem_config[1], elem_config[2]
            
            if attr_name and attr_value:
                elements = soup.find_all(tag_name, {attr_name: attr_value})
            else:
                elements = soup.find_all(tag_name)
            
            for element in elements:
                title = element.get_text(strip=True)
                if not title:
                    continue
                

                link = None
                if link_attr in element.attrs:
                    link = element.attrs[link_attr]
                elif element.find('a'):
                    link = element.find('a').get('href')
                elif element.name == 'a':
                    link = element.get('href')
                
                if link: #링크를 절대 경로로
                    if link.startswith('/'):
                        link = urljoin(base_url, link)
                    elif not link.startswith('http'):
                        link = urljoin(search_url, link)
                    
                    if title not in results:
                        results[title] = link
        
    except Exception as e:
        log_message(f"    {site_url} 페이지 {page} 크롤링 실패: {str(e)}")
    
    return results