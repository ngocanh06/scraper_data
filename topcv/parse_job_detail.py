import sys
import io
import os
import re
import random
import time

from bs4 import BeautifulSoup
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_manager import JobDB

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SOURCE       = 'topcv'
PAGE_TIMEOUT = 20
JS_WAIT      = 4

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

def clean_location(raw_text: str) -> str:
    """Rút trích tên tỉnh/thành phố chuẩn từ văn bản thô.
    - 1 tỉnh  → trả tỉnh đó
    - 2-3 tỉnh → giữ tất cả (join ', ') để không mất dữ liệu đa tỉnh
    - >3 tỉnh  → 'Toàn quốc'
    """
    if not raw_text or raw_text == 'Không đề cập':
        return 'Không đề cập'

    low = raw_text.lower()
    if '×địa điểm' in low or '×hà nội' in low or ('bắc kạn' in low and 'cao bằng' in low):
        return 'Toàn quốc'

    found = []
    for prov in VIETNAM_PROVINCES:
        if prov.lower() in low:
            if prov not in found:
                found.append(prov)

    if len(found) > 3:
        return 'Toàn quốc'

    # Giữ lại TẤT CẢ tỉnh tìm được (kể cả đa tỉnh như HCM + Bình Dương)
    if found:
        return ', '.join(found)

    cleaned = re.sub(r'(Lĩnh vực|Theo dõi|NTD|Việc đang tuyển|GẤP|Full-time|Part-time).*', '', raw_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if len(cleaned) <= 100 else 'Không đề cập'


# Path toi chromedriver phu hop voi phien ban Chrome tren may (neu co)
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


def parse_full_topcv_job(driver: uc.Chrome, url: str, stt_index: int) -> dict | None:
    try:
        driver.get(url)

        try:
            WebDriverWait(driver, PAGE_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, 'h1'))
            )
        except TimeoutException:
            print(f'  [!] Timeout khi chờ trang: {url}')
            return None

        time.sleep(JS_WAIT)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        def get_text_multi(*selectors: str, default: str = 'Không đề cập') -> str:
            for sel in selectors:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(strip=True)
                    if text:
                        return text
            return default

        def s(value: str, maxlen: int = 200) -> str:
            return re.sub(r'\s+', ' ', str(value).strip())[:maxlen] if value else ''

        def get_general_info(label_kw: str, default: str = 'Không đề cập') -> str:
            for item_sel in [
                '.box-job-information-general-info-list__item',
                '.job-detail__info--item',
                '[class*=general-info] li',
                '[class*=job-info] tr',
            ]:
                for item in soup.select(item_sel):
                    text_parts = [p.strip() for p in item.get_text('\n').split('\n') if p.strip()]
                    if len(text_parts) >= 2:
                        if label_kw.lower() in text_parts[0].lower():
                            return text_parts[1]
            return default

        def get_header_info(label_kw: str, default: str = 'Không đề cập') -> str:
            header_info = soup.select_one('.box-header-job-list-info')
            if header_info:
                for item in header_info.select('.list-info__content'):
                    text_parts = [p.strip() for p in item.get_text('\n').split('\n') if p.strip()]
                    if len(text_parts) >= 2:
                        if label_kw.lower() in text_parts[0].lower():
                            return text_parts[1]
                for item in header_info.find_all(True, recursive=False):
                    text_parts = [p.strip() for p in item.get_text('\n').split('\n') if p.strip()]
                    if len(text_parts) >= 2:
                        if label_kw.lower() in text_parts[0].lower():
                            return text_parts[1]
            return default

        def get_detail_section(title_kw: str, default: str = 'Không đề cập') -> str:
            for item in soup.select('.box-job-information-detail-item'):
                title_el = item.select_one('.box-job-information-detail-item__title')
                if title_el:
                    title_text = title_el.get_text(strip=True).lower()
                    if title_kw.lower() in title_text:
                        text_el = item.select_one('.box-job-information-detail-item__text')
                        if text_el:
                            return text_el.get_text(strip=True)
                        full_text = item.get_text(strip=True)
                        title_only = title_el.get_text(strip=True)
                        if full_text.startswith(title_only):
                            return full_text[len(title_only):].strip()
                        return full_text
            return default

        def get_address_time_item(label_kw: str, default: str = 'Không đề cập') -> str:
            for item in soup.select('.box-job-information-address-and-time-list__item'):
                title_el = item.select_one('.box-job-information-address-and-time-list__item--title')
                if title_el and label_kw.lower() in title_el.get_text(strip=True).lower():
                    content_el = item.select_one('.box-job-information-address-and-time-list__item--content')
                    if content_el:
                        return content_el.get_text(strip=True)
                    full = item.get_text(strip=True)
                    t = title_el.get_text(strip=True)
                    return full[len(t):].strip() if full.startswith(t) else full
            return default

        job_title = get_text_multi('.box-header-job h1', 'h1.job-detail__info--title', 'h1', default='Không đề cập')
        company = get_text_multi('.box-company-info', '.box-header-job__company a', default='Không đề cập')
        salary = get_text_multi('.box-header-job__salary--title', default='Thỏa thuận')
        raw_loc = get_header_info('địa điểm')
        location = clean_location(raw_loc)
        experience = get_header_info('kinh nghiệm')
        deadline = get_header_info('hạn')

        job_type = get_general_info('loại hình', 'Toàn thời gian')
        position = get_general_info('cấp bậc', 'Nhân viên')
        quantity = get_general_info('số lượng')
        gender   = get_general_info('giới tính', 'Không yêu cầu')
        age      = get_general_info('tuổi')

        # Bằng cấp — thử nhiều keyword khác nhau vì TopCV dùng label không nhất quán
        education = get_general_info('trình độ học vấn')
        if education == 'Không đề cập':
            education = get_general_info('trình độ')
        if education == 'Không đề cập':
            education = get_general_info('bằng cấp')
        # Fallback: tìm text regex trực tiếp trong HTML
        if education == 'Không đề cập':
            _edu_pattern = re.compile(
                r'(Đại học|Cao đẳng|Trung cấp|Thạc sĩ|Tiến sĩ|THPT|Không yêu cầu)',
                re.IGNORECASE
            )
            for tag in soup.find_all(['span', 'p', 'td', 'li', 'div']):
                txt = tag.get_text(strip=True)
                if len(txt) < 60:
                    m = _edu_pattern.search(txt)
                    if m:
                        # Đảm bảo đây là text badge chứ không phải nội dung dài
                        education = m.group(0).capitalize()
                        break

        category = get_text_multi('.box-job-detail-category a', default='Không đề cập')
        if category == 'Không đề cập':
            meta_desc = soup.select_one('meta[name="keywords"]')
            if meta_desc:
                content = meta_desc.get('content', '')
                parts = [p.strip() for p in content.split(',') if '/' in p and 'http' not in p]
                if parts:
                    category = parts[0]

        description = get_detail_section('mô tả công việc')
        requirements = get_detail_section('yêu cầu ứng viên')
        benefits = get_detail_section('quyền lợi')

        address_detail = get_address_time_item('địa điểm làm việc')
        work_time = get_address_time_item('thời gian làm việc')

        # Kỹ năng — thử nhiều selector theo thứ tự ưu tiên
        skill_tags = []

        # Tầng 1: selector chính thức của TopCV
        tag_scrolls = soup.select('.job-tags__group-list-tag-scroll')
        if tag_scrolls:
            for scroll in tag_scrolls:
                for tag in scroll.find_all(True, recursive=False):
                    t = tag.get_text(strip=True)
                    if t and t not in skill_tags:
                        skill_tags.append(t)

        # Tầng 2: các class thay thế
        if not skill_tags:
            for sel in [
                '.box-job-tags a', '.job-tags a', '[class*="tag"] a',
                '.tag a', '.skills-tag', '[class*="skill"] a',
            ]:
                for el in soup.select(sel):
                    t = el.get_text(strip=True)
                    if t and len(t) < 60 and t not in skill_tags:
                        skill_tags.append(t)
                if skill_tags:
                    break

        # Tầng 3: trích từ section "Kỹ năng" trong mô tả/yêu cầu
        if not skill_tags:
            _skill_section = re.search(
                r'(?:Kỹ năng|Skills?)[:\s]+(.*?)(?:\n|$)',
                requirements + description,
                re.IGNORECASE,
            )
            if _skill_section:
                raw_skills = _skill_section.group(1).strip()
                # Tách theo dấu phẩy, chấm phẩy hoặc /
                for sk in re.split(r'[,;/]', raw_skills):
                    sk = sk.strip()
                    if sk and len(sk) < 80:
                        skill_tags.append(sk)

        skills = ', '.join(skill_tags) if skill_tags else 'Không đề cập'
        
        # Tổng hợp thông tin liên hệ TopCV
        contact_parts = []
        recruiter_dom = get_text_multi('.job-detail__recruiter', default='')
        if recruiter_dom and recruiter_dom != 'Không đề cập':
            contact_parts.append(f"Liên hệ: {recruiter_dom}")
            
        _email_pat = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        _phone_pat = re.compile(r'(?:\+84|0)(?:3[2-9]|5[2689]|7[06-9]|8[1-9]|9[0-9])\d{7}\b')
        _ex_doms = ['topcv.vn', 'jobsgo.vn', 'vietnamworks.com', 'careerviet.vn', 'careerbuilder.vn', 'schema.org', 'w3.org', 'google.com', 'facebook.com']
        
        full_text = f"{description} {benefits} {requirements}"
        _found_emails = list(set([e for e in _email_pat.findall(full_text) if not any(d in e.lower() for d in _ex_doms)]))
        _found_phones = list(set(_phone_pat.findall(full_text)))
        
        if _found_emails:
            contact_parts.append(f"Email: {', '.join(_found_emails[:2])}")
        if _found_phones:
            contact_parts.append(f"SĐT: {', '.join(_found_phones[:2])}")
        if address_detail and address_detail != 'Không đề cập':
            contact_parts.append(f"Địa chỉ: {address_detail[:100]}")
            
        contact = ' | '.join(contact_parts) if contact_parts else 'Nộp CV trực tiếp qua hệ thống TopCV'

        image_element = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
        image_url = image_element.get('content', '').strip() if image_element else ''

        if requirements and requirements != 'Không đề cập':
            if description != 'Không đề cập':
                description = description + ' | YÊU CẦU: ' + requirements
            else:
                description = requirements

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
            'Ảnh đại diện':        image_url,
            'Ghi chú':             url,
        }
    except Exception as e:
        print(f'  [!] Lỗi khi parse TopCV job: {e}')
        return None
