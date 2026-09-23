"""
careerviet/parse_careerviet_job.py
───────────────────────────────────
Module bóc tách thông tin chi tiết việc làm từ CareerViet.vn (trước đây là CareerBuilder.vn).
Kết hợp JSON-LD Schema (JobPosting) + HTML Parsing + Chuẩn hoá Tỉnh thành.
"""

import sys
import io
import os
import re
import json
import time
import random
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import JobDB
from provinces import normalize_province_name

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SOURCE_CAREERVIET = 'careerviet'
PAGE_TIMEOUT      = 20
JS_WAIT           = 4

_CHROMEDRIVER_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
    'chromedriver_151.exe'
)


def create_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--window-position=-2400,-2400')
    options.add_argument('--lang=vi-VN')

    driver = uc.Chrome(
        options=options,
        headless=False,
        use_subprocess=False,
    )
    return driver


def clean_text(text: str) -> str:
    if not text:
        return 'Không đề cập'
    cleaned = re.sub(r'\s+', ' ', text).strip()
    return cleaned if cleaned else 'Không đề cập'


def parse_full_careerviet_job(driver: uc.Chrome, job_url: str) -> dict:
    """
    Truy cập và bóc tách dữ liệu từ trang chi tiết việc làm trên CareerViet.vn.
    Trả về dict tương thích với schema hệ thống.
    """
    record = {
        'Ghi chú': job_url,
        'Tỉnh thành': 'Toàn Quốc',
        'Loại hình công việc': 'Toàn thời gian',
        'Lĩnh vực/ngành nghề': 'Không đề cập',
        'Nhà tuyển dụng': 'Không đề cập',
        'Công việc': 'Không đề cập',
        'Chức vụ': 'Nhân viên',
        'Số lượng': 'Không đề cập',
        'Giới tính': 'Không đề cập',
        'Độ tuổi': 'Không đề cập',
        'Mức lương': 'Thỏa thuận',
        'Thời gian làm việc': 'Không đề cập',
        'Địa điểm chi tiết': 'Không đề cập',
        'Mô tả công việc': 'Không đề cập',
        'Quyền lợi': 'Không đề cập',
        'Kinh nghiệm': 'Không đề cập',
        'Kỹ năng': 'Không đề cập',
        'Bằng cấp': 'Không đề cập',
        'Hạn nộp Hồ sơ': 'Không đề cập',
        'Thông tin liên hệ': 'Không đề cập'
    }

    try:
        driver.get(job_url)
        time.sleep(JS_WAIT)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 1. Thử lấy từ JSON-LD Schema
        for s in soup.find_all('script', type='application/ld+json'):
            if not s.string:
                continue
            try:
                data = json.loads(s.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    if data.get('title'):
                        record['Công việc'] = clean_text(data['title'])
                    
                    org = data.get('hiringOrganization')
                    if isinstance(org, dict) and org.get('name'):
                        record['Nhà tuyển dụng'] = clean_text(org['name'])
                    
                    sal = data.get('baseSalary')
                    if isinstance(sal, dict):
                        val = sal.get('value', {})
                        if isinstance(val, dict) and val.get('value'):
                            record['Mức lương'] = clean_text(str(val['value']))
                    
                    loc = data.get('jobLocation')
                    if isinstance(loc, dict):
                        addr = loc.get('address', {})
                        if isinstance(addr, dict):
                            raw_addr = addr.get('streetAddress') or addr.get('addressRegion') or addr.get('addressLocality')
                            if raw_addr:
                                record['Địa điểm chi tiết'] = clean_text(raw_addr)
                                record['Tỉnh thành'] = normalize_province_name(raw_addr)

                    valid_through = data.get('validThrough')
                    if valid_through:
                        record['Hạn nộp Hồ sơ'] = clean_text(valid_through.split('T')[0])
                    break
            except Exception:
                pass

        # 2. Bóc tách / Bổ sung từ HTML Elements
        if record['Công việc'] == 'Không đề cập':
            h1 = soup.select_one('h1.title, .job-header h1, .job-desc h1, h1')
            if h1:
                record['Công việc'] = clean_text(h1.get_text())

        if record['Nhà tuyển dụng'] in ('Không đề cập', 'Bảo mật'):
            company_el = soup.select_one('.employer-name, a.employer, .company-name, .job-header .company')
            if company_el:
                record['Nhà tuyển dụng'] = clean_text(company_el.get_text())

        # Chi tiết info list (Lương, Ngành nghề, Cấp bậc, Hình thức, Bằng cấp, Kinh nghiệm...)
        info_items = soup.select('.detail-box li, .job-detail-info li, ul.info-item li, .detail-box p, .detail-row li, .detail-row p')
        for item in info_items:
            txt = clean_text(item.get_text(separator=' '))
            if 'Ngành nghề' in txt or 'Ngành' in txt:
                record['Lĩnh vực/ngành nghề'] = clean_text(re.sub(r'^(Ngành nghề|Ngành)\s*:?\s*', '', txt, flags=re.IGNORECASE))
            elif 'Cấp bậc' in txt:
                val = clean_text(re.sub(r'^Cấp bậc\s*:?\s*', '', txt, flags=re.IGNORECASE))
                if val:
                    record['Chức vụ'] = val
            elif 'Hình thức' in txt:
                raw_ht = clean_text(re.sub(r'^Hình thức\s*:?\s*', '', txt, flags=re.IGNORECASE))
                ht_low = raw_ht.lower()
                if any(k in ht_low for k in ['chính thức', 'toàn thời', 'full-time', 'fulltime']):
                    record['Loại hình công việc'] = 'Toàn thời gian'
                elif any(k in ht_low for k in ['bán thời', 'part-time', 'parttime']):
                    record['Loại hình công việc'] = 'Bán thời gian'
                elif any(k in ht_low for k in ['từ xa', 'remote', 'online']):
                    record['Loại hình công việc'] = 'Làm việc từ xa'
                elif any(k in ht_low for k in ['thực tập', 'intern']):
                    record['Loại hình công việc'] = 'Thực tập'
                elif any(k in ht_low for k in ['tự do', 'freelance']):
                    record['Loại hình công việc'] = 'Freelance'
                elif raw_ht and raw_ht != 'Không đề cập':
                    record['Loại hình công việc'] = raw_ht
            elif 'Kinh nghiệm' in txt:
                record['Kinh nghiệm'] = clean_text(re.sub(r'^Kinh nghiệm\s*:?\s*', '', txt, flags=re.IGNORECASE))
            elif 'Bằng cấp' in txt:
                record['Bằng cấp'] = clean_text(re.sub(r'^Bằng cấp\s*:?\s*', '', txt, flags=re.IGNORECASE))
            elif 'Độ tuổi' in txt:
                record['Độ tuổi'] = clean_text(re.sub(r'^Độ tuổi\s*:?\s*', '', txt, flags=re.IGNORECASE))
            elif 'Giới tính' in txt:
                record['Giới tính'] = clean_text(re.sub(r'^Giới tính\s*:?\s*', '', txt, flags=re.IGNORECASE))
            elif 'Lương' in txt and record['Mức lương'] == 'Thỏa thuận':
                record['Mức lương'] = clean_text(re.sub(r'^Lương\s*:?\s*', '', txt, flags=re.IGNORECASE))
            elif ('Hồ Chí Minh' in txt or 'Hà Nội' in txt or 'Đà Nẵng' in txt or 'Bình Dương' in txt) and record['Tỉnh thành'] == 'Toàn Quốc':
                record['Tỉnh thành'] = normalize_province_name(txt)
                record['Địa điểm chi tiết'] = txt

        # Tổng hợp Thông tin liên hệ
        contact_parts = []
        _email_pat = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        _phone_pat = re.compile(r'(?:\+84|0)(?:3[2-9]|5[2689]|7[06-9]|8[1-9]|9[0-9])\d{7}\b')
        _ex_doms = ['topcv.vn', 'jobsgo.vn', 'vietnamworks.com', 'careerviet.vn', 'careerbuilder.vn', 'schema.org', 'w3.org', 'google.com', 'facebook.com']
        
        full_text = f"{record['Mô tả công việc']} {record['Quyền lợi']} {record['Kỹ năng']}"
        _found_emails = list(set([e for e in _email_pat.findall(full_text) if not any(d in e.lower() for d in _ex_doms)]))
        _found_phones = list(set(_phone_pat.findall(full_text)))
        
        if _found_emails:
            contact_parts.append(f"Email: {', '.join(_found_emails[:2])}")
        if _found_phones:
            contact_parts.append(f"SĐT: {', '.join(_found_phones[:2])}")
        if record['Địa điểm chi tiết'] != 'Không đề cập':
            contact_parts.append(f"Địa chỉ: {record['Địa điểm chi tiết'][:100]}")
            
        record['Thông tin liên hệ'] = ' | '.join(contact_parts) if contact_parts else 'Nộp CV trực tiếp qua hệ thống CareerViet'

    except Exception as e:
        print(f"   [!] Lỗi khi bóc tách CareerViet job detail ({job_url}): {e}")

    return record


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()

    test_url = 'https://careerviet.vn/vi/tim-viec-lam/truong-nhom-booking-koc-kol-tieng-trung-gap.35C78F1A.html'
    print(f"🧪 Test parsing CareerViet job detail: {test_url}")
    drv = create_driver()
    try:
        data = parse_full_careerviet_job(drv, test_url)
        print("\n--- KẾT QUẢ BÓC TÁCH ---")
        for k, v in data.items():
            print(f"  • {k}: {str(v)[:100]}")
    finally:
        drv.quit()
