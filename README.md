# 기후 변화 증거 검색 MCP 서버

이 프로젝트는 FastMCP SDK를 사용하여 구현된 Model Context Protocol (MCP) 서버로, LLM 모델이 기후 변화와 관련된 의문점에 대한 증거를 웹에서 검색할 수 있도록 돕습니다.

## 주요 기능

1. **HTML 분석**: BeautifulSoup4를 사용하여 HTML 콘텐츠를 분석하고 특정 태그나 텍스트를 추출합니다.
2. **사전 정의된 도메인 크롤링**: 기후 변화 관련 분야(탄소배출, 전기차, 해수면상승, 기온, 생태계)에 특화된 웹사이트에서 정보를 크롤링합니다.
3. **사용자 정의 URL 크롤링**: 직접 지정한 URL에서 정보를 크롤링하고 키워드 기반으로 필터링합니다.
4. **검색 기반 크롤링**: 웹사이트의 자체 검색 기능을 활용하여 키워드 검색 결과를 수집합니다.
5. **증거 추출**: HTML 콘텐츠에서 기후 변화 관련 질문에 대한 증거를 추출합니다.

## 기능 업데이트

- **HTML 파일 저장**: 모든 크롤링 기능은 수집된 HTML을 `./resource` 폴더에 자동 저장하고 파일 경로를 반환합니다.
- **검색 방법 구분**: 검색 기반 크롤링은 정확한 검색 결과인지, 대체 방법으로 찾은 것인지 명확히 구분하여 반환합니다.
- **다국어 검색 지원**: 다양한 언어로 웹사이트 검색이 가능합니다(기본값: 한국어).

## 지원하는 기후 변화 분야

- 탄소배출
- 전기차
- 해수면상승
- 기온
- 생태계


## 도구 사용 예시

### HTML 분석

```python
html_analyzer(
    html_content="<html><body><p>기후 변화는 실제입니다.</p></body></html>",
    extract_text_only=True
)
```

### 사전 정의된 도메인 크롤링

```python
# 크롤링 결과는 HTML 파일로 저장되고 파일 경로가 반환됩니다
result = climate_domain_crawler(
    category="탄소배출",
    keywords=["탄소중립", "감축목표"]
)
# result = {'urls': [...], 'file_paths': [...], ...}
```

### 사용자 정의 URL 크롤링

```python
# 크롤링 결과는 HTML 파일로 저장되고 파일 경로가 반환됩니다
result = custom_url_crawler(
    start_url="https://example.com/climate",
    keywords=["기후위기", "대응방안"]
)
# result = {'urls': [...], 'file_paths': [...], ...}
```

### 검색 기반 크롤링 (신규)

```python
# 웹사이트의 검색 기능을 활용한 키워드 검색
result = search_based_crawler(
    base_url="https://www.ipcc.ch",
    keywords=["climate mitigation", "sea level"],
    language="en"
)
# result = {'search_results': {...}, 'search_method': {...}, 'descriptions': {...}, ...}
```

### 증거 추출

```python
# HTML 파일 내용에서 질문 관련 증거 추출
evidence = extract_climate_evidence(
    html_content=open("./resource/climate_file.html").read(),
    query="해수면 상승 영향"
)
# evidence = {'evidence_paragraphs': [...], 'query': '해수면 상승 영향'}
```

## 사용 시나리오

1. **카테고리 확인**: LLM은 지원되는 기후 변화 카테고리 목록을 리소스를 통해 확인합니다.
2. **도메인 크롤링**: 적절한 카테고리와 키워드로 정보를 검색합니다.
3. **증거 추출**: 크롤링된 HTML 파일에서 의문점에 대한 증거를 추출합니다.
4. **HTML 분석**: 필요시 HTML 파일의 특정 태그나 전체 텍스트를 분석합니다.

## 폴더 구조

```
fact_mcp/
├── main.py        # MCP 서버 코드
├── README.md      # 프로젝트 설명
└── resource/      # 크롤링된 HTML 파일 저장 폴더 (자동 생성)
```
