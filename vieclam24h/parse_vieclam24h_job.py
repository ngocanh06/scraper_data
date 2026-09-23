"""
vieclam24h/parse_vieclam24h_job.py
───────────────────────────────────
Module bóc tách thông tin chi tiết việc làm từ Vieclam24h.vn.
Sử dụng JSON-LD Schema chuẩn (JobPosting) kết hợp HTML parsing dự phòng & chuẩn hóa tỉnh thành.
"""

import sys
import io
import os
import re
import json
import time
import random
import requests
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import JobDB
from provinces import normalize_province_name

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SOURCE_VIECLAM24H = 'vieclam24h'

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://vieclam24h.vn/'
}


def clean_html_text(raw_html: str) -> str:
    """Làm sạch HTML thành văn bản thuần có xuống dòng hợp lý."""
    if not raw_html:
        return 'Không đề cập'
    soup = BeautifulSoup(raw_html, 'html.parser')
    for li in soup.find_all('li'):
        li.insert_before('\n• ')
    for br in soup.find_all(['br', 'p', 'div', 'h1', 'h2', 'h3', 'h4']):
        br.insert_before('\n')
    text = soup.get_text()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines) if lines else 'Không đề cập'


def format_salary(salary_data) -> str:
    """Định dạng mức lương từ JSON-LD baseSalary."""
    if not salary_data:
        return 'Thoả thuận'
    if isinstance(salary_data, str):
        return salary_data.strip() or 'Thoả thuận'
    if isinstance(salary_data, dict):
        val = salary_data.get('value')
        currency = salary_data.get('currency', 'VND')
        if isinstance(val, (int, float)):
            if currency == 'VND' and val >= 1000000:
                return f"{val/1000000:.0f} triệu {currency}"
            return f"{val:,} {currency}"
        if isinstance(val, dict):
            min_v = val.get('minValue')
            max_v = val.get('maxValue')
            if min_v and max_v:
                if min_v >= 1000000 and max_v >= 1000000:
                    return f"{min_v/1000000:.0f} - {max_v/1000000:.0f} triệu {currency}"
                return f"{min_v:,} - {max_v:,} {currency}"
            elif min_v:
                if min_v >= 1000000:
                    return f"Từ {min_v/1000000:.0f} triệu {currency}"
                return f"Từ {min_v:,} {currency}"
            elif max_v:
                if max_v >= 1000000:
                    return f"Lên đến {max_v/1000000:.0f} triệu {currency}"
                return f"Lên đến {max_v:,} {currency}"
    return 'Thoả thuận'


def format_experience(exp_data) -> str:
    """Định dạng kinh nghiệm từ experienceRequirements."""
    if not exp_data:
        return 'Không yêu cầu kinh nghiệm'
    if isinstance(exp_data, str):
        return exp_data.strip()
    if isinstance(exp_data, dict):
        months = exp_data.get('monthsOfExperience')
        if months is not None:
            if months == 0:
                return 'Không yêu cầu kinh nghiệm'
            elif months < 12:
                return f"{months} tháng"
            elif months % 12 == 0:
                return f"{months//12} năm"
            else:
                return f"{months/12:.1f} năm"
    return 'Không yêu cầu kinh nghiệm'


def format_employment_type(emp_type: str) -> str:
    """Chuyển đổi enum employmentType sang tiếng Việt."""
    if not emp_type:
        return 'Toàn thời gian'
    emp_upper = str(emp_type).upper()
    if 'FULL' in emp_upper:
        return 'Toàn thời gian'
    elif 'PART' in emp_upper:
        return 'Bán thời gian'
    elif 'INTERN' in emp_upper:
        return 'Thực tập'
    elif 'CONTRACT' in emp_upper or 'TEMPORARY' in emp_upper:
        return 'Hợp đồng / Thời vụ'
    elif 'FREELANCE' in emp_upper:
        return 'Freelance'
    return emp_type


def parse_full_vieclam24h_job(job_url: str, session: requests.Session = None, timeout: int = 15) -> dict:
    """
    Bóc tách dữ liệu 1 tin tuyển dụng Vieclam24h.vn từ URL.
    Trả về dict khớp chính xác cấu trúc _FIELD_MAP của JobDB.
    """
    clean_url = job_url.split('?')[0]
    http = session or requests.Session()
    
    record = {
        'Ghi chú': clean_url,
        'Tỉnh thành': 'Không đề cập',
        'Loại hình công việc': 'Toàn thời gian',
        'Lĩnh vực/ngành nghề': 'Không đề cập',
        'Nhà tuyển dụng': 'Không đề cập',
        'Công việc': 'Không đề cập',
        'Chức vụ': 'Nhân viên',
        'Số lượng': 'Không đề cập',
        'Giới tính': 'Không yêu cầu',
        'Độ tuổi': 'Không yêu cầu',
        'Mức lương': 'Thoả thuận',
        'Thời gian làm việc': 'Giờ hành chính',
        'Địa điểm chi tiết': 'Không đề cập',
        'Mô tả công việc': 'Không đề cập',
        'Quyền lợi': 'Không đề cập',
        'Kinh nghiệm': 'Không yêu cầu kinh nghiệm',
        'Kỹ năng': 'Không đề cập',
        'Bằng cấp': 'Không yêu cầu',
        'Hạn nộp Hồ sơ': 'Không đề cập',
        'Thông tin liên hệ': 'Nộp hồ sơ trực tuyến trên Vieclam24h',
    }

    try:
        resp = http.get(clean_url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            print(f"   [!] HTTP {resp.status_code} khi tải {clean_url}")
            return record

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Trích xuất JSON-LD JobPosting
        json_ld = None
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    json_ld = data
                    break
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                            json_ld = item
                            break
                    if json_ld:
                        break
            except:
                continue

        if json_ld:
            # Tiêu đề công việc
            record['Công việc'] = json_ld.get('title') or record['Công việc']
            
            # Nhà tuyển dụng
            org = json_ld.get('hiringOrganization')
            if isinstance(org, dict):
                record['Nhà tuyển dụng'] = org.get('name') or record['Nhà tuyển dụng']
            elif isinstance(org, str):
                record['Nhà tuyển dụng'] = org
            
            # Chức vụ / Cấp bậc
            record['Chức vụ'] = json_ld.get('occupationalCategory') or record['Chức vụ']
            
            # Số lượng
            if json_ld.get('totalJobOpenings'):
                record['Số lượng'] = str(json_ld.get('totalJobOpenings'))
            
            # Bằng cấp
            record['Bằng cấp'] = json_ld.get('qualifications') or record['Bằng cấp']
            
            # Lĩnh vực / Ngành nghề
            record['Lĩnh vực/ngành nghề'] = json_ld.get('industry') or record['Lĩnh vực/ngành nghề']
            
            # Loại hình
            record['Loại hình công việc'] = format_employment_type(json_ld.get('employmentType'))
            
            # Mức lương
            record['Mức lương'] = format_salary(json_ld.get('baseSalary'))
            
            # Kinh nghiệm
            record['Kinh nghiệm'] = format_experience(json_ld.get('experienceRequirements'))
            
            # Kỹ năng
            skills_val = json_ld.get('skills')
            if isinstance(skills_val, list):
                record['Kỹ năng'] = ', '.join(skills_val)
            elif isinstance(skills_val, str):
                record['Kỹ năng'] = skills_val
            
            # Hạn nộp
            vt = json_ld.get('validThrough')
            if vt:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', vt)
                record['Hạn nộp Hồ sơ'] = date_match.group(1) if date_match else vt
            
            # Mô tả công việc
            desc_html = json_ld.get('description', '')
            record['Mô tả công việc'] = clean_html_text(desc_html)
            
            # Quyền lợi
            benefits_html = json_ld.get('jobBenefits', '')
            record['Quyền lợi'] = clean_html_text(benefits_html)
            
            # Địa điểm làm việc & Tỉnh thành
            loc = json_ld.get('jobLocation')
            locations_list = loc if isinstance(loc, list) else ([loc] if loc else [])
            addr_details = []
            regions = []
            for item in locations_list:
                if isinstance(item, dict):
                    addr = item.get('address', {})
                    if isinstance(addr, dict):
                        street = addr.get('streetAddress', '')
                        locality = addr.get('addressLocality', '')
                        region = addr.get('addressRegion', '')
                        full_addr = ', '.join(filter(None, [street, locality, region]))
                        if full_addr and full_addr not in addr_details:
                            addr_details.append(full_addr)
                        if region and region not in regions:
                            regions.append(region)
            
            if addr_details:
                record['Địa điểm chi tiết'] = ' | '.join(addr_details)
            if regions:
                record['Tỉnh thành'] = normalize_province_name(', '.join(regions))

        # 2. HTML Fallback nếu JSON-LD thiếu trường
        if record['Công việc'] == 'Không đề cập':
            h1 = soup.find('h1')
            if h1:
                record['Công việc'] = h1.get_text(strip=True)

        if record['Nhà tuyển dụng'] == 'Không đề cập':
            company_el = soup.select_one('a[href*="/danh-sach-tin-tuyen-dung-"], div[class*="company-name"], h2[class*="company"]')
            if company_el:
                record['Nhà tuyển dụng'] = company_el.get_text(strip=True)

        if record['Tỉnh thành'] == 'Không đề cập' or not record['Tỉnh thành']:
            # Thử tìm text địa điểm trong DOM
            loc_el = soup.find(string=re.compile(r'Địa điểm làm việc|Khu vực', re.I))
            if loc_el and loc_el.parent:
                record['Tỉnh thành'] = normalize_province_name(loc_el.parent.get_text(strip=True))

        # Chuẩn hoá Tỉnh thành lần cuối
        record['Tỉnh thành'] = normalize_province_name(record['Tỉnh thành'])

    except Exception as e:
        print(f"   [!] Lỗi khi bóc tách Vieclam24h ({clean_url}): {e}")

    return record


if __name__ == '__main__':
    test_url = 'https://vieclam24h.vn/it-phan-mem/search-engine-optimization-seo-executive-c8p122id200909097.html'
    print(f"--- Đang test bóc tách: {test_url} ---")
    data = parse_full_vieclam24h_job(test_url)
    for k, v in data.items():
        val_preview = str(v)[:80] + '...' if len(str(v)) > 80 else str(v)
        print(f"  {k:22}: {val_preview}")
