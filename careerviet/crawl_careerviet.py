"""
careerviet/crawl_careerviet.py
───────────────────────────────
Script cào dữ liệu CareerViet.vn theo danh mục & tỉnh thành.
Tự động lưu vào SQL Server (bảng [careerviet]) và xuất file Excel careerviet_matrix_jobs.xlsx.
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
from parse_careerviet_job import parse_full_careerviet_job, create_driver, SOURCE_CAREERVIET
from provinces import get_careerviet_locations

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Các ngành nghề chính trên CareerViet
CAREERVIET_INDUSTRIES = [
    {'name': 'Kinh doanh / Bán hàng',   'url': 'https://careerviet.vn/viec-lam/ban-hang-kinh-doanh-c31-vi.html'},
    {'name': 'Marketing / PR',          'url': 'https://careerviet.vn/viec-lam/marketing-truyen-thong-quang-cao-c4-vi.html'},
    {'name': 'Tiếp thị trực tuyến',     'url': 'https://careerviet.vn/viec-lam/tiep-thi-truc-tuyen-c37-vi.html'},
    {'name': 'IT / Phần mềm',           'url': 'https://careerviet.vn/viec-lam/it-phan-mem-c63-vi.html'},
    {'name': 'Kế toán / Kiểm toán',    'url': 'https://careerviet.vn/viec-lam/ke-toan-kiem-toan-c2-vi.html'},
    {'name': 'Hành chính / Nhân sự',    'url': 'https://careerviet.vn/viec-lam/nhan-su-hanh-chinh-c27-vi.html'},
    {'name': 'Tài chính / Ngân hàng',   'url': 'https://careerviet.vn/viec-lam/tai-chinh-dau-tu-c58-vi.html'},
    {'name': 'Xây dựng / Kiến trúc',    'url': 'https://careerviet.vn/viec-lam/xay-dung-c15-vi.html'},
    {'name': 'Sản xuất / Vận hành',    'url': 'https://careerviet.vn/viec-lam/san-xuat-c14-vi.html'},
    {'name': 'Logistics / Kho vận',      'url': 'https://careerviet.vn/viec-lam/kho-van-vat-tu-cung-ung-c64-vi.html'},
    {'name': 'CSKH / Telesales',          'url': 'https://careerviet.vn/viec-lam/dich-vu-khach-hang-c60-vi.html'},
    {'name': 'Giáo dục / Đào tạo',     'url': 'https://careerviet.vn/viec-lam/giao-duc-dao-tao-c19-vi.html'},
    {'name': 'Bất động sản',            'url': 'https://careerviet.vn/viec-lam/bat-dong-san-c45-vi.html'},
]

CAREERVIET_CATEGORIES = CAREERVIET_INDUSTRIES + get_careerviet_locations(mode='34')

MAX_PAGES_PER_CATEGORY = 8
DELAY_MIN = 3.0
DELAY_MAX = 5.0


def extract_careerviet_urls_from_page(driver: uc.Chrome, page_url: str) -> list[str]:
    urls = []
    try:
        driver.get(page_url)
        time.sleep(random.uniform(2.5, 3.5))

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/vi/tim-viec-lam/' in href or '.35' in href:
                full_url = href if href.startswith('http') else 'https://careerviet.vn' + href
                clean_url = full_url.split('?')[0]
                if clean_url not in urls and 'careerviet.vn' in clean_url and '/nha-tuyen-dung/' not in clean_url:
                    urls.append(clean_url)
    except Exception as e:
        print(f'   [!] Lỗi khi lấy danh sách job từ CareerViet page: {e}')

    return urls


def main():
    print("=" * 70)
    print("🚀 BẮT ĐẦU CÀO DỮ LIỆU CAREERVIET (SQL SERVER + EXCEL)")
    print("=" * 70)

    # Khoi tao ket noi SQL Server
    db = JobDB()
    db.ensure_table(SOURCE_CAREERVIET)

    excel_file = os.path.join(os.path.dirname(__file__), 'careerviet_matrix_jobs.xlsx')
    root_excel_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'careerviet_matrix_jobs.xlsx'))

    driver = create_driver()
    all_scraped_records = []
    seen_urls = set()

    def save_excel(records=None):
        records = all_scraped_records if records is None else records
        if not records:
            return
        for path in (excel_file, root_excel_file):
            saved_path = save_records_to_excel(records, path)
            print(f"\n📊 Đã lưu {len(records)} dòng Excel: {saved_path}")

    try:
        for idx, cat in enumerate(CAREERVIET_CATEGORIES, 1):
            cat_name = cat['name']
            base_url = cat['url']
            print(f"\n[{idx}/{len(CAREERVIET_CATEGORIES)}] Danh mục: {cat_name}")

            for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                if page == 1:
                    page_url = base_url
                else:
                    if '-vi.html' in base_url:
                        page_url = base_url.replace('-vi.html', f'-p{page}-vi.html')
                    else:
                        page_url = f"{base_url}?page={page}"

                print(f"   📄 Trang {page}: {page_url}")
                job_urls = extract_careerviet_urls_from_page(driver, page_url)
                print(f"      -> Tìm thấy {len(job_urls)} job links.")

                if not job_urls:
                    print("      -> Không còn job nào, chuyển danh mục tiếp theo.")
                    break

                new_count = 0
                for j_idx, j_url in enumerate(job_urls, 1):
                    if j_url in seen_urls:
                        continue
                    seen_urls.add(j_url)

                    try:
                        record = parse_full_careerviet_job(driver, j_url)
                        if record and record.get('Công việc') != 'Không đề cập':
                            # Insert SQL Server
                            db.insert(SOURCE_CAREERVIET, record)
                            all_scraped_records.append(record)
                            new_count += 1
                            print(f"      [{j_idx}/{len(job_urls)}] Saved: {record['Công việc']} | {record['Nhà tuyển dụng']} | {record['Tỉnh thành']}")
                            if len(all_scraped_records) % 10 == 0:
                                save_excel()
                    except (DatabasePersistenceError, ExcelPersistenceError):
                        raise
                    except Exception as err:
                        print(f"      [!] Lỗi cào job {j_url}: {err}")

                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                print(f"   ✅ Đã lưu {new_count} job mới từ Trang {page}.")
                save_excel()

    except (DatabasePersistenceError, ExcelPersistenceError):
        raise
    except KeyboardInterrupt:
        print("\n⚠️ Người dùng hủy tiến trình.")
    except Exception as e:
        print(f"\n❌ Lỗi hệ thống: {e}")
    finally:
        try:
            driver.quit()
        except Exception as err:
            print(f"[!] Lỗi khi đóng Chrome CareerViet: {err}")
        finally:
            try:
                save_excel(db.get_all_records(SOURCE_CAREERVIET))
            finally:
                db.close()

    print("\n🎉 Hoàn tất cào dữ liệu CareerViet!")


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
