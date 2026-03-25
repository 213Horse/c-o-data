from curl_cffi import requests
import re
from bs4 import BeautifulSoup

def test_curl_cffi(isbn):
    url = f"https://www.amazon.com/s?k={isbn}&i=stripbooks"
    print(f"Testing URL: {url}")
    # impersonate a real browser
    res = requests.get(url, impersonate="chrome110", timeout=15)
    print("Status:", res.status_code)
    
    if "api-services-support@amazon.com" in res.text or "captcha" in res.text.lower():
        print("CAPTCHA BLOCKED (Search)!")
        return
    else:
        print("Search Success!")

    soup = BeautifulSoup(res.text, "lxml")
    links = soup.select("a.a-link-normal.s-no-outline")
    if not links: 
        print("No search results found.")
        return

    product_url = None
    for l in links:
        href = l.get("href", "")
        if "/dp/" in href or "/gp/product/" in href:
            product_url = "https://www.amazon.com" + href
            break
            
    if product_url:
        print(f"Product URL: {product_url}")
        res2 = requests.get(product_url, impersonate="chrome110", timeout=15)
        print("Product Status:", res2.status_code)
        if "api-services-support@amazon.com" in res2.text or "captcha" in res2.text.lower():
            print("CAPTCHA BLOCKED (Product)!")
            return
        else:
            print("Product Success!")
            soup2 = BeautifulSoup(res2.text, "lxml")
            title = soup2.select_one("#productTitle")
            print("Title:", title.text.strip() if title else "NO TITLE")
            
            # test details
            details = {}
            for li in soup2.select("#detailBullets_feature_div li"):
                label_span = li.select_one(".a-text-bold")
                if label_span:
                    label = label_span.get_text().replace(":", "").replace("\u200f", "").replace("\u200e", "").strip()
                    val = li.get_text().replace(label_span.get_text(), "").strip()
                    details[label] = re.sub(r'^[:\s]+', '', val)
            print("Details:", details)

test_curl_cffi("9781444939453")
