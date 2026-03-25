import pandas as pd
import requests
import isbnlib
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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Referer": "https://www.google.com/"
}

# -------------------------
# HELPERS
# -------------------------
def parse_dimensions(dim_str):
    """Parses '5.39 x 1.38 x 8.07 inches' into Length, Width, Height."""
    if not dim_str:
        return None, None, None
    matches = re.findall(r"(\d+\.?\d*)", dim_str)
    if len(matches) >= 3:
        return matches[0], matches[1], matches[2]
    return None, None, None

def download_image(url, isbn):
    """Downloads image and returns the local filename."""
    if not url:
        return None
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            filename = f"{isbn}.jpg"
            filepath = os.path.join(IMAGE_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(res.content)
            return filename
    except:
        pass
    return None

# -------------------------
# GOOGLE BOOKS API
# -------------------------
def get_google_books(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if "items" not in data:
            return None
        info = data["items"][0]["volumeInfo"]
        return {
            "ISBN": isbn,
            "Tên sách": info.get("title"),
            "NXB": info.get("publisher"),
            "description(vi)": info.get("description"),
            "image_url": info.get("imageLinks", {}).get("thumbnail")
        }
    except:
        return None

# -------------------------
# AMAZON SCRAPER
# -------------------------
def get_amazon_data(isbn):
    try:
        search_url = f"https://www.amazon.com/s?k={isbn}"
        res = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "lxml")

        link = soup.select_one("a.a-link-normal.s-no-outline")
        if not link:
            return None

        product_url = "https://www.amazon.com" + link.get("href")
        time.sleep(1) # Be gentle
        res2 = requests.get(product_url, headers=HEADERS, timeout=10)
        soup2 = BeautifulSoup(res2.text, "lxml")

        # Basic Info
        title = soup2.select_one("#productTitle")
        title = title.text.strip() if title else None
        
        format_val = soup2.select_one("#productBinding")
        format_val = format_val.text.strip() if format_val else None

        # Details (Publisher, Weight, Dimensions)
        details = {}
        for li in soup2.select("#detailBullets_feature_div li"):
            text = li.get_text(separator=":", strip=True)
            if ":" in text:
                parts = text.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                # Clean up nested labels
                val = val.split(":")[-1].strip()
                details[key] = val

        # Image
        img = soup2.select_one("#landingImage")
        img_url = img.get("src") if img else None

        # Description
        desc_div = soup2.select_one("#bookDescription_feature_div")
        desc = desc_div.get_text(strip=True) if desc_div else None

        d_l, d_w, d_h = parse_dimensions(details.get("Dimensions"))

        return {
            "ISBN": isbn,
            "Tên sách": title,
            "NXB": details.get("Publisher"),
            "Format": format_val,
            "Khối lượng": details.get("Item Weight"),
            "Dài (Length)": d_l,
            "Rộng (Width)": d_w,
            "Cao (Height)": d_h,
            "image_url": img_url,
            "description(vi)": desc
        }

    except Exception as e:
        print(f"Amazon error for {isbn}: {e}")
        return None

# -------------------------
# MAIN PROCESS
# -------------------------
def process_isbn(isbn):
    print(f"Processing: {isbn}")
    
    # Try Amazon first for details
    data = get_amazon_data(isbn)
    
    # If Amazon fails or missing title, try Google
    if not data or not data.get("Tên sách"):
        g_data = get_google_books(isbn)
        if g_data:
            if not data: data = {"ISBN": isbn}
            data.update({k: v for k, v in g_data.items() if v})

    # Download image if found
    if data and data.get("image_url"):
        data["image_name"] = download_image(data["image_url"], isbn)
    
    # Standardize result keys
    result = {
        "ISBN": isbn,
        "Tên sách": data.get("Tên sách") if data else None,
        "NXB": data.get("NXB") if data else None,
        "Format": data.get("Format") if data else None,
        "Khối lượng": data.get("Khối lượng") if data else None,
        "Dài (Length)": data.get("Dài (Length)") if data else None,
        "Rộng (Width)": data.get("Rộng (Width)") if data else None,
        "Cao (Height)": data.get("Cao (Height)") if data else None,
        "image_name": data.get("image_name") if data else None,
        "description(vi)": data.get("description(vi)") if data else None
    }
    return result

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found!")
        return

    df = pd.read_excel(INPUT_FILE)
    results = []

    for isbn in df.iloc[:, 0]:
        isbn = str(isbn).strip()
        if not isbn or isbn == "nan": continue
        
        data = process_isbn(isbn)
        results.append(data)
        time.sleep(2) # Avoid getting blocked

    output_df = pd.DataFrame(results)
    output_df.to_excel(OUTPUT_FILE, index=False)
    print(f"DONE -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()