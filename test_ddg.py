import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def get_amazon_url_via_ddg(isbn):
    url = f"https://html.duckduckgo.com/html/?q=site:amazon.com+{isbn}"
    res = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")
    for a in soup.find_all("a", class_="result__url"):
        href = a.get("href", "")
        if "amazon.com" in href and ("/dp/" in href or "/product/" in href):
            return href.strip()
    return None

print(get_amazon_url_via_ddg("9781536213911"))
