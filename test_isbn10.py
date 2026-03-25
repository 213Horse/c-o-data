import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}

def isbn13_to_isbn10(isbn13):
    isbn13 = str(isbn13).replace("-", "").strip()
    if len(isbn13) != 13 or not isbn13.startswith("978"):
        return None
    core = isbn13[3:12]
    sum = 0
    for i in range(9):
        sum += int(core[i]) * (10 - i)
    check_digit = 11 - (sum % 11)
    if check_digit == 10:
        check_digit = "X"
    elif check_digit == 11:
        check_digit = "0"
    return core + str(check_digit)

# Test with 9781444939453
isbn10 = isbn13_to_isbn10("9781444939453")
print("ISBN-10:", isbn10)

url = f"https://www.amazon.com/dp/{isbn10}"
print("URL:", url)
res = requests.get(url, headers=HEADERS)
print("Status:", res.status_code)
if "Toto" in res.text:
    print("Found Toto!")
if "api-services-support@amazon.com" in res.text or "captcha" in res.text.lower():
    print("CAPTCHA BLOCKED!")
else:
    print("NOT BLOCKED!")
