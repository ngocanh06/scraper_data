"""
topcv/crawl_matrix.py
────────────────────
Script cào dữ liệu TopCV theo ma trận [Tỉnh thành × Ngành nghề].
Tự động lưu vào SQL Server (bảng [topcv]) và xuất file Excel topcv_matrix_jobs.xlsx.
"""

import sys
import io
import os
import re
import random
import time
import pandas as pd

from bs4 import BeautifulSoup
import undetected_chromedriver as uc

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import DatabasePersistenceError, JobDB
from excel_storage import ExcelPersistenceError, save_records_to_excel
from parse_job_detail import parse_full_topcv_job, create_driver, SOURCE
from provinces import get_topcv_cities

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Mặc định lấy danh sách tỉnh thành (dùng mode='34' hoặc mode='all')
CITIES = get_topcv_cities(mode='34')


CATEGORIES = [
    {'name': 'Kinh doanh / Bán hàng', 'slug': 'tim-viec-lam-nhan-vien-kinh-doanh'},
    {'name': 'Marketing / PR',        'slug': 'tim-viec-lam-marketing'},
    {'name': 'Hành chính / Nhân sự',  'slug': 'tim-viec-lam-hanh-chinh-nhan-su'},
    {'name': 'Kế toán / Kiểm toán',  'slug': 'tim-viec-lam-ke-toan'},
    {'name': 'IT / Phần mềm',         'slug': 'tim-viec-lam-it'},
    {'name': 'CSKH / Telesales',       'slug': 'tim-viec-lam-nhan-vien-cham-soc-khach-hang'},
    {'name': 'Tài chính / Ngân hàng', 'slug': 'tim-viec-lam-ngan-hang'},
    {'name': 'Kỹ thuật / Xây dựng',   'slug': 'tim-viec-lam-ky-su-xay-dung'},
    {'name': 'Bất động sản',          'slug': 'tim-viec-lam-bat-dong-san'},
    {'name': 'Giáo dục / Đào tạo',    'slug': 'tim-viec-lam-giao-duc'},
]

MAX_PAGES_PER_CELL = 8
DELAY_MIN = 3.0
DELAY_MAX = 5.0


def extract_job_urls_from_search(driver: uc.Chrome, search_url: str) -> list[str]:
    urls = []
    try:
        driver.get(search_url)
        time.sleep(random.uniform(2.5, 3.5))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for container in soup.select('.job-item-search-result, .job-item-2024, .job-ta, [class*="job-item"]'):
            a_tag = container.select_one('h3.title a, .title a, a[href*=".html"]')
            if a_tag:
                href = a_tag.get('href', '')
                if href and ('.html' in href) and ('/viec-lam/' in href or 'brand' in href or 'tuyen-dung' in href):
                    clean_url = href.split('?')[0] if '?' in href else href
                    if clean_url not in urls:
                        urls.append(clean_url)
    except Exception as e:
        print(f'   [!] Lỗi khi lấy danh sách job từ TopCV search page: {e}')

    return urls


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

    print('=' * 70)
    print('🚀 [TOPCV] BẮT ĐẦU CÀO DỮ LIỆU THEO MA TRẬN [TỈNH THÀNH × NGÀNH NGHỀ]')
    print('=' * 70)

    db = JobDB()
    db.ensure_table(SOURCE)

    print('[TopCV Chrome] Đang khởi động undetected-chromedriver ngầm...')
    driver = create_driver()
    print('[TopCV Chrome] Chrome đã sẵn sàng!\n')

    total_scraped = 0
    total_saved = 0
    seen_urls = set()
    dataset = []
    excel_file = os.path.join(os.path.dirname(__file__), 'topcv_matrix_jobs.xlsx')

    def save_excel(records=None):
        records = dataset if records is None else records
        if records:
            saved_path = save_records_to_excel(records, excel_file)
            print(f'   📊 [TopCV Excel] Đã lưu {len(records)} việc làm vào {saved_path}')

    try:
        for cat in CATEGORIES:
            for city in CITIES:
                cell_name = f"{cat['name']} × {city['name']}"
                print(f'\n📌 [TopCV: {cell_name}]')
                base_url = f"https://www.topcv.vn/{cat['slug']}-{city['slug']}"

                for page in range(1, MAX_PAGES_PER_CELL + 1):
                    search_url = f"{base_url}?page={page}" if page > 1 else base_url
                    print(f'   📄 Trang {page}/{MAX_PAGES_PER_CELL}: {search_url}')

                    job_urls = extract_job_urls_from_search(driver, search_url)
                    if not job_urls:
                        print('   [i] Không còn job nào ở trang này. Chuyển ô tiếp theo.')
                        break

                    print(f'   → Tìm thấy {len(job_urls)} việc làm.')

                    for idx, url in enumerate(job_urls, start=1):
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        total_scraped += 1

                        print(f'      [{total_scraped}] Cào TopCV detail: {url[-65:]}')
                        record = parse_full_topcv_job(driver, url, stt_index=total_scraped)

                        if record:
                            ok = db.insert(SOURCE, record)
                            dataset.append(record)
                            if ok:
                                total_saved += 1
                                print(f'         ✅ [TopCV DB UPSERT] {record["Công việc"][:35]} | {record["Nhà tuyển dụng"][:25]} | {record["Mức lương"]}')
                        else:
                            print(f'         ❌ Không parse được job TopCV này.')

                        if len(dataset) % 10 == 0:
                            save_excel()

                        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                    save_excel()
                    time.sleep(random.uniform(2.0, 4.0))

    except (DatabasePersistenceError, ExcelPersistenceError):
        raise
    except KeyboardInterrupt:
        print('\n[!] Người dùng dừng TopCV scraper.')
    except Exception as e:
        print(f'\n[!] Lỗi TopCV scraper: {e}')
    finally:
        try:
            save_excel(db.get_all_records(SOURCE))
        finally:
            try:
                driver.quit()
            except Exception:
                pass
            print('\n[TopCV Chrome] Đã đóng Chrome.')
            db.close()

    print('\n' + '=' * 70)
    print('=== TỔNG KẾT TOPCV SCRAPER ===')
    print(f'  Tổng số URL đã quét:      {len(seen_urls)}')
    print(f'  Số job đã cào chi tiết:   {total_scraped}')
    print(f'  Bản ghi lưu/cập nhật DB:  {total_saved}')
    print(f'  File Excel đã xuất:       {excel_file}')
    print('=' * 70)
