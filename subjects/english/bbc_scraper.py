import requests
from bs4 import BeautifulSoup
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

def fetch_article(url: str) -> dict:
    """
    URL에서 영문 뉴스 기사 본문을 가져옵니다.
    Returns: {"title": str, "text": str, "url": str, "source": str}
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
    except requests.exceptions.SSLError:
        try:
            http_url = url.replace("https://", "http://")
            resp = requests.get(http_url, headers=HEADERS, timeout=15, verify=False)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e2:
            raise ConnectionError(f"페이지를 불러오지 못했습니다 (SSL): {e2}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"페이지를 불러오지 못했습니다: {e}")

    title_tag = soup.find("h1")
    title = title_tag.get_text().strip() if title_tag else "제목 없음"

    article_content = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"article|body|content", re.I))
    
    if article_content:
        paragraphs = article_content.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    text_parts = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 20]
    text = _clean(" ".join(text_parts))

    if len(text) < 100:
        text = _clean(soup.get_text(separator=" "))

    return {
        "title": title,
        "text": text[:8000], 
        "url": url,
        "source": _get_domain(url).upper(),
    }

def get_bbc_news_list():
    """
    BBC 최신 뉴스 목록(제목, URL)을 가져옵니다.
    """
    url = "https://www.bbc.com/news/technology"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        news_items = []
        seen_urls = set()
        
        links = soup.find_all("a", href=True)
        for link in links:
            href = link["href"]
            if href.startswith("/"):
                href = "https://www.bbc.com" + href
            
            if "/articles/" in href and href not in seen_urls:
                title_tag = link.find(["h2", "h3"]) or link
                title = title_tag.get_text().strip()
                if title and len(title) > 15:
                    news_items.append({"title": title, "url": href})
                    seen_urls.add(href)
            
            if len(news_items) >= 12:
                break
        
        return news_items
    except Exception as e:
        print(f"BBC 뉴스 목록 가져오기 오류: {e}")
        return []

def _get_domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return match.group(1) if match else url

def _clean(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw)
    return text.strip()
