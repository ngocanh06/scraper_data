"""
vieclam24h/crawl_vieclam24h.py
───────────────────────────────
Script cào dữ liệu Vieclam24h.vn theo danh mục ngành nghề & tỉnh thành.
Tự động lưu vào SQL Server (bảng [dbo].[vieclam24h]) và xuất file Excel vieclam24h_matrix_jobs.xlsx.
"""

import sys
import io
import os
import re
import random
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import JobDB
from parse_vieclam24h_job import (
    parse_full_vieclam24h_job,
    DEFAULT_HEADERS,
    SOURCE_VIECLAM24H
)
from provinces import get_vieclam24h_locations

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Danh mục các ngành nghề chính trên Vieclam24h
VIECLAM24H_INDUSTRIES = [
    {'name': 'Bán hàng / Kinh doanh',                 'url': 'https://vieclam24h.vn/viec-lam-ban-hang-kinh-doanh-o13.html'},
    {'name': 'Marketing',                            'url': 'https://vieclam24h.vn/viec-lam-marketing-o12.html'},
    {'name': 'IT Phần mềm',                          'url': 'https://vieclam24h.vn/viec-lam-it-phan-mem-o8.html'},
    {'name': 'IT Phần cứng / Mạng',                  'url': 'https://vieclam24h.vn/viec-lam-it-phan-cung-mang-o7.html'},
    {'name': 'Kế toán',                              'url': 'https://vieclam24h.vn/viec-lam-ke-toan-o17.html'},
    {'name': 'Hành chính / Thư ký',                  'url': 'https://vieclam24h.vn/viec-lam-hanh-chinh-thu-ky-o1.html'},
    {'name': 'Nhân sự',                              'url': 'https://vieclam24h.vn/viec-lam-nhan-su-o22.html'},
    {'name': 'Tài chính / Đầu tư / Chứng khoán',     'url': 'https://vieclam24h.vn/viec-lam-tai-chinh-dau-tu-chung-khoan-o18.html'},
    {'name': 'Ngân hàng',                            'url': 'https://vieclam24h.vn/viec-lam-ngan-hang-o19.html'},
    {'name': 'Bán sỉ / Bán lẻ / Cửa hàng',           'url': 'https://vieclam24h.vn/viec-lam-ban-si-ban-le-quan-ly-cua-hang-o6.html'},
    {'name': 'Thu mua / Kho vận / Chuỗi cung ứng',   'url': 'https://vieclam24h.vn/viec-lam-thu-mua-kho-van-chuoi-cung-ung-o14.html'},
    {'name': 'Xuất Nhập Khẩu',                       'url': 'https://vieclam24h.vn/viec-lam-xuat-nhap-khau-o15.html'},
    {'name': 'Vận tải / Giao nhận',                  'url': 'https://vieclam24h.vn/viec-lam-van-tai-lai-xe-giao-nhan-o16.html'},
    {'name': 'Sản xuất / Lắp ráp / Chế biến',        'url': 'https://vieclam24h.vn/viec-lam-san-xuat-lap-rap-che-bien-o9.html'},
    {'name': 'Khách sạn / Nhà hàng / Du lịch',       'url': 'https://vieclam24h.vn/viec-lam-khach-san-nha-hang-du-lich-o5.html'},
    {'name': 'Thiết kế / Sáng tạo nghệ thuật',       'url': 'https://vieclam24h.vn/viec-lam-thiet-ke-sang-tao-nghe-thuat-o3.html'},
    {'name': 'Kiến trúc / Thiết kế nội ngoại thất',  'url': 'https://vieclam24h.vn/viec-lam-kien-truc-thiet-ke-noi-ngoai-that-o4.html'},
    {'name': 'Y tế / Chăm sóc sức khỏe',             'url': 'https://vieclam24h.vn/viec-lam-y-te-cham-soc-suc-khoe-o21.html'},
    {'name': 'Bảo hiểm',                             'url': 'https://vieclam24h.vn/viec-lam-bao-hiem-o23.html'},
    {'name': 'Thông tin / Truyền thông / Quảng cáo', 'url': 'https://vieclam24h.vn/viec-lam-thong-tin-truyen-thong-quang-cao-o24.html'},
    {'name': 'Vận hành / Bảo trì',                   'url': 'https://vieclam24h.vn/viec-lam-van-hanh-bao-tri-bao-duong-o10.html'},
    {'name': 'An ninh / Bảo vệ',                     'url': 'https://vieclam24h.vn/viec-lam-an-ninh-bao-ve-o2.html'},
]

VIECLAM24H_CATEGORIES = VIECLAM24H_INDUSTRIES + get_vieclam24h_locations(mode='34')

MAX_PAGES_PER_CATEGORY = 5
DELAY_JOB_MIN = 1.0
DELAY_JOB_MAX = 2.0


def extract_vieclam24h_job_urls(session: requests.Session, page_url: str) -> list[str]:
    """Trích xuất danh sách link bài đăng tuyển dụng từ 1 trang danh mục/tỉnh thành."""
    urls = []
    try:
        resp = session.get(page_url, headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"   [!] HTTP {resp.status_code} khi tải danh sách: {page_url}")
            return urls

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for a in soup.find_all('a', href=True):
            raw_href = a['href'].strip()
            clean_href = raw_href.split('?')[0]
            # Link chi tiết job trên Vieclam24h có dạng:
            # /{nganh-nghe}/{ten-job}-c{nganh_id}p{tinh_id}id{job_id}.html
            if re.search(r'id\d+\.html$', clean_href, re.IGNORECASE):
                if not clean_href.startswith('/viec-lam-') and 'dieu-khoan' not in clean_href and 'tin-tuc' not in clean_href:
                    full_url = clean_href if clean_href.startswith('http') else 'https://vieclam24h.vn' + clean_href
                    if full_url not in urls and 'vieclam24h.vn' in full_url:
                        urls.append(full_url)
    except Exception as e:
        print(f"   [!] Lỗi khi lấy danh sách job từ Vieclam24h page {page_url}: {e}")

    return urls


def export_excel(records: list[dict], local_path: str, root_path: str):
    """Xuất danh sách ra file Excel."""
    if not records:
        return
    df = pd.DataFrame(records)
    try:
        df.to_excel(local_path, index=False)
        print(f"  [Excel] Đã lưu {len(records)} jobs vào: {local_path}")
    except Exception as e:
        print(f"  [!] Lỗi lưu Excel cục bộ: {e}")

    try:
        df.to_excel(root_path, index=False)
        print(f"  [Excel] Đã đồng bộ sang thư mục gốc: {root_path}")
    except Exception as e:
        print(f"  [!] Lỗi lưu Excel gốc: {e}")


def main():
    print("=" * 70)
    print("🚀 BẮT ĐẦU CÀO DỮ LIỆU VIECLAM24H (SQL SERVER + EXCEL)")
    print("=" * 70)

    # Khởi tạo kết nối SQL Server
    db = JobDB()
    db.ensure_table(SOURCE_VIECLAM24H)

    excel_file = os.path.join(os.path.dirname(__file__), 'vieclam24h_matrix_jobs.xlsx')
    root_excel_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vieclam24h_matrix_jobs.xlsx'))

    session = requests.Session()
    all_scraped_records = []
    seen_urls = set()

    # Nạp các URL đã có trong Database để tránh cào lại
    try:
        cursor = db._conn.cursor()
        cursor.execute(f"SELECT url FROM [dbo].[{SOURCE_VIECLAM24H}]")
        for row in cursor.fetchall():
            seen_urls.add(row[0])
        print(f"[DB] Đã có {len(seen_urls):,} jobs trong bảng [{SOURCE_VIECLAM24H}] (sẽ bỏ qua khi trùng)")
    except Exception as e:
        print(f"[DB] Không đọc được danh sách URL cũ: {e}")

    total_categories = len(VIECLAM24H_CATEGORIES)

    try:
        for idx, cat in enumerate(VIECLAM24H_CATEGORIES, 1):
            cat_name = cat['name']
            base_url = cat['url']
            print(f"\n[{idx}/{total_categories}] Đang duyệt: {cat_name}")

            for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                page_url = base_url if page == 1 else f"{base_url}?page={page}"
                print(f"  -> Trang {page}/{MAX_PAGES_PER_CATEGORY}: {page_url}")

                job_urls = extract_vieclam24h_job_urls(session, page_url)
                print(f"     Tìm thấy {len(job_urls)} jobs trên trang.")

                if not job_urls:
                    print("     (Hết trang hoặc không có dữ liệu, chuyển danh mục tiếp theo)")
                    break

                for j_idx, j_url in enumerate(job_urls, 1):
                    if j_url in seen_urls:
                        continue
                    seen_urls.add(j_url)

                    try:
                        job_data = parse_full_vieclam24h_job(j_url, session=session)
                        
                        # Lưu vào SQL Server
                        db.insert(SOURCE_VIECLAM24H, job_data)
                        all_scraped_records.append(job_data)

                        print(f"     [+] ({len(all_scraped_records):,}) {job_data['Công việc'][:45]} | {job_data['Nhà tuyển dụng'][:30]} | {job_data['Tỉnh thành']}")
                    except Exception as je:
                        print(f"     [!] Lỗi cào job {j_url}: {je}")

                    time.sleep(random.uniform(DELAY_JOB_MIN, DELAY_JOB_MAX))

                # Xuất excel định kỳ mỗi 50 jobs
                if len(all_scraped_records) > 0 and len(all_scraped_records) % 50 == 0:
                    export_excel(all_scraped_records, excel_file, root_excel_file)

                time.sleep(random.uniform(1.5, 3.0))

    except KeyboardInterrupt:
        print("\n[!] Người dùng đã tạm dừng cào.")
    except Exception as e:
        print(f"\n[!] Có lỗi phát sinh trong quá trình cào: {e}")
    finally:
        db.close()
        export_excel(all_scraped_records, excel_file, root_excel_file)
        print(f"\n🎉 HOÀN TẤT! Đã cào thêm {len(all_scraped_records):,} jobs từ Vieclam24h.")


if __name__ == '__main__':
    main()
