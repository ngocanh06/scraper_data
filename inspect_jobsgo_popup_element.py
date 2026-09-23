import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

if __name__ == '__main__':
    options = uc.ChromeOptions()
    options.add_argument('--window-position=-2400,-2400')
    options.add_argument('--window-size=1920,1080')

    driver = uc.Chrome(options=options, headless=False)
    try:
        url = 'https://jobsgo.vn/viec-lam/nhan-vien-kinh-doanh-dich-vu-van-tai-sales-logistics-luong-cung-upto-15tr-long-an-28383842188.html'
        print(f"Fetching URL: {url}")
        driver.get(url)
        time.sleep(4)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        print("\n=== FINDING THE EXACT ELEMENT CONTAINING '×Địa điểm:×Hà Nội' ===")
        for tag in soup.find_all(True):
            txt = tag.get_text(strip=True)
            if '×Địa điểm:' in txt:
                cls = ' '.join(tag.get('class', []))
                id_attr = tag.get('id', '')
                print(f"  <{tag.name}> id='{id_attr}' class='{cls[:50]}' -> len(txt)={len(txt)}")

    finally:
        try:
            driver.quit()
        except:
            pass
