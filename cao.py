import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
import re

# -------------------------
# CONFIG
# -------------------------
INPUT_FILE = "danhsachisbn.xlsx"
OUTPUT_FILE = "output.xlsx"
IMAGE_DIR = "images"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://www.amazon.com/"
}

# -------------------------
# HELPERS
# -------------------------
def clean_text(text):
    if not text: return ""
    text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\ufeff]', '', text)
    return text.strip()

def parse_dimensions(dim_str):
    if not dim_str: return None, None, None, None
    matches = re.findall(r"(\d+\.?\d*)", dim_str)
    # Extract unit (e.g., inches, cm)
    unit_match = re.search(r"([a-zA-Z]+)$", dim_str.strip())
    unit = unit_match.group(1) if unit_match else ""
    
    if len(matches) >= 3:
        return matches[0], matches[1], matches[2], unit
    return None, None, None, None

def parse_weight(weight_str):
    if not weight_str: return None, None
    match = re.search(r"(\d+\.?\d*)\s*(.*)", str(weight_str))
    if match:
        return match.group(1), match.group(2).strip()
    return weight_str, None

def download_image(url, isbn):
    if not url: return None
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            filename = f"{isbn}.jpg"
            filepath = os.path.join(IMAGE_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(res.content)
            return filename
    except: pass
    return None

# -------------------------
# GOOGLE BOOKS API
# -------------------------
def get_google_books(query, query_type="isbn"):
    q = f"isbn:{query}" if query_type == "isbn" else query
    url = f"https://www.googleapis.com/books/v1/volumes?q={q}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if "items" not in data: return None
        info = data["items"][0]["volumeInfo"]
        return {
            "Tên sách": info.get("title"),
            "NXB": info.get("publisher"),
            "description(vi)": info.get("description"),
            "image_url": info.get("imageLinks", {}).get("thumbnail")
        }
    except: return None

# -------------------------
# OPEN LIBRARY API
# -------------------------
def get_open_library_data(isbn):
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        res = requests.get(url, timeout=10)
        data = res.json().get(f"ISBN:{isbn}")
        if not data: return None
        return {
            "Tên sách": data.get("title"),
            "NXB": data.get("publishers", [{}])[0].get("name"),
            "Format": data.get("physical_format"),
            "Khối lượng": data.get("weight"),
            "image_url": data.get("cover", {}).get("large")
        }
    except: return None

# -------------------------
# AMAZON SCRAPER
# -------------------------
def get_amazon_data(query, query_type="isbn"):
    try:
        from curl_cffi import requests as curl_requests
        search_suffix = "&i=stripbooks" if query_type == "isbn" else " paperback"
        search_url = f"https://www.amazon.com/s?k={query}{search_suffix}"
        res = curl_requests.get(search_url, impersonate="chrome110", timeout=15)
        soup = BeautifulSoup(res.text, "lxml")

        links = soup.select("a.a-link-normal.s-no-outline")
        if not links: return None
            
        product_url = None
        for l in links:
            href = l.get("href", "")
            if "/dp/" in href or "/gp/product/" in href:
                # Prefer non-Audible/Kindle
                link_text = l.get_text().lower()
                if "audible" not in link_text and "kindle" not in link_text:
                    product_url = "https://www.amazon.com" + href
                    break
        
        if not product_url:
            product_url = "https://www.amazon.com" + links[0].get("href")

        time.sleep(1.5)
        res2 = curl_requests.get(product_url, impersonate="chrome110", timeout=15)
        soup2 = BeautifulSoup(res2.text, "lxml")

        title = soup2.select_one("#productTitle")
        title = clean_text(title.text) if title else None
        
        format_val = soup2.select_one("#productBinding")
        format_val = clean_text(format_val.text) if format_val else None

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

        img = soup2.select_one("#landingImage, #imgBlkFront, #ebooksImgBlkFront, #main-image")
        img_url = None
        if img:
            # Try to get highest-res from dynamic image dict
            if img.has_attr("data-a-dynamic-image"):
                import json
                try:
                    dyn = json.loads(img.get("data-a-dynamic-image", "{}"))
                    if dyn:
                        # Get URL with max width
                        img_url = max(dyn.keys(), key=lambda k: dyn[k][0])
                except:
                    pass
            if not img_url:
                img_url = img.get("src") or img.get("data-old-hires")

        desc_div = soup2.select_one("#bookDescription_feature_div")
        desc = clean_text(desc_div.get_text()) if desc_div else None

        # Flexible matching
        dim_str = details.get("Dimensions") or details.get("Product Dimensions") or details.get("Package Dimensions")
        weight_str = details.get("Item Weight") or details.get("Weight")
        pub_str = details.get("Publisher") or details.get("Publisher ")
        
        # Format detection improvements
        # 1. Standard Binding
        f_el = soup2.select_one("#productBinding")
        # 2. Subtitle (Hardcover – June 20, 2024)
        if not f_el:
            f_el = soup2.select_one("#productSubtitle")
        # 3. Selected Swatch
        if not f_el:
            swatch = soup2.select_one(".swatchElement.selected .a-color-base")
            if swatch: f_el = swatch
            
        format_text = clean_text(f_el.get_text()) if f_el else None
        # Clean up subtitle if it contains a date (Hardcover – ...)
        if format_text and "–" in format_text:
            format_text = format_text.split("–")[0].strip()
            
        final_format = format_text or details.get("Format") or details.get("Binding") or details.get("Program Type")
        
        if not final_format:
            for k in details:
                if "paperback" in k.lower() or "hardcover" in k.lower():
                    final_format = k
                    break

        d_l, d_w, d_h, d_unit = parse_dimensions(dim_str)
        w_val, w_unit = parse_weight(weight_str)

        return {
            "Tên sách": title,
            "NXB": pub_str,
            "Format": final_format,
            "Khối lượng": w_val,
            "Đơn vị khối lượng": w_unit,
            "Dài (Length)": d_l,
            "Rộng (Width)": d_w,
            "Cao (Height)": d_h,
            "Đơn vị kích thước": d_unit,
            "image_url": img_url,
            "description(vi)": desc
        }
    except Exception as e:
        print(f"Amazon error for {query}: {e}")
        return None

# -------------------------
# MAIN PROCESS
# -------------------------
def process_isbn(isbn):
    print(f"Processing: {isbn}")
    results = []
    
    # Cascade 1: ISBN based
    data_isbn = get_amazon_data(isbn, "isbn")
    if data_isbn: results.append(data_isbn)
    
    # If ISBN result is Audiobook or missing dimensions, try Title based search for Paperback
    is_audio = data_isbn and ("audio" in str(data_isbn.get("Format")).lower() or "audio" in str(data_isbn.get("NXB")).lower())
    needs_dimensions = not data_isbn or not data_isbn.get("Dài (Length)")
    
    if is_audio or needs_dimensions:
        title = data_isbn.get("Tên sách") if data_isbn else None
        if not title:
            g_temp = get_google_books(isbn, "isbn")
            title = g_temp.get("Tên sách") if g_temp else None
            
        if title:
            # Clean title of series info or brackets
            clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
            print(f"  Fallback Title Search: {clean_title}")
            data_title = get_amazon_data(clean_title, "title")
            if data_title: results.append(data_title)

    # API fallbacks
    g_data = get_google_books(isbn, "isbn")
    if g_data: results.append(g_data)
    ol_data = get_open_library_data(isbn)
    if ol_data: results.append(ol_data)
    
    # Merge
    merged = {"ISBN": isbn}
    fields = ["Tên sách", "NXB", "Format", "Khối lượng", "Đơn vị khối lượng", "Dài (Length)", "Rộng (Width)", "Cao (Height)", "Đơn vị kích thước", "image_url", "description(vi)"]
    for field in fields:
        for res in results:
            if res.get(field):
                merged[field] = res[field]
                break

    if merged.get("image_url") and not merged.get("image_name"):
        merged["image_name"] = download_image(merged["image_url"], isbn)
    return merged

def main():
    if not os.path.exists(INPUT_FILE): return
    df = pd.read_excel(INPUT_FILE)
    results = []
    for isbn in df.iloc[:10, 0]:
        isbn = str(isbn).strip()
        if not isbn or isbn == "nan": continue
        results.append(process_isbn(isbn))
        time.sleep(3)

    output_df = pd.DataFrame(results)
    cols = ["ISBN", "Tên sách", "NXB", "Format", "Khối lượng", "Đơn vị khối lượng", "Dài (Length)", "Rộng (Width)", "Cao (Height)", "Đơn vị kích thước", "image_url", "image_name", "description(vi)"]
    output_df = output_df.reindex(columns=cols)
    output_df.to_excel(OUTPUT_FILE, index=False)
    print(f"DONE -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()