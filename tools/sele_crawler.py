from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
from datetime import datetime
from urllib.parse import urljoin


def log_message(message: str):
    """로그를 log.txt에 기록"""
    log_file_path = os.path.join(os.path.dirname(__file__), 'log.txt')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")


def crawl_by_selenium(site_url: str, site_config: dict, keywords: str) -> dict:
    """
    셀레니움을 사용한 크롤링
    (현재 클릭인 경우만 존재)
    """
    results = {}
    
    # Chrome 옵션 설정 (성능 최적화)
    options = webdriver.ChromeOptions()
    
    # 기본 헤드리스 설정
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5) 
        
        log_message(f"Selenium 크롤링 시작: {site_url}")
        
        if site_url.startswith('www.'):
            base_url = f"https://{site_url}"
        else:
            base_url = f"https://www.{site_url}"
        
        search_path = site_config.get('t_how', '')
        search_url = f"{base_url}{search_path}{keywords}"
        
        log_message(f"  검색 URL: {search_url}")
        
        driver.get(search_url)
        time.sleep(2)  
        
        # 최대 3페이지까지만 크롤링
        for page in range(1, 4):
            log_message(f"  페이지 {page} 크롤링 중...")
            
            page_results = extract_articles_from_page(driver, site_config, base_url)
            results.update(page_results)
            
            log_message(f"  페이지 {page}에서 {len(page_results)}개 기사 수집")
            
            if page < 3:
                if not go_to_next_page(driver, site_config):
                    log_message(f"  다음 페이지 버튼을 찾을 수 없음. 크롤링 종료")
                    break
                time.sleep(1)  # 페이지 로딩 대기 시간 단축
        
    except Exception as e:
        log_message(f"Selenium 크롤링 중 오류 발생: {str(e)}")
    
    finally:
        if driver:
            driver.quit()
    
    return results


def extract_articles_from_page(driver, site_config: dict, base_url: str) -> dict:
    """현재 페이지에서 기사 제목과 링크 추출"""
    results = {}
    
    try:
        elem_config = site_config.get('elem', [])
        link_attr = site_config.get('link', 'href')
        
        if len(elem_config) >= 3:
            tag_name, attr_name, attr_value = elem_config[0], elem_config[1], elem_config[2]
            
            if attr_name == 'class':
                css_selector = f"{tag_name}.{attr_value.replace(' ', '.')}"
            elif attr_name == 'data-testid':
                css_selector = f"{tag_name}[data-testid='{attr_value}']"
            else:
                css_selector = f"{tag_name}[{attr_name}='{attr_value}']"
            
            elements = driver.find_elements(By.CSS_SELECTOR, css_selector)
            
            for element in elements:
                try:
                    title = element.text.strip()
                    if not title:
                        continue
                    
                    link = None
                    try:
                        if link_attr in ['href', 'data-zjs-href']:
                            link = element.get_attribute(link_attr)
                        
                        if not link:
                            parent_link = element.find_element(By.XPATH, "./ancestor::a[1]")
                            if parent_link:
                                link = parent_link.get_attribute('href')
                        
                        if not link:
                            child_link = element.find_element(By.TAG_NAME, "a")
                            if child_link:
                                link = child_link.get_attribute('href')
                                
                    except NoSuchElementException:
                        continue
                    
                    if link:
                        if link.startswith('/'):
                            link = urljoin(base_url, link)
                        elif not link.startswith('http'):
                            link = urljoin(base_url, link)

                        if title not in results and link.startswith('http'):
                            results[title] = link
                            
                except Exception as e:
                    continue
    
    except Exception as e:
        log_message(f"기사 추출 중 오류: {str(e)}")
    
    return results


def go_to_next_page(driver, site_config: dict) -> bool:
    """다음 페이지로 이동"""
    try:
        next_type = site_config.get('next', '')
        
        if next_type == 'click':
            n_how = site_config.get('n_how', [])
            
            if len(n_how) >= 3:
                tag_name, attr_name, attr_value = n_how[0], n_how[1], n_how[2]
                
                if attr_name == 'class':
                    css_selector = f"{tag_name}.{attr_value.replace(' ', '.')}"
                elif attr_name == 'data-testid':
                    css_selector = f"{tag_name}[data-testid='{attr_value}']"
                else:
                    css_selector = f"{tag_name}[{attr_name}='{attr_value}']"

                try:
                    next_button = WebDriverWait(driver, 3).until(  # 대기 시간 단축
                        EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
                    )
                    driver.execute_script("arguments[0].click();", next_button)
                    return True
                    
                except TimeoutException:
                    common_selectors = [
                        "a[aria-label*='Next']",
                        "button[aria-label*='Next']",
                        ".pagination-next",
                        ".next-page",
                        "[data-testid*='next']"
                    ]
                    
                    for selector in common_selectors:
                        try:
                            next_button = driver.find_element(By.CSS_SELECTOR, selector)
                            if next_button.is_enabled():
                                driver.execute_script("arguments[0].click();", next_button)
                                return True
                        except NoSuchElementException:
                            continue
        
        return False
        
    except Exception as e:
        log_message(f"다음 페이지 이동 중 오류: {str(e)}")
        return False


# def test_cnn_selenium():
#     """CNN Selenium 크롤링 테스트"""
#     site_config = {
#         "type": "selenium",
#         "t_how": "/search?q=",
#         "next": "click",
#         "n_how": ["div", "class", "pagination-arrow pagination-arrow-right search__pagination-link text-active"],
#         "elem": ["span", "class", "container__headline-text"],
#         "link": "data-zjs-href"
#     }
    
#     results = crawl_by_selenium("edition.cnn.com", site_config, "technology")
    
#     print(f"CNN Selenium 크롤링 결과: {len(results)}개 기사")
#     for i, (title, link) in enumerate(list(results.items())[:5]):
#         print(f"{i+1}. {title[:80]}...")
#         print(f"   링크: {link}\n")
    
#     return results


# if __name__ == "__main__":
#     test_cnn_selenium()