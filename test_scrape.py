import requests
from bs4 import BeautifulSoup
import re
import urllib3
urllib3.disable_warnings()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://www.amazon.com/"
}

def clean_text(text):
    if not text: return ""
    text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\ufeff]', '', text)
    return text.strip()

def test_amazon(query):
    search_url = f"https://www.amazon.com/s?k={query}&i=stripbooks"
    print(f"Search URL: {search_url}")
    res = requests.get(search_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.text, "lxml")
    
    if "api-services-support@amazon.com" in res.text or "captcha" in res.text.lower():
        print("DETECTED CAPTCHA ON SEARCH PAGE!")
        with open("test_search.html", "w") as f:
            f.write(res.text)
        return

    links = soup.select("a.a-link-normal.s-no-outline")
    if not links: 
        print("No search results found.")
        with open("test_search.html", "w") as f:
            f.write(res.text)
        return

    product_url = None
    for l in links:
        href = l.get("href", "")
        if "/dp/" in href or "/gp/product/" in href:
            link_text = l.get_text().lower()
            if "audible" not in link_text and "kindle" not in link_text:
                product_url = "https://www.amazon.com" + href
                break
    
    if not product_url:
        product_url = "https://www.amazon.com" + links[0].get("href")

    print(f"Product URL: {product_url}")
    
    res2 = requests.get(product_url, headers=HEADERS, timeout=15)
    with open("test_product.html", "w") as f:
        f.write(res2.text)
        
    if "api-services-support@amazon.com" in res2.text or "captcha" in res2.text.lower():
        print("DETECTED CAPTCHA ON PRODUCT PAGE!")
        return

    soup2 = BeautifulSoup(res2.text, "lxml")
    
    details = {}
    for li in soup2.select("#detailBullets_feature_div li"):
        label_span = li.select_one(".a-text-bold")
        if label_span:
            label = clean_text(label_span.get_text()).replace(":", "").strip()
            val = clean_text(li.get_text()).replace(clean_text(label_span.get_text()), "").strip()
            details[label] = re.sub(r'^[:\s]+', '', val)

    if not details.get("Publisher") or not details.get("Dimensions"):
        for tr in soup2.select("table.a-keyvalue tr"):
            th = tr.select_one("th")
            td = tr.select_one("td")
            if th and td:
                details[clean_text(th.get_text())] = clean_text(td.get_text())
                
    print("Extracted Details:", details)

test_amazon("9781536213911")
