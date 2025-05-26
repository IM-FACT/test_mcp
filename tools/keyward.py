from bs4 import BeautifulSoup
import re
import json
from typing import Annotated
from pydantic import Field
from .down import download_html

def extract_keyword(
    html_url: Annotated[str, Field(description="URL of the webpage to extract keywords from")],
    keywords: Annotated[str, Field(description="Keywords to search for in the webpage content")],
) -> str:
    """

    """

    html_uri = download_html(html_url)
    if html_uri == '0':
        return "실패"
    
    with open(html_uri, 'r', encoding='utf-8') as docs:
        soup = BeautifulSoup(docs, "lxml")

        words = keywords.split()

        ps = soup.find_all("p")
        mid_result = {}

        for word in words:
            pset : set[str] = set()
            for p in ps:
                content = p.get_text(strip=True)
                if re.search(re.escape(word), content, re.IGNORECASE):
                    pset.add(content)
            
            mid_result["<p>"+word+"</p>"] = list(pset)
        result = json.dumps(mid_result, ensure_ascii=False, indent=2)
    
    return result


if __name__ == "__main__":
    print(extract_keyword("test.html", "global"))
