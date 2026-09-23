"""
vietnamworks/crawl_vietnamworks.py
───────────────────────────────────
Script cào dữ liệu VietnamWorks.com theo danh mục/tỉnh thành.
Tự động lưu vào SQL Server (bảng [vietnamworks]) và xuất file Excel vietnamworks_matrix_jobs.xlsx.
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
from db_manager import JobDB
from parse_vietnamworks_job import parse_full_vietnamworks_job, create_driver, SOURCE_VIETNAMWORKS
from provinces import get_vietnamworks_locations

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Tự động lấy danh sách tỉnh thành VietnamWorks từ provinces.py (mode '34' hoặc 'all')
VNW_CATEGORIES = get_vietnamworks_locations(mode='34')


MAX_PAGES_PER_CATEGORY = 8
DELAY_MIN = 3.0
DELAY_MAX = 5.0


def extract_vnw_urls_from_page(driver: uc.Chrome, page_url: str) -> list[str]:
    urls = []
    try:
        driver.get(page_url)
        time.sleep(random.uniform(2.5, 3.5))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '-jv/' in href or '-jv?' in href or '-jd/' in href or '-jv' in href:
                full_url = href if href.startswith('http') else 'https://www.vietnamworks.com' + href
                clean_url = full_url.split('?')[0]
                if clean_url not in urls and 'vietnamworks.com' in clean_url:
                    urls.append(clean_url)
    except Exception as e:
        print(f'   [!] Lỗi khi lấy danh sách job từ VietnamWorks page: {e}')

    return urls


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

    print('=' * 70)
    print('🚀 [VIETNAMWORKS] BẮT ĐẦU CÀO DỮ LIỆU VIETNAMWORKS.COM')
    print('=' * 70)

    db = JobDB()
    db.ensure_table(SOURCE_VIETNAMWORKS)

    print('[VietnamWorks Chrome] Đang khởi động undetected-chromedriver...')
    driver = create_driver()
    print('[VietnamWorks Chrome] Chrome đã sẵn sàng!\n')

    total_scraped = 0
    total_saved = 0
    seen_urls = set()
    dataset = []
    excel_file = os.path.join(os.path.dirname(__file__), 'vietnamworks_matrix_jobs.xlsx')

    def save_excel():
        if dataset:
            df = pd.DataFrame(dataset)
            try:
                df.to_excel(excel_file, index=False)
                print(f'   📊 [VietnamWorks Excel] Đã lưu {len(dataset)} việc làm vào {excel_file}')
            except PermissionError:
                alt = os.path.join(os.path.dirname(__file__), 'vietnamworks_matrix_jobs_out.xlsx')
                df.to_excel(alt, index=False)
                print(f'   📊 [VietnamWorks Excel] File {excel_file} đang mở, đã lưu vào {alt}')
            except Exception as e:
                print(f'   [!] Lỗi lưu Excel VietnamWorks: {e}')

    try:
        for cat in VNW_CATEGORIES:
            print(f'\n📌 [VietnamWorks: {cat["name"]}]')
            base_url = cat['url']

            for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                p_url = f"{base_url}?page={page}" if page > 1 else base_url
                print(f'   📄 Trang {page}/{MAX_PAGES_PER_CATEGORY}: {p_url}')

                job_urls = extract_vnw_urls_from_page(driver, p_url)
                if not job_urls:
                    print('   [i] Không còn job nào ở trang này. Chuyển danh mục tiếp theo.')
                    break

                print(f'   → Tìm thấy {len(job_urls)} việc làm.')

                for idx, url in enumerate(job_urls, start=1):
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    total_scraped += 1

                    print(f'      [{total_scraped}] Cào VietnamWorks detail: {url[-65:]}')
                    record = parse_full_vietnamworks_job(driver, url, stt_index=total_scraped)

                    if record:
                        dataset.append(record)
                        ok = db.insert(SOURCE_VIETNAMWORKS, record)
                        if ok:
                            total_saved += 1
                            print(f'         ✅ [VNW DB UPSERT] {record["Công việc"][:35]} | {record["Nhà tuyển dụng"][:25]} | {record["Mức lương"]}')
                    else:
                        print(f'         ❌ Không parse được job VietnamWorks này.')

                    if len(dataset) % 10 == 0:
                        save_excel()

                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                save_excel()
                time.sleep(random.uniform(2.0, 4.0))

    except KeyboardInterrupt:
        print('\n[!] Người dùng dừng VietnamWorks scraper.')
    except Exception as e:
        print(f'\n[!] Lỗi VietnamWorks scraper: {e}')
    finally:
        save_excel()
        try:
            driver.quit()
        except Exception:
            pass
        print('\n[VietnamWorks Chrome] Đã đóng Chrome.')
        db.close()

    print('\n' + '=' * 70)
    print('=== TỔNG KẾT VIETNAMWORKS SCRAPER ===')
    print(f'  Tổng số URL đã quét:      {len(seen_urls)}')
    print(f'  Số job đã cào chi tiết:   {total_scraped}')
    print(f'  Bản ghi lưu/cập nhật DB:  {total_saved}')
    print(f'  File Excel đã xuất:       {excel_file}')
    print('=' * 70)
