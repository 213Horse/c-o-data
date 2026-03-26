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
            "Tác giả": ", ".join(info.get("authors", [])) if info.get("authors") else None,
            "Mô tả": info.get("description"),
            "Năm xuất bản": info.get("publishedDate"),
            "NXB": info.get("publisher"),
            "Số trang": info.get("pageCount"),
            "Ngôn ngữ": info.get("language"),
            "image_url": info.get("imageLinks", {}).get("thumbnail"),
            "description(vi)": info.get("description")
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
            "Tác giả": data.get("authors", [{}])[0].get("name"),
            "Mô tả": data.get("excerpts", [{}])[0].get("text"),
            "Năm xuất bản": data.get("publish_date"),
            "NXB": data.get("publishers", [{}])[0].get("name"),
            "Format": data.get("physical_format"),
            "Khối lượng": data.get("weight"),
            "Số trang": data.get("number_of_pages"),
            "Ngôn ngữ": None,
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
            if img.has_attr("data-a-dynamic-image"):
                import json
                try:
                    dyn = json.loads(img.get("data-a-dynamic-image", "{}"))
                    if dyn:
                        img_url = max(dyn.keys(), key=lambda k: dyn[k][0])
                except:
                    pass
            if not img_url:
                img_url = img.get("src") or img.get("data-old-hires")

        desc_div = soup2.select_one("#bookDescription_feature_div")
        desc = clean_text(desc_div.get_text()) if desc_div else None

        dim_str = details.get("Dimensions") or details.get("Product Dimensions") or details.get("Package Dimensions")
        weight_str = details.get("Item Weight") or details.get("Weight")
        pub_str = details.get("Publisher") or details.get("Publisher ")
        
        pub_year = None
        if pub_str and "(" in pub_str and ")" in pub_str:
            match = re.search(r'\((.*?)\)', pub_str)
            if match:
                pub_year = match.group(1)
            pub_str = pub_str.split("(")[0].strip()
            
        author_el = soup2.select_one(".author a")
        author = clean_text(author_el.get_text()) if author_el else details.get("Author")

        pages = details.get("Hardcover") or details.get("Paperback") or details.get("Print length") or details.get("Pages")
        if pages:
            pages = str(pages).replace("pages", "").strip()

        lang = details.get("Language")
        
        f_el = soup2.select_one("#productBinding")
        if not f_el:
            f_el = soup2.select_one("#productSubtitle")
        if not f_el:
            swatch = soup2.select_one(".swatchElement.selected .a-color-base")
            if swatch: f_el = swatch
            
        format_text = clean_text(f_el.get_text()) if f_el else None
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
            "Tác giả": author,
            "Mô tả": desc,
            "Năm xuất bản": pub_year,
            "NXB": pub_str,
            "Kích thước": dim_str,
            "Số trang": pages,
            "Format": final_format,
            "Ngôn ngữ": lang,
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
        return {"error": str(e)}

# -------------------------
# SEARCH ENGINE FALLBACK
# -------------------------
def search_fahasa_link(isbn):
    import urllib.parse
    import time
    from curl_cffi import requests as curl_requests
    
    # Fahasa uses an exposed App Search API for its frontend search
    api_url = "https://www.fahasa.com/api/elsearch/api/as/v1/engines/fhs-production-v2/search.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": "Bearer search-zs5622edvxg9bt9nb5y9m2oo",
        "Content-Type": "application/json"
    }
    
    # Try searching by exact ISBN first, then fall back to "ISBN fahasa" if that's what was passed
    queries = [isbn]
    
    for q in queries:
        payload = {
            "query": q,
            "page": {"size": 1, "current": 1}
        }
        try:
            res = curl_requests.post(api_url, json=payload, headers=headers, impersonate="chrome110", timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "results" in data and len(data["results"]) > 0:
                    link = data["results"][0].get("link", {}).get("raw", "")
                    if link:
                        if not link.startswith("http"):
                            link = "https://www.fahasa.com" + link
                        return link
        except Exception as e:
            print(f"  Fahasa API Search Failed: {e}")
            pass
            
    return None

# -------------------------
# FAHASA SCRAPER
# -------------------------
def get_fahasa_data(isbn, title=None):
    # Try direct search by ISBN first
    url = f"https://www.fahasa.com/catalogsearch/result/?q={isbn}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.fahasa.com/",
    }
    
    try:
        from curl_cffi import requests as curl_requests
        session = curl_requests.Session()
        res = session.get(url, headers=headers, impersonate="chrome110", timeout=15)
        soup = BeautifulSoup(res.text, "lxml")
        
        product_url = None
        if "catalogsearch/result" not in res.url and ".html" in res.url:
            product_url = res.url
        else:
            item = soup.select_one(".product-item-info a, .product-image")
            if item:
                product_url = item.get("href")
        
        # If ISBN search fails, try Search Engine Fallback (Google/DDG style)
        if not product_url:
            print(f"  Fahasa ISBN search failed. Trying search engine fallback...")
            product_url = search_fahasa_link(isbn)
            
        # If still no product_url and we have a title, try searching by Title on Fahasa
        if not product_url and title:
            # Try full title and then a simplified version (before :, -, ()
            clean_q = re.split(r'[:\-\(]', title)[0].strip()
            title_queries = [title]
            if clean_q and clean_q != title:
                title_queries.append(clean_q)
                
            for q_title in title_queries:
                print(f"  Fahasa fallback: Searching by Title '{q_title}'...")
                search_title_url = f"https://www.fahasa.com/catalogsearch/result/?q={urllib.parse.quote(q_title)}"
                res = session.get(search_title_url, headers=headers, impersonate="chrome110", timeout=15)
                soup = BeautifulSoup(res.text, "lxml")
                if "catalogsearch/result" not in res.url and ".html" in res.url:
                    product_url = res.url
                    break
                else:
                    item = soup.select_one(".product-item-info a, .product-image")
                    if item:
                        product_url = item.get("href")
                        break

        if product_url:
            print(f"  Scraping Fahasa: {product_url}")
            res = session.get(product_url, headers=headers, impersonate="chrome110", timeout=15)
            soup = BeautifulSoup(res.text, "lxml")
            
            title = soup.select_one(".product-view-name-main h1, h1")
            
            # Extract detailed info directly from the "Thông tin chi tiết" table
            details = {}
            for tr in soup.select("table.data-table tr, table#product-attribute-specs-table tr, .product-attributes tr, .detail-table tr"):
                th = tr.select_one("th, td.label")
                td = tr.select_one("td.data, td:not(.label)")
                if th and td:
                    label = clean_text(th.get_text(strip=True)).replace(":", "")
                    val = clean_text(td.get_text(strip=True))
                    details[label] = val

            # Fallbacks just in case the table isn't found
            author = details.get("Tác giả") or details.get("Author") or clean_text((soup.select_one(".data_author") or soup.new_tag("div")).get_text())
            publisher = details.get("NXB") or details.get("Nhà xuất bản") or clean_text((soup.select_one(".data_publisher") or soup.new_tag("div")).get_text())
            format_val = details.get("Hình thức") or details.get("Format") or clean_text((soup.select_one(".data_format") or soup.new_tag("div")).get_text())
            weight_str = details.get("Trọng lượng (gr)") or details.get("Trọng lượng") or details.get("Khối lượng") or clean_text((soup.select_one(".data_weight") or soup.new_tag("div")).get_text())
            dim_str = details.get("Kích Thước Bao Bì") or details.get("Kích thước") or clean_text((soup.select_one(".data_dimensions") or soup.new_tag("div")).get_text())
            pages = details.get("Số trang") or clean_text((soup.select_one(".data_qty_of_page") or soup.new_tag("div")).get_text())
            lang = details.get("Ngôn Ngữ") or details.get("Ngôn ngữ") or details.get("Language") or clean_text((soup.select_one(".data_languages") or soup.new_tag("div")).get_text())
            year = details.get("Năm XB") or details.get("Năm xuất bản") or clean_text((soup.select_one(".data_publish_year") or soup.new_tag("div")).get_text())
            
            desc = soup.select_one("#desc_content")
            img = soup.select_one(".product-view-image-main img, #lightgallery-item-0 img")
            
            d_l, d_w, d_h, d_unit = parse_dimensions(dim_str) if dim_str else (None, None, None, None)
            w_val, w_unit = parse_weight(weight_str) if weight_str else (None, None)
            if not w_unit and "gr" in str(details.get("Trọng lượng (gr)", "")).lower():
                w_unit = "grams"

            return {
                "Tên sách": clean_text(title.get_text(strip=True)) if title else None,
                "Tác giả": author if author else None,
                "Mô tả": clean_text(desc.get_text(strip=True)) if desc else None,
                "Năm xuất bản": year if year else None,
                "NXB": publisher if publisher else None,
                "Kích thước": dim_str if dim_str else None,
                "Số trang": pages if pages else None,
                "Format": format_val if format_val else None,
                "Ngôn ngữ": lang if lang else None,
                "Khối lượng": w_val,
                "Đơn vị khối lượng": w_unit,
                "Dài (Length)": d_l,
                "Rộng (Width)": d_w,
                "Cao (Height)": d_h,
                "Đơn vị kích thước": d_unit,
                "image_url": img.get("src") or img.get("data-src") if img else None,
                "description(vi)": clean_text(desc.get_text(strip=True)) if desc else None
            }
    except: pass
    return None

# -------------------------
# MAIN PROCESS
# -------------------------
def process_isbn(isbn):
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

def run_scraper(mode="foreign", progress_callback=None, log_callback=None):
    def emit_log(msg):
        if log_callback: log_callback(msg)
        print(msg)

    emit_log(f"Mode: {mode.upper()}")
    if not os.path.exists(INPUT_FILE):
        emit_log(f"Error: {INPUT_FILE} not found.")
        return
    
    # 1. Load existing results if any to track progress
    # ... (same logic as before)
    existing_isbns = set()
    existing_df = pd.DataFrame()
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_df = pd.read_excel(OUTPUT_FILE)
            if not existing_df.empty and "ISBN" in existing_df.columns:
                existing_isbns = set(existing_df["ISBN"].astype(str).tolist())
                emit_log(f"Found {len(existing_isbns)} already processed items in {OUTPUT_FILE}")
        except Exception as e:
            emit_log(f"Warning: Could not read {OUTPUT_FILE}, starting fresh. Error: {e}")

    # 2. Load input list
    df = pd.read_excel(INPUT_FILE)
    
    # 3. Filter for unprocessed ISBNs
    to_process = []
    for isbn in df.iloc[:, 0]:
        isbn_str = str(isbn).strip()
        if not isbn_str or isbn_str == "nan": continue
        if isbn_str not in existing_isbns:
            to_process.append(isbn_str)
    
    if not to_process:
        emit_log("All ISBNs have been processed!")
        if progress_callback: progress_callback(100)
        return

    # 4. Process up to 1000 items
    to_process = to_process[:1000]
    total_to_process = len(to_process)
    emit_log(f"Total remaining: {total_to_process}. Starting...")

    cols = [
        "ISBN", "Tên sách", "Tác giả", "Mô tả", "Năm xuất bản", "NXB", 
        "Kích thước", "Khối lượng", "Đơn vị khối lượng", "Dài (Length)", "Rộng (Width)", "Cao (Height)", "Đơn vị kích thước", 
        "Số trang", "Format", "Ngôn ngữ", "image_url", "image_name", "description(vi)"
    ]

    processed_in_this_run = 0
    for isbn in to_process:
        emit_log(f"\nProcessing: {isbn}")
        results = []
        
        if mode == "foreign":
            # Foreign mode: Amazon fallbacks + Google + OpenLibrary
            data_amazon = get_amazon_data(isbn, "isbn")
            if data_amazon: results.append(data_amazon)

            is_audio = data_amazon and ("audio" in str(data_amazon.get("Format")).lower() or "audio" in str(data_amazon.get("NXB")).lower())
            needs_dimensions = not data_amazon or not data_amazon.get("Dài (Length)")
            
            if is_audio or needs_dimensions:
                title = data_amazon.get("Tên sách") if data_amazon else None
                if not title:
                    g_temp = get_google_books(isbn, "isbn")
                    title = g_temp.get("Tên sách") if g_temp else None
                if title:
                    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
                    emit_log(f"  Fallback Title Search: {clean_title}")
                    data_title = get_amazon_data(clean_title, "title")
                    if data_title: results.append(data_title)

            g_data = get_google_books(isbn, "isbn")
            if g_data: results.append(g_data)
            ol_data = get_open_library_data(isbn)
            if ol_data: results.append(ol_data)
        
        else: # Vietnamese mode
            # Step 1: SEARCH GOOGLE FOR FAHASA LINK FIRST
            emit_log(f"  Searching Google for Fahasa link...")
            f_data = get_fahasa_data(isbn)
            
            if f_data:
                results.append(f_data)
                emit_log(f"  Fahasa found: {f_data.get('Tên sách')}")
            else:
                emit_log(f"  Fahasa not found or failed. Falling back to Amazon...")
                data_amazon = get_amazon_data(isbn, "isbn")
                if data_amazon:
                    results.append(data_amazon)
                    emit_log(f"  Amazon found: {data_amazon.get('Tên sách')}")

        # Merge
        fields = [
            "Tên sách", "Tác giả", "Phân loại", "NXB", "Năm XB", "Ngôn ngữ", 
            "Số trang", "Format", "Khối lượng", "Đơn vị khối lượng",
            "Dài (Length)", "Rộng (Width)", "Cao (Height)", "Đơn vị kích thước", "image_url"
        ]
        merged = {"ISBN": isbn}
        for field in fields:
            for res in results:
                if res.get(field):
                    merged[field] = res[field]
                    break
        
        if merged.get("image_url") and not merged.get("image_name"):
            merged["image_name"] = download_image(merged["image_url"], isbn)

        # Save immediately
        new_row_df = pd.DataFrame([merged])
        if existing_df.empty:
            existing_df = new_row_df
        else:
            existing_df = pd.concat([existing_df, new_row_df], ignore_index=True)
        
        save_df = existing_df.reindex(columns=cols)
        save_df.to_excel(OUTPUT_FILE, index=False)
        emit_log(f"  Saved: {isbn}")
        
        processed_in_this_run += 1
        if progress_callback:
            progress_callback(int((processed_in_this_run / total_to_process) * 100))
        
        time.sleep(3)

    emit_log(f"\nALL DONE! Total now: {len(existing_df)} in {OUTPUT_FILE}")
    if progress_callback: progress_callback(100)

if __name__ == "__main__":
    run_scraper()