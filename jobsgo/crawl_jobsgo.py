"""
jobsgo/crawl_jobsgo.py
───────────────────────
Script cào dữ liệu JobsGO.vn theo ma trận danh mục/tỉnh thành.
Tự động lưu vào SQL Server (bảng [jobsgo]) và xuất file Excel jobsgo_matrix_jobs.xlsx.
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

# Thêm thư mục gốc vào python path để import db_manager
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import JobDB
from parse_jobsgo_job import parse_full_jobsgo_job, create_driver, SOURCE_JOBSGO
from provinces import get_jobsgo_locations

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Các ngành nghề chính trên JobsGO
JOBSGO_INDUSTRIES = [
    {'name': 'Kinh doanh / Bán hàng',  'url': 'https://jobsgo.vn/viec-lam-kinh-doanh-ban-hang.html'},
    {'name': 'Marketing / PR',           'url': 'https://jobsgo.vn/viec-lam-marketing-pr-quang-cao.html'},
    {'name': 'IT / Phần mềm',          'url': 'https://jobsgo.vn/viec-lam-cong-nghe-thong-tin.html'},
    {'name': 'Kế toán / Kiểm toán',   'url': 'https://jobsgo.vn/viec-lam-ke-toan-kiem-toan.html'},
    {'name': 'Hành chính / Nhân sự',   'url': 'https://jobsgo.vn/viec-lam-nhan-su.html'},
    {'name': 'Tài chính / Ngân hàng',  'url': 'https://jobsgo.vn/viec-lam-tai-chinh-ngan-hang-chung-khoan.html'},
    {'name': 'Xây dựng / Kiến trúc',   'url': 'https://jobsgo.vn/viec-lam-xay-dung-kien-truc-noi-that.html'},
    {'name': 'Sản xuất / Vận hành',   'url': 'https://jobsgo.vn/viec-lam-san-xuat.html'},
    {'name': 'Logistics / Kho vận',     'url': 'https://jobsgo.vn/viec-lam-logistics-xuat-nhap-khau.html'},
    {'name': 'CSKH / Telesales',         'url': 'https://jobsgo.vn/viec-lam-cham-soc-khach-hang.html'},
    {'name': 'Giáo dục / Đào tạo',    'url': 'https://jobsgo.vn/viec-lam-giao-duc-dao-tao.html'},
    {'name': 'Y tế / Sức khỏe',       'url': 'https://jobsgo.vn/viec-lam-y-te-duoc.html'},
    {'name': 'Bất động sản',           'url': 'https://jobsgo.vn/viec-lam-bat-dong-san.html'},
]

# Tự động kết hợp Ngành nghề + Đầy đủ Tỉnh thành Việt Nam (mode '34' hoặc 'all')
JOBSGO_CATEGORIES = JOBSGO_INDUSTRIES + get_jobsgo_locations(mode='34')


MAX_PAGES_PER_CATEGORY = 8
DELAY_MIN = 3.0
DELAY_MAX = 5.0


def extract_jobsgo_urls_from_page(driver: uc.Chrome, page_url: str) -> list[str]:
    urls = []
    try:
        driver.get(page_url)
        time.sleep(random.uniform(2.5, 3.5))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # CHỈ LẤY CÁC THẺ <a> NẰM TRONG TIÊU ĐỀ JOB (h2 a, h3 a, .job-title a)
        for a in soup.select('h2 a, h3 a, .job-title a, a.job-item-title'):
            href = a.get('href', '')
            if '/viec-lam/' in href and re.search(r'-\d+\.html', href):
                if 'cong-ty' not in href.lower() and '/tuyen-dung/' not in href:
                    full_url = href if href.startswith('http') else 'https://jobsgo.vn' + href
                    clean_url = full_url.split('?')[0]
                    if clean_url not in urls:
                        urls.append(clean_url)
    except Exception as e:
        print(f'   [!] Lỗi khi lấy danh sách job từ JobsGO search page: {e}')

    return urls


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

    print('=' * 70)
    print('🚀 [JOBSGO] BẮT ĐẦU CÀO DỮ LIỆU JOBSGO.VN')
    print('=' * 70)

    db = JobDB()
    db.ensure_table(SOURCE_JOBSGO)

    print('[JobsGO Chrome] Đang khởi động undetected-chromedriver ngầm...')
    driver = create_driver()
    print('[JobsGO Chrome] Chrome đã sẵn sàng!\n')

    total_scraped = 0
    total_saved = 0
    seen_urls = set()
    dataset = []
    excel_file = os.path.join(os.path.dirname(__file__), 'jobsgo_matrix_jobs.xlsx')

    def save_excel():
        if dataset:
            df = pd.DataFrame(dataset)
            try:
                df.to_excel(excel_file, index=False)
                print(f'   📊 [JobsGO Excel] Đã lưu {len(dataset)} việc làm vào {excel_file}')
            except PermissionError:
                alt = os.path.join(os.path.dirname(__file__), 'jobsgo_matrix_jobs_out.xlsx')
                df.to_excel(alt, index=False)
                print(f'   📊 [JobsGO Excel] File {excel_file} đang mở, đã lưu vào {alt}')
            except Exception as e:
                print(f'   [!] Lỗi lưu Excel JobsGO: {e}')

    try:
        for cat in JOBSGO_CATEGORIES:
            print(f'\n📌 [JobsGO: {cat["name"]}]')
            base_url = cat['url']

            for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                p_url = f"{base_url}?p={page}" if page > 1 else base_url
                print(f'   📄 Trang {page}/{MAX_PAGES_PER_CATEGORY}: {p_url}')

                job_urls = extract_jobsgo_urls_from_page(driver, p_url)
                if not job_urls:
                    print('   [i] Không còn job nào ở trang này. Chuyển danh mục tiếp theo.')
                    break

                print(f'   → Tìm thấy {len(job_urls)} việc làm.')

                for idx, url in enumerate(job_urls, start=1):
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    total_scraped += 1

                    print(f'      [{total_scraped}] Cào JobsGO detail: {url[-65:]}')
                    record = parse_full_jobsgo_job(driver, url, stt_index=total_scraped)

                    if record:
                        dataset.append(record)
                        ok = db.insert(SOURCE_JOBSGO, record)
                        if ok:
                            total_saved += 1
                            print(f'         ✅ [JobsGO DB UPSERT] {record["Công việc"][:35]} | {record["Nhà tuyển dụng"][:25]} | {record["Mức lương"]}')
                    else:
                        print(f'         ❌ Không parse được job JobsGO này.')

                    if len(dataset) % 10 == 0:
                        save_excel()

                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                save_excel()
                time.sleep(random.uniform(2.0, 4.0))

    except KeyboardInterrupt:
        print('\n[!] Người dùng dừng JobsGO scraper.')
    except Exception as e:
        print(f'\n[!] Lỗi JobsGO scraper: {e}')
    finally:
        save_excel()
        try:
            driver.quit()
        except Exception:
            pass
        print('\n[JobsGO Chrome] Đã đóng Chrome.')
        db.close()

    print('\n' + '=' * 70)
    print('=== TỔNG KẾT JOBSGO SCRAPER ===')
    print(f'  Tổng số URL đã quét:      {len(seen_urls)}')
    print(f'  Số job đã cào chi tiết:   {total_scraped}')
    print(f'  Bản ghi lưu/cập nhật DB:  {total_saved}')
    print(f'  File Excel đã xuất:       {excel_file}')
    print('=' * 70)
