"""
jobsgo/parse_jobsgo_job.py
───────────────────────────
Module bóc tách thông tin chi tiết việc làm từ JobsGO.vn.
Sử dụng JSON-LD Schema chuẩn của Google + Xóa Popup Modal + Rút trích nghiêm ngặt.
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

SOURCE_JOBSGO = 'jobsgo'
PAGE_TIMEOUT  = 20
JS_WAIT       = 4

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


# Path toi chromedriver phu hop voi phien ban Chrome tren may (neu co)
# Dat file chromedriver_151.exe vao thu muc goc scraper_data de dung
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
    """Chỉ giữ lại duy nhất tên Tỉnh/Thành phố hợp lệ của Việt Nam. Nếu dính text rác từ Popup Modal chọn địa điểm thì trả về 'Toàn quốc'."""
    if not raw_text or raw_text == 'Không đề cập':
        return 'Không đề cập'
    
    # Loại bỏ ngay lập tức nếu dính nút Popup Modal chọn địa điểm
    low = raw_text.lower()
    if '×địa điểm' in low or '×hà nội' in low or 'bắc kạn' in low and 'cao bằng' in low:
        return 'Toàn quốc'
    
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
    """Lọc nghiêm ngặt các giá trị badge (Cấp bậc, Bằng cấp, Loại hình) tránh bị dính text rác."""
    if not val or val == 'Không đề cập':
        return default
    for opt in valid_options:
        if opt.lower() in val.lower():
            return opt
    return default


def parse_full_jobsgo_job(driver: uc.Chrome, url: str, stt_index: int) -> dict | None:
    # Từ chối ngay lập tức nếu đây là trang Công ty (/tuyen-dung/ hoặc cong-ty-) chứ không phải trang tin việc làm (/viec-lam/)
    if '/tuyen-dung/' in url or 'cong-ty-' in url.lower() or not url.startswith('https://jobsgo.vn/viec-lam/'):
        print(f'  [!] Bỏ qua URL không phải tin tuyển dụng: {url}')
        return None

    try:
        driver.get(url)

        try:
            WebDriverWait(driver, PAGE_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, 'h1'))
            )
        except TimeoutException:
            print(f'  [!] Timeout khi chờ trang JobsGO: {url}')
            return None

        time.sleep(JS_WAIT)
        raw_soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Kiểm tra trang đã hết hạn / không có thông tin tuyển dụng (trang profile công ty)
        if not raw_soup.select_one('h1.job-title, .job-places, [class*="salary"]'):
            print(f'  [!] Bỏ qua trang không phải tin tuyển dụng active: {url}')
            return None

        # ── 1. Parse qua JSON-LD Schema chuẩn của Google ──────────────────
        json_data = None
        for script in raw_soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    json_data = data
                    break
            except Exception:
                pass

        # ── 2. Xóa các Modal popup khỏi DOM để tránh bị dính text rác ──────
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        for modal in soup.select('.modal, #location-modal, [class*="modal"]'):
            modal.decompose()

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

        def get_badge_info(keyword: str, default: str = 'Không đề cập') -> str:
            for tag in soup.select('.job-meta-item, .jg-sp2-field, span, p, td, li'):
                txt = tag.get_text(strip=True)
                if keyword.lower() in txt.lower() and len(txt) < 80:
                    if ':' in txt:
                        parts = txt.split(':', 1)
                        if len(parts) > 1 and parts[1].strip():
                            val = parts[1].strip()
                            if len(val) < 60 and not any(x in val.lower() for x in ['địa điểm', 'kinh nghiệm', 'bằng cấp', 'mức lương', 'tuyên dung', 'xem thông tin']):
                                return val
            return default

        # ── TRÍCH XUẤT THÔNG TIN CHÍNH ────────────────────────────────

        # 1. Công việc
        job_title = json_data.get('title') if json_data and json_data.get('title') else get_text_multi('h1.job-title', 'h1')

        # 2. Nhà tuyển dụng
        company = 'Không đề cập'
        if json_data and isinstance(json_data.get('hiringOrganization'), dict):
            company = json_data['hiringOrganization'].get('name', 'Không đề cập')
        if company == 'Không đề cập':
            company = get_text_multi('a[href*="/tuyen-dung/"]', '.company-name', '.job-company a')
        if company.endswith('Xem thông tin công ty'):
            company = company[:-len('Xem thông tin công ty')].strip()

        # 3. Mức lương
        salary = 'Thỏa thuận'
        if json_data and isinstance(json_data.get('baseSalary'), dict):
            bs = json_data['baseSalary']
            min_v = bs.get('minValue')
            max_v = bs.get('maxValue')
            if min_v and max_v:
                salary = f"{int(min_v)//1000000} - {int(max_v)//1000000} triệu"
            elif min_v:
                salary = f"Từ {int(min_v)//1000000} triệu"
        if salary == 'Thỏa thuận':
            sal_dom = get_text_multi('.salary', '.jg-sp2-fval', '.job-salary', '[class*="salary"]')
            if 'triệu' in sal_dom.lower() or 'thỏa thuận' in sal_dom.lower():
                salary = sal_dom

        # 4. Tỉnh thành & Địa chỉ chi tiết
        raw_location = 'Không đề cập'
        address_detail = 'Không đề cập'

        if json_data and isinstance(json_data.get('jobLocation'), list) and json_data['jobLocation']:
            addr_obj = json_data['jobLocation'][0].get('address', {})
            if isinstance(addr_obj, dict):
                raw_location = addr_obj.get('addressRegion', 'Không đề cập')
                address_detail = addr_obj.get('streetAddress', 'Không đề cập')

        if raw_location == 'Không đề cập':
            loc_el = soup.select_one('.jg-sp2-field .jg-sp2-fval, .breadcrumb-item a[href*="tai-"]')
            if loc_el:
                raw_location = loc_el.get_text(strip=True)

        location = clean_location(raw_location)
        print(f"      [DEBUG LOC] Raw: '{raw_location[:50]}...' -> Cleaned: '{location}'")

        if address_detail == 'Không đề cập':
            addr_el = soup.select_one('.job-places span.fw-500')
            if addr_el:
                address_detail = addr_el.get_text(strip=True)
            else:
                address_detail = location

        # 5. Mô tả công việc & Quyền lợi
        description = 'Không đề cập'
        benefits = 'Không đề cập'

        if json_data:
            if json_data.get('description'):
                description = json_data.get('description')
            if json_data.get('jobBenefits'):
                benefits = json_data.get('jobBenefits')

        if description == 'Không đề cập':
            desc_div = soup.select_one('.job-description, .tab-content')
            if desc_div:
                description = desc_div.get_text(strip=True)

        # 6. Ngành nghề
        category = 'Không đề cập'
        if json_data and isinstance(json_data.get('industry'), list) and json_data['industry']:
            category = ', '.join(json_data['industry'])
        if category == 'Không đề cập':
            category = get_text_multi('.job-category a', '.breadcrumb li a')

        # 7. Hạn nộp
        deadline = 'Không đề cập'
        if json_data and json_data.get('validThrough'):
            vt = json_data['validThrough']
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', vt)
            if match:
                deadline = f"{match.group(3)}/{match.group(2)}/{match.group(1)}"
        if deadline == 'Không đề cập':
            deadline = get_badge_info('hạn nộp')

        # 8. Kinh nghiệm
        experience = 'Không yêu cầu'
        if json_data and json_data.get('experienceRequirements'):
            req = json_data['experienceRequirements']
            if isinstance(req, str) and req != 'no requirements':
                experience = req
        if experience == 'Không yêu cầu':
            exp_badge = get_badge_info('kinh nghiệm')
            if exp_badge != 'Không đề cập':
                experience = exp_badge

        # 9. Các trường badge được lọc nghiêm ngặt
        raw_job_type = get_badge_info('loại hình')
        job_type = clean_badge(raw_job_type, ["Toàn thời gian", "Bán thời gian", "Thực tập", "Remote", "Thời vụ", "Part-time", "Full-time"], "Toàn thời gian")

        raw_position = get_badge_info('cấp bậc')
        position = clean_badge(raw_position, ["Nhân viên", "Trưởng nhóm", "Trưởng phòng", "Giám đốc", "Quản lý", "Mới tốt nghiệp", "Chuyên viên", "Leader"], "Nhân viên")

        raw_education = get_badge_info('bằng cấp')
        # Fallback 1: trích từ JSON-LD educationRequirements
        if raw_education == 'Không đề cập' and json_data:
            edu_req = json_data.get('educationRequirements')
            if isinstance(edu_req, dict):
                raw_education = edu_req.get('credentialCategory', 'Không đề cập')
            elif isinstance(edu_req, str) and edu_req:
                raw_education = edu_req
        # Fallback 2: tìm theo label/value trong các khối tổng quan
        if raw_education == 'Không đề cập':
            for item in soup.select('.job-overview-item, .jg-sp2-field, .job-meta-item, [class*="overview"] li'):
                label_el = item.select_one('label, .label, .jg-sp2-label, strong, dt')
                value_el = item.select_one('.value, .jg-sp2-fval, dd, span:not(label)')
                if label_el and 'bằng cấp' in label_el.get_text(strip=True).lower() and value_el:
                    raw_education = value_el.get_text(strip=True)
                    break
        # Fallback 3: regex trong toàn bộ trang (an toàn nhất)
        if raw_education == 'Không đề cập':
            _edu_pat = re.compile(
                r'(?:Bằng cấp|Học vấn)[\s:]+(Đại học|Cao đẳng|Trung cấp|Thạc sĩ|Tiến sĩ|THPT|Không yêu cầu)',
                re.IGNORECASE
            )
            m = _edu_pat.search(soup.get_text())
            if m:
                raw_education = m.group(1)
        education = clean_badge(raw_education, ["Đại học", "Cao đẳng", "Trung cấp", "THPT", "Thạc sĩ", "Tiến sĩ", "Không yêu cầu"], "Không yêu cầu")

        gender = clean_badge(get_badge_info('giới tính'), ["Nam", "Nữ", "Không yêu cầu"], "Không yêu cầu")

        quantity = get_badge_info('số lượng')
        if len(quantity) > 20:
            quantity = 'Không đề cập'

        age = 'Không đề cập'
        # Tầng 1: tìm theo label/value trong các khối tổng quan
        for item in soup.select('.job-overview-item, .jg-sp2-field, .job-meta-item, [class*="overview"] li'):
            label_el = item.select_one('label, .label, .jg-sp2-label, strong, dt')
            value_el = item.select_one('.value, .jg-sp2-fval, dd, span:not(label)')
            if label_el and 'độ tuổi' in label_el.get_text(strip=True).lower() and value_el:
                val = value_el.get_text(strip=True)
                if val and len(val) < 50:
                    age = val
                    break
        # Tầng 2: get_badge_info fallback
        if age == 'Không đề cập':
            age_raw = get_badge_info('độ tuổi')
            if age_raw != 'Không đề cập' and len(age_raw) <= 50:
                age = age_raw
        # Tầng 3: regex tìm pattern "Độ tuổi: 20 - 35"
        if age == 'Không đề cập':
            m = re.search(r'Độ tuổi[:\s]+(\d[\d\s\-–&à tuổi]+)', soup.get_text())
            if m and len(m.group(1).strip()) < 50:
                age = m.group(1).strip()

        work_time = get_badge_info('thời gian làm việc')
        if len(work_time) > 100:
            work_time = 'Không đề cập'

        # Kỹ năng — nhiều tầng fallback
        skill_tags = [el.get_text(strip=True) for el in soup.select('.job-tags a, .tag-item')]

        # Fallback 1: các class thay thế khác
        if not skill_tags:
            for sel in ['.skill-tag', '[class*="skill"] a', '[class*="tag"] a:not([href*="tuyen-dung"])']:
                skill_tags = [el.get_text(strip=True) for el in soup.select(sel)
                              if el.get_text(strip=True) and len(el.get_text(strip=True)) < 60]
                if skill_tags:
                    break

        # Fallback 2: trích từ JSON-LD nếu có
        if not skill_tags and json_data:
            jd_skills = json_data.get('skills') or json_data.get('skill') or []
            if isinstance(jd_skills, str) and jd_skills:
                skill_tags = [s.strip() for s in re.split(r'[,;]', jd_skills) if s.strip()]
            elif isinstance(jd_skills, list):
                skill_tags = [str(s).strip() for s in jd_skills if s]

        # Fallback 3: trích từ section "Kỹ năng" trong mô tả
        if not skill_tags and description != 'Không đề cập':
            m_skill = re.search(
                r'(?:Kỹ năng|Skills?)[:\s]+(.*?)(?:\n|\.|$)',
                description,
                re.IGNORECASE,
            )
            if m_skill:
                for sk in re.split(r'[,;/]', m_skill.group(1)):
                    sk = sk.strip()
                    if sk and len(sk) < 80:
                        skill_tags.append(sk)

        skills = ', '.join(skill_tags) if skill_tags else 'Không đề cập'
        
        # Tổng hợp thông tin liên hệ JobsGO
        contact_parts = []
        _email_pat = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        _phone_pat = re.compile(r'(?:\+84|0)(?:3[2-9]|5[2689]|7[06-9]|8[1-9]|9[0-9])\d{7}\b')
        _ex_doms = ['topcv.vn', 'jobsgo.vn', 'vietnamworks.com', 'careerviet.vn', 'careerbuilder.vn', 'schema.org', 'w3.org', 'google.com', 'facebook.com']
        
        full_text = f"{description} {benefits}"
        _found_emails = list(set([e for e in _email_pat.findall(full_text) if not any(d in e.lower() for d in _ex_doms)]))
        _found_phones = list(set(_phone_pat.findall(full_text)))
        
        if _found_emails:
            contact_parts.append(f"Email: {', '.join(_found_emails[:2])}")
        if _found_phones:
            contact_parts.append(f"SĐT: {', '.join(_found_phones[:2])}")
        if address_detail and address_detail != 'Không đề cập':
            contact_parts.append(f"Địa chỉ: {address_detail[:100]}")
            
        contact = ' | '.join(contact_parts) if contact_parts else 'Nộp CV trực tiếp qua hệ thống JobsGO'

        image_url = ''
        if json_data and isinstance(json_data.get('image'), str):
            image_url = json_data['image'].strip()
        if not image_url:
            image_element = soup.select_one('meta[property="og:image"], meta[name="twitter:image"]')
            image_url = image_element.get('content', '').strip() if image_element else ''

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
        print(f'  [!] Lỗi khi parse JobsGO job: {e}')
        return None
