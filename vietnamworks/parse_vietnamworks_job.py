"""
vietnamworks/parse_vietnamworks_job.py
───────────────────────────────────────
Module bóc tách thông tin chi tiết việc làm từ VietnamWorks.com.
Sử dụng JSON-LD Schema chuẩn + DOM parsing fallback.
"""

import sys
import io
import os
import re
import json
import time
from bs4 import BeautifulSoup

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import JobDB

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SOURCE_VIETNAMWORKS = 'vietnamworks'
PAGE_TIMEOUT        = 20
JS_WAIT             = 4

VIETNAM_PROVINCES = [
    "Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Bình Dương", "Đồng Nai", "Bắc Ninh", "Hải Phòng",
    "Cần Thơ", "Quảng Ninh", "Bà Rịa - Vũng Tàu", "An Giang", "Bình Định", "Bình Phước",
    "Bình Thuận", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bến Tre", "Cao Bằng", "Cà Mau",
    "Đắc Lắc", "Đắk Lắk", "Đắk Nông", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam", "Hà Tĩnh",
    "Hải Dương", "Hậu Giang", "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang",
    "Kon Tum", "Lai Châu", "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định",
    "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình",
    "Quảng Nam", "Quảng Ngãi", "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh",
    "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang",
    "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái", "Toàn quốc"
]

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


def clean_location(raw_text: str) -> str:
    """Rút trích tên Tỉnh/Thành phố hợp lệ."""
    if not raw_text or raw_text == 'Không đề cập':
        return 'Không đề cập'
    
    low = raw_text.lower()
    found = []
    for prov in VIETNAM_PROVINCES:
        if prov.lower() in low:
            if prov not in found:
                found.append(prov)
    
    if len(found) > 3:
        return 'Toàn quốc'
    
    if found:
        return ', '.join(found)
    
    return 'Không đề cập'


def clean_badge(val: str, valid_options: list, default: str) -> str:
    if not val or val == 'Không đề cập':
        return default
    for opt in valid_options:
        if opt.lower() in val.lower():
            return opt
    return default


def parse_full_vietnamworks_job(driver: uc.Chrome, url: str, stt_index: int) -> dict | None:
    if not ('-jv' in url or '-jd' in url or '/viec-lam/' in url or 'vietnamworks.com/' in url):
        print(f'  [!] Bỏ qua URL không phải tin tuyển dụng: {url}')
        return None

    try:
        driver.get(url)

        try:
            WebDriverWait(driver, PAGE_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, 'h1'))
            )
        except TimeoutException:
            print(f'  [!] Timeout khi chờ trang VietnamWorks: {url}')
            return None

        time.sleep(JS_WAIT)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 1. Parse JSON-LD Schema
        json_data = None
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    json_data = data
                    break
            except Exception:
                pass

        def s(value: str, maxlen: int = 200) -> str:
            return re.sub(r'\s+', ' ', str(value).strip())[:maxlen] if value else ''

        def get_text_multi(*selectors, default='Không đề cập') -> str:
            for sel in selectors:
                el = soup.select_one(sel)
                if el:
                    t = el.get_text(strip=True)
                    if t and len(t) < 300:
                        return t
            return default

        # ── 1. Công việc ────────────────────────────────
        job_title = 'Không đề cập'
        if json_data and json_data.get('title'):
            job_title = json_data['title']
        if job_title == 'Không đề cập':
            job_title = get_text_multi('h1', '.job-title', '[class*="title"]')

        # ── 2. Nhà tuyển dụng ────────────────────────────
        company = 'Không đề cập'
        if json_data and isinstance(json_data.get('hiringOrganization'), dict):
            company = json_data['hiringOrganization'].get('name', 'Không đề cập')
        if company == 'Không đề cập':
            company = get_text_multi('.company-name', 'a[href*="/nha-tuyen-dung/"]', 'a[href*="/companies/"]')

        # ── 3. Mức lương ─────────────────────────────────
        salary = 'Thỏa thuận'
        if json_data and isinstance(json_data.get('baseSalary'), dict):
            bs = json_data['baseSalary']
            if isinstance(bs.get('value'), dict):
                v = bs['value'].get('value')
                if v:
                    salary = str(v)
            elif bs.get('value'):
                salary = str(bs['value'])
        if salary == 'Thỏa thuận' or not salary:
            sal_dom = get_text_multi('.salary', '[class*="salary"]', '.job-salary')
            if any(k in sal_dom.lower() for k in ['trỉệu', 'triệu', '$', 'usd', 'thỏa thuận', 'lương']):
                salary = sal_dom

        # ── 4. Tỉnh thành & Địa chỉ ──────────────────────
        raw_location = 'Không đề cập'
        address_detail = 'Không đề cập'

        if json_data and isinstance(json_data.get('jobLocation'), dict):
            addr = json_data['jobLocation'].get('address', {})
            if isinstance(addr, dict):
                raw_location = addr.get('addressRegion') or addr.get('addressLocality') or 'Không đề cập'
                address_detail = addr.get('streetAddress', 'Không đề cập')

        if raw_location == 'Không đề cập':
            raw_location = get_text_multi('.location', '[class*="location"]', '.company-address')

        location = clean_location(raw_location)
        if address_detail == 'Không đề cập':
            address_detail = location

        # ── 5. Mô tả công việc & Quyền lợi ────────────────
        description = 'Không đề cập'
        benefits = 'Không đề cập'

        if json_data:
            if json_data.get('description'):
                description = BeautifulSoup(json_data['description'], 'html.parser').get_text('\n', strip=True)
            if json_data.get('jobBenefits'):
                benefits = BeautifulSoup(json_data['jobBenefits'], 'html.parser').get_text('\n', strip=True)

        if description == 'Không đề cập':
            desc_el = soup.select_one('.job-description, [class*="description"]')
            if desc_el:
                description = desc_el.get_text(strip=True)

        # ── 6. Lĩnh vực / Ngành nghề ─────────────────────
        category = 'Không đề cập'
        if json_data and json_data.get('industry'):
            category = str(json_data['industry'])
        if category == 'Không đề cập':
            category = get_text_multi('.category-name', '.breadcrumb li:last-child a', '[class*="category"]')

        # ── 7. Kỹ năng ──────────────────────────────────
        skills = 'Không đề cập'
        if json_data and json_data.get('skills'):
            skills = str(json_data['skills'])
        if skills == 'Không đề cập':
            skill_tags = [el.get_text(strip=True) for el in soup.select('[class*="skill"] a, .tag-item, .skill-name')]
            skills = ', '.join(skill_tags) if skill_tags else 'Không đề cập'

        # ── 8. Hạn nộp ──────────────────────────────────
        deadline = 'Không đề cập'
        if json_data and json_data.get('validThrough'):
            vt = json_data['validThrough']
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', vt)
            if match:
                deadline = f"{match.group(3)}/{match.group(2)}/{match.group(1)}"

        # ── 9. Cấp bậc, Bằng cấp, Kinh nghiệm, Số lượng, v.v. ───────
        html_str = driver.page_source

        # 9.1 Loại hình công việc
        emp_type_raw = json_data.get('employmentType', '') if json_data else ''
        if not emp_type_raw:
            _emp_m = re.search(r'typeWorkingId\\?["\']?\s*:\s*(\d+)', html_str)
            if _emp_m and _emp_m.group(1) == '1':
                emp_type_raw = 'FULL_TIME'
        if 'FULL_TIME' in str(emp_type_raw).upper() or 'chính thức' in str(emp_type_raw).lower():
            job_type = 'Toàn thời gian'
        elif 'PART_TIME' in str(emp_type_raw).upper():
            job_type = 'Bán thời gian'
        else:
            job_type = clean_badge(str(emp_type_raw), ["Toàn thời gian", "Bán thời gian", "Thực tập", "FULL_TIME", "PART_TIME"], "Toàn thời gian")

        # 9.2 Số lượng tuyển
        quantity = 'Không đề cập'
        _qty_m = re.search(r'numberOfRecruits\\?["\']?\s*:\s*(\d+)', html_str)
        if _qty_m:
            q_val = int(_qty_m.group(1))
            if q_val > 0:
                quantity = f"{q_val} người"
        if quantity == 'Không đề cập':
            _qty_dom = re.search(r's[ốo]\s*l[ượ]ng\s*(?:tuy[ển]*)*[\s:]*(\d+)', soup.get_text(), re.I)
            if _qty_dom:
                quantity = f"{_qty_dom.group(1)} người"

        # 9.3 Kinh nghiệm
        experience = 'Không yêu cầu'
        _exp_m = re.search(r'yearsOfExperience\\?["\']?\s*:\s*(\d+)', html_str)
        if _exp_m and int(_exp_m.group(1)) > 0:
            experience = f"Tối thiểu {_exp_m.group(1)} năm"
        else:
            _exp_dom = re.search(r'(\d+\s*-\s*\d+|\d+)\s*năm\s*kinh\s*nghiệm', soup.get_text(), re.I)
            if _exp_dom:
                experience = f"{_exp_dom.group(1)} năm"

        # 9.4 Bằng cấp
        education = 'Không yêu cầu'
        _edu_m = re.search(r'(Đại học|Cao đẳng|Trung cấp|Thạc sĩ|Tiến sĩ|THPT)', soup.get_text(), re.I)
        if _edu_m:
            education = _edu_m.group(1).capitalize()

        # 9.5 Chức vụ
        position = 'Nhân viên'
        for item in soup.select('[class*="sc-7bf5461f"], [class*="sc-f098d520"], div, li'):
            t = item.get_text(separator=' ', strip=True)
            if t.upper().startswith('CẤP BẬC'):
                val = re.sub(r'^CẤP BẬC\s*:?\s*', '', t, flags=re.IGNORECASE).strip()
                if val and len(val) < 50:
                    position = val
                    break
        if position == 'Nhân viên':
            _pos_m = re.search(r'jobLevelVI\\?["\']?\s*:\s*"([^"]+)"', html_str)
            if _pos_m:
                position = _pos_m.group(1)

        # 9.6 Thông tin liên hệ tổng hợp
        contact_parts = []
        _email_pat = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        _phone_pat = re.compile(r'(?:\+84|0)(?:3[2-9]|5[2689]|7[06-9]|8[1-9]|9[0-9])\d{7}\b')
        _ex_doms = ['topcv.vn', 'jobsgo.vn', 'vietnamworks.com', 'careerviet.vn', 'careerbuilder.vn', 'schema.org', 'w3.org', 'google.com', 'facebook.com']
        
        full_text = f"{description} {benefits} {skills}"
        _found_emails = list(set([e for e in _email_pat.findall(full_text) if not any(d in e.lower() for d in _ex_doms)]))
        _found_phones = list(set(_phone_pat.findall(full_text)))
        
        if _found_emails:
            contact_parts.append(f"Email: {', '.join(_found_emails[:2])}")
        if _found_phones:
            contact_parts.append(f"SĐT: {', '.join(_found_phones[:2])}")
        if json_data and isinstance(json_data.get('hiringOrganization'), dict) and json_data['hiringOrganization'].get('sameAs'):
            contact_parts.append(f"Website: {json_data['hiringOrganization']['sameAs']}")
        if address_detail and address_detail != 'Không đề cập':
            contact_parts.append(f"Địa chỉ: {address_detail}")
            
        contact = ' | '.join(contact_parts) if contact_parts else 'Nộp CV trực tiếp qua hệ thống VietnamWorks'

        return {
            'STT':                 stt_index,
            'Tỉnh thành':          s(location, 200),
            'Loại hình công việc': s(job_type, 200),
            'Lĩnh vực/ngành nghề': s(category, 300),
            'Nhà tuyển dụng':      s(company, 300),
            'Công việc':           s(job_title, 500),
            'Chức vụ':             s(position, 200),
            'Số lượng':            s(quantity, 100),
            'Giới tính':           s(gender, 100),
            'Độ tuổi':             s(age, 100),
            'Mức lương':           s(salary, 200),
            'Thời gian làm việc':  s(work_time, 200),
            'Địa điểm chi tiết':   s(address_detail, 4000),
            'Mô tả công việc':     s(description, 4000),
            'Quyền lợi':           s(benefits, 4000),
            'Kinh nghiệm':         s(experience, 200),
            'Kỹ năng':             s(skills, 4000),
            'Bằng cấp':            s(education, 200),
            'Hạn nộp Hồ sơ':       s(deadline, 100),
            'Thông tin liên hệ':   s(contact, 4000),
            'Ghi chú':             url,
        }

    except Exception as e:
        print(f'  [!] Lỗi khi parse VietnamWorks job: {e}')
        return None
