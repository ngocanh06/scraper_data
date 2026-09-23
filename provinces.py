"""
provinces.py
────────────
Module quản lý tập trung danh sách tỉnh thành Việt Nam (63 tỉnh thành và 34 tỉnh trọng điểm).
Cung cấp URL/slug chính xác cho từng website tuyển dụng:
  - TopCV
  - JobsGO
  - VietnamWorks
  - Mở rộng cho các nguồn tuyển dụng tương lai (CareerBuilder, TimViecNhanh,...)
"""

import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# Danh sách đầy đủ 63 tỉnh thành Việt Nam với slug & ID tương ứng từng nguồn
PROVINCES_DATA = [
    # ── Tỉnh/Thành phố lớn & Trọng điểm Kinh tế ──
    {
        'name': 'Hồ Chí Minh',
        'topcv_slug': 'tai-ho-chi-minh-l2',
        'jobsgo_slug': 'tai-ho-chi-minh',
        'vnw_slug': 'ho-chi-minh-v29-vn',
        'is_top34': True
    },
    {
        'name': 'Hà Nội',
        'topcv_slug': 'tai-ha-noi-l1',
        'jobsgo_slug': 'tai-ha-noi',
        'vnw_slug': 'ha-noi-v24-vn',
        'is_top34': True
    },
    {
        'name': 'Bình Dương',
        'topcv_slug': 'tai-binh-duong-l3',
        'jobsgo_slug': 'tai-binh-duong',
        'vnw_slug': 'binh-duong-v11-vn',
        'is_top34': True
    },
    {
        'name': 'Đồng Nai',
        'topcv_slug': 'tai-dong-nai-l5',
        'jobsgo_slug': 'tai-dong-nai',
        'vnw_slug': 'dong-nai-v18-vn',
        'is_top34': True
    },
    {
        'name': 'Bắc Ninh',
        'topcv_slug': 'tai-bac-ninh-l4',
        'jobsgo_slug': 'tai-bac-ninh',
        'vnw_slug': 'bac-ninh-v6-vn',
        'is_top34': True
    },
    {
        'name': 'Hải Phòng',
        'topcv_slug': 'tai-hai-phong-l9',
        'jobsgo_slug': 'tai-hai-phong',
        'vnw_slug': 'hai-phong-v28-vn',
        'is_top34': True
    },
    {
        'name': 'Đà Nẵng',
        'topcv_slug': 'tai-da-nang-l8',
        'jobsgo_slug': 'tai-da-nang',
        'vnw_slug': 'da-nang-v17-vn',
        'is_top34': True
    },
    {
        'name': 'Cần Thơ',
        'topcv_slug': 'tai-can-tho-l20',
        'jobsgo_slug': 'tai-can-tho',
        'vnw_slug': 'can-tho-v15-vn',
        'is_top34': True
    },
    {
        'name': 'Hải Dương',
        'topcv_slug': 'tai-hai-duong-l7',
        'jobsgo_slug': 'tai-hai-duong',
        'vnw_slug': 'hai-duong-v30-vn',
        'is_top34': True
    },
    {
        'name': 'Hưng Yên',
        'topcv_slug': 'tai-hung-yen-l6',
        'jobsgo_slug': 'tai-hung-yen',
        'vnw_slug': 'hung-yen-v32-vn',
        'is_top34': True
    },
    {
        'name': 'Bà Rịa-Vũng Tàu',
        'topcv_slug': 'tai-ba-ria-vung-tau-l11',
        'jobsgo_slug': 'tai-ba-ria-vung-tau',
        'vnw_slug': 'ba-ria-vung-tau-v3-vn',
        'is_top34': True
    },
    {
        'name': 'Quảng Ninh',
        'topcv_slug': 'tai-quang-ninh-l53',
        'jobsgo_slug': 'tai-quang-ninh',
        'vnw_slug': 'quang-ninh-v49-vn',
        'is_top34': True
    },
    {
        'name': 'Long An',
        'topcv_slug': 'tai-long-an-l40',
        'jobsgo_slug': 'tai-long-an',
        'vnw_slug': 'long-an-v35-vn',
        'is_top34': True
    },
    {
        'name': 'Bắc Giang',
        'topcv_slug': 'tai-bac-giang-l12',
        'jobsgo_slug': 'tai-bac-giang',
        'vnw_slug': 'bac-giang-v7-vn',
        'is_top34': True
    },
    {
        'name': 'Thái Nguyên',
        'topcv_slug': 'tai-thai-nguyen-l59',
        'jobsgo_slug': 'tai-thai-nguyen',
        'vnw_slug': 'thai-nguyen-v51-vn',
        'is_top34': True
    },
    {
        'name': 'Thanh Hóa',
        'topcv_slug': 'tai-thanh-hoa-l60',
        'jobsgo_slug': 'tai-thanh-hoa',
        'vnw_slug': 'thanh-hoa-v52-vn',
        'is_top34': True
    },
    {
        'name': 'Nghệ An',
        'topcv_slug': 'tai-nghe-an-l45',
        'jobsgo_slug': 'tai-nghe-an',
        'vnw_slug': 'nghe-an-v37-vn',
        'is_top34': True
    },
    {
        'name': 'Thừa Thiên Huế',
        'topcv_slug': 'tai-thua-thien-hue-l61',
        'jobsgo_slug': 'tai-thua-thien-hue',
        'vnw_slug': 'thua-thien-hue-v53-vn',
        'is_top34': True
    },
    {
        'name': 'Khánh Hòa',
        'topcv_slug': 'tai-khanh-hoa-l33',
        'jobsgo_slug': 'tai-khanh-hoa',
        'vnw_slug': 'khanh-hoa-v33-vn',
        'is_top34': True
    },
    {
        'name': 'Lâm Đồng',
        'topcv_slug': 'tai-lam-dong-l37',
        'jobsgo_slug': 'tai-lam-dong',
        'vnw_slug': 'lam-dong-v64-vn',
        'is_top34': True
    },
    {
        'name': 'Đắk Lắk',
        'topcv_slug': 'tai-dak-lak-l23',
        'jobsgo_slug': 'tai-dak-lak',
        'vnw_slug': 'dak-lak-v19-vn',
        'is_top34': True
    },
    {
        'name': 'Bình Định',
        'topcv_slug': 'tai-binh-dinh-l16',
        'jobsgo_slug': 'tai-binh-dinh',
        'vnw_slug': 'binh-dinh-v12-vn',
        'is_top34': True
    },
    {
        'name': 'Tiền Giang',
        'topcv_slug': 'tai-tien-giang-l62',
        'jobsgo_slug': 'tai-tien-giang',
        'vnw_slug': 'tien-giang-v54-vn',
        'is_top34': True
    },
    {
        'name': 'Bến Tre',
        'topcv_slug': 'tai-ben-tre-l15',
        'jobsgo_slug': 'tai-ben-tre',
        'vnw_slug': 'ben-tre-v10-vn',
        'is_top34': True
    },
    {
        'name': 'An Giang',
        'topcv_slug': 'tai-an-giang-l10',
        'jobsgo_slug': 'tai-an-giang',
        'vnw_slug': 'an-giang-v2-vn',
        'is_top34': True
    },
    {
        'name': 'Kiên Giang',
        'topcv_slug': 'tai-kien-giang-l34',
        'jobsgo_slug': 'tai-kien-giang',
        'vnw_slug': 'kien-giang-v34-vn',
        'is_top34': True
    },
    {
        'name': 'Tây Ninh',
        'topcv_slug': 'tai-tay-ninh-l57',
        'jobsgo_slug': 'tai-tay-ninh',
        'vnw_slug': 'tay-ninh-v48-vn',
        'is_top34': True
    },
    {
        'name': 'Bình Phước',
        'topcv_slug': 'tai-binh-phuoc-l17',
        'jobsgo_slug': 'tai-binh-phuoc',
        'vnw_slug': 'binh-phuoc-v13-vn',
        'is_top34': True
    },
    {
        'name': 'Bình Thuận',
        'topcv_slug': 'tai-binh-thuan-l18',
        'jobsgo_slug': 'tai-binh-thuan',
        'vnw_slug': 'binh-thuan-v14-vn',
        'is_top34': True
    },
    {
        'name': 'Nam Định',
        'topcv_slug': 'tai-nam-dinh-l44',
        'jobsgo_slug': 'tai-nam-dinh',
        'vnw_slug': 'nam-dinh-v36-vn',
        'is_top34': True
    },
    {
        'name': 'Vĩnh Phúc',
        'topcv_slug': 'tai-vinh-phuc-l67',
        'jobsgo_slug': 'tai-vinh-phuc',
        'vnw_slug': 'vinh-phuc-v58-vn',
        'is_top34': True
    },
    {
        'name': 'Phú Thọ',
        'topcv_slug': 'tai-phu-tho-l48',
        'jobsgo_slug': 'tai-phu-tho',
        'vnw_slug': 'phu-tho-v40-vn',
        'is_top34': True
    },
    {
        'name': 'Thái Bình',
        'topcv_slug': 'tai-thai-binh-l58',
        'jobsgo_slug': 'tai-thai-binh',
        'vnw_slug': 'thai-binh-v50-vn',
        'is_top34': True
    },
    {
        'name': 'Quảng Nam',
        'topcv_slug': 'tai-quang-nam-l51',
        'jobsgo_slug': 'tai-quang-nam',
        'vnw_slug': 'quang-nam-v43-vn',
        'is_top34': True
    },
    {
        'name': 'Quảng Ngãi',
        'topcv_slug': 'tai-quang-ngai-l52',
        'jobsgo_slug': 'tai-quang-ngai',
        'vnw_slug': 'quang-ngai-v44-vn',
        'is_top34': True
    },

    # ── Các Tỉnh Thành Khác ──
    {'name': 'Bắc Kạn',      'topcv_slug': 'tai-bac-kan-l13',      'jobsgo_slug': 'tai-bac-kan',      'vnw_slug': 'bac-kan-v8-vn',      'is_top34': False},
    {'name': 'Bạc Liêu',     'topcv_slug': 'tai-bac-lieu-l14',     'jobsgo_slug': 'tai-bac-lieu',     'vnw_slug': 'bac-lieu-v9-vn',     'is_top34': False},
    {'name': 'Cà Mau',       'topcv_slug': 'tai-ca-mau-l19',       'jobsgo_slug': 'tai-ca-mau',       'vnw_slug': 'ca-mau-v16-vn',      'is_top34': False},
    {'name': 'Cao Bằng',     'topcv_slug': 'tai-cao-bang-l21',     'jobsgo_slug': 'tai-cao-bang',     'vnw_slug': 'cao-bang-v60-vn',    'is_top34': False},
    {'name': 'Đắc Nông',     'topcv_slug': 'tai-dak-nong-l22',     'jobsgo_slug': 'tai-dak-nong',     'vnw_slug': 'dak-nong-v20-vn',    'is_top34': False},
    {'name': 'Điện Biên',    'topcv_slug': 'tai-dien-bien-l24',    'jobsgo_slug': 'tai-dien-bien',    'vnw_slug': 'dien-bien-v21-vn',   'is_top34': False},
    {'name': 'Đồng Tháp',    'topcv_slug': 'tai-dong-thap-l25',    'jobsgo_slug': 'tai-dong-thap',    'vnw_slug': 'dong-thap-v22-vn',   'is_top34': False},
    {'name': 'Gia Lai',      'topcv_slug': 'tai-gia-lai-l26',      'jobsgo_slug': 'tai-gia-lai',      'vnw_slug': 'gia-lai-v23-vn',     'is_top34': False},
    {'name': 'Hà Giang',     'topcv_slug': 'tai-ha-giang-l27',     'jobsgo_slug': 'tai-ha-giang',     'vnw_slug': 'ha-giang-v25-vn',    'is_top34': False},
    {'name': 'Hà Nam',       'topcv_slug': 'tai-ha-nam-l28',       'jobsgo_slug': 'tai-ha-nam',       'vnw_slug': 'ha-nam-v26-vn',      'is_top34': False},
    {'name': 'Hà Tĩnh',      'topcv_slug': 'tai-ha-tinh-l29',      'jobsgo_slug': 'tai-ha-tinh',      'vnw_slug': 'ha-tinh-v27-vn',     'is_top34': False},
    {'name': 'Hậu Giang',    'topcv_slug': 'tai-hau-giang-l30',    'jobsgo_slug': 'tai-hau-giang',    'vnw_slug': 'hau-giang-v31-vn',   'is_top34': False},
    {'name': 'Hòa Bình',     'topcv_slug': 'tai-hoa-binh-l31',     'jobsgo_slug': 'tai-hoa-binh',     'vnw_slug': 'hoa-binh-v61-vn',    'is_top34': False},
    {'name': 'Kon Tum',      'topcv_slug': 'tai-kon-tum-l35',      'jobsgo_slug': 'tai-kon-tum',      'vnw_slug': 'kontum-v65-vn',      'is_top34': False},
    {'name': 'Lai Châu',     'topcv_slug': 'tai-lai-chau-l36',     'jobsgo_slug': 'tai-lai-chau',     'vnw_slug': 'lai-chau-v62-vn',    'is_top34': False},
    {'name': 'Lạng Sơn',     'topcv_slug': 'tai-lang-son-l37',     'jobsgo_slug': 'tai-lang-son',     'vnw_slug': 'lang-son-v63-vn',    'is_top34': False},
    {'name': 'Ninh Bình',    'topcv_slug': 'tai-ninh-binh-l46',    'jobsgo_slug': 'tai-ninh-binh',    'vnw_slug': 'ninh-binh-v38-vn',   'is_top34': False},
    {'name': 'Ninh Thuận',   'topcv_slug': 'tai-ninh-thuan-l47',   'jobsgo_slug': 'tai-ninh-thuan',   'vnw_slug': 'ninh-thuan-v39-vn',  'is_top34': False},
    {'name': 'Phú Yên',      'topcv_slug': 'tai-phu-yen-l49',      'jobsgo_slug': 'tai-phu-yen',      'vnw_slug': 'phu-yen-v41-vn',     'is_top34': False},
    {'name': 'Quảng Bình',   'topcv_slug': 'tai-quang-binh-l50',   'jobsgo_slug': 'tai-quang-binh',   'vnw_slug': 'quang-binh-v42-vn',  'is_top34': False},
    {'name': 'Quảng Trị',    'topcv_slug': 'tai-quang-tri-l54',    'jobsgo_slug': 'tai-quang-tri',    'vnw_slug': 'quang-tri-v45-vn',   'is_top34': False},
    {'name': 'Sóc Trăng',    'topcv_slug': 'tai-soc-trang-l55',    'jobsgo_slug': 'tai-soc-trang',    'vnw_slug': 'soc-trang-v46-vn',   'is_top34': False},
    {'name': 'Sơn La',       'topcv_slug': 'tai-son-la-l56',       'jobsgo_slug': 'tai-son-la',       'vnw_slug': 'son-la-v47-vn',      'is_top34': False},
    {'name': 'Trà Vinh',     'topcv_slug': 'tai-tra-vinh-l63',     'jobsgo_slug': 'tai-tra-vinh',     'vnw_slug': 'tra-vinh-v55-vn',    'is_top34': False},
    {'name': 'Tuyên Quang',  'topcv_slug': 'tai-tuyen-quang-l64',  'jobsgo_slug': 'tai-tuyen-quang',  'vnw_slug': 'tuyen-quang-v56-vn', 'is_top34': False},
    {'name': 'Vĩnh Long',    'topcv_slug': 'tai-vinh-long-l65',    'jobsgo_slug': 'tai-vinh-long',    'vnw_slug': 'vinh-long-v57-vn',   'is_top34': False},
    {'name': 'Yên Bái',      'topcv_slug': 'tai-yen-bai-l68',      'jobsgo_slug': 'tai-yen-bai',      'vnw_slug': 'yen-bai-v59-vn',     'is_top34': False},
]


# ── DANH SÁCH 34 TỈNH THÀNH SAU SÁP NHẬP (NGHỊ QUYẾT TỈNH THÀNH MỚI) ──
# Gồm 6 Thành phố trực thuộc TW và 28 Tỉnh mới
MERGED_34_PROVINCES = [
    {'name': 'TP. Hồ Chí Minh',  'sub_names': ['Hồ Chí Minh', 'Bình Dương', 'Bà Rịa-Vũng Tàu']},
    {'name': 'Hà Nội',            'sub_names': ['Hà Nội']},
    {'name': 'TP. Hải Phòng',    'sub_names': ['Hải Phòng', 'Hải Dương']},
    {'name': 'TP. Đà Nẵng',      'sub_names': ['Đà Nẵng', 'Quảng Nam']},
    {'name': 'TP. Huế',          'sub_names': ['Thừa Thiên Huế']},
    {'name': 'TP. Cần Thơ',      'sub_names': ['Cần Thơ', 'Sóc Trăng', 'Hậu Giang']},
    {'name': 'Lào Cai',          'sub_names': ['Yên Bái', 'Lào Cai']},
    {'name': 'Thái Nguyên',      'sub_names': ['Thái Nguyên', 'Bắc Kạn']},
    {'name': 'Tuyên Quang',      'sub_names': ['Tuyên Quang', 'Hà Giang']},
    {'name': 'Phú Thọ',          'sub_names': ['Phú Thọ', 'Vĩnh Phúc', 'Hà Nam']},
    {'name': 'Bắc Ninh',         'sub_names': ['Bắc Ninh', 'Bắc Giang']},
    {'name': 'Hưng Yên',         'sub_names': ['Hưng Yên', 'Thái Bình']},
    {'name': 'Ninh Bình',        'sub_names': ['Ninh Bình', 'Nam Định']},
    {'name': 'Lai Châu',         'sub_names': ['Lai Châu']},
    {'name': 'Điện Biên',        'sub_names': ['Điện Biên']},
    {'name': 'Sơn La',           'sub_names': ['Sơn La']},
    {'name': 'Lạng Sơn',         'sub_names': ['Lạng Sơn']},
    {'name': 'Cao Bằng',         'sub_names': ['Cao Bằng']},
    {'name': 'Quảng Ninh',       'sub_names': ['Quảng Ninh']},
    {'name': 'Thanh Hóa',        'sub_names': ['Thanh Hóa']},
    {'name': 'Nghệ An',          'sub_names': ['Nghệ An']},
    {'name': 'Hà Tĩnh',          'sub_names': ['Hà Tĩnh']},
    {'name': 'Quảng Trị',        'sub_names': ['Quảng Trị', 'Quảng Bình']},
    {'name': 'Quảng Ngãi',       'sub_names': ['Quảng Ngãi']},
    {'name': 'Gia Lai',          'sub_names': ['Gia Lai', 'Kon Tum']},
    {'name': 'Khánh Hòa',        'sub_names': ['Khánh Hòa', 'Ninh Thuận']},
    {'name': 'Lâm Đồng',         'sub_names': ['Lâm Đồng', 'Đắc Nông']},
    {'name': 'Đắk Lắk',          'sub_names': ['Đắk Lắk', 'Phú Yên']},
    {'name': 'Đồng Nai',         'sub_names': ['Đồng Nai', 'Bình Phước']},
    {'name': 'Tây Ninh',         'sub_names': ['Tây Ninh', 'Long An']},
    {'name': 'Vĩnh Long',        'sub_names': ['Vĩnh Long', 'Bến Tre', 'Trà Vinh']},
    {'name': 'Đồng Tháp',        'sub_names': ['Đồng Tháp', 'Tiền Giang']},
    {'name': 'Cà Mau',           'sub_names': ['Cà Mau', 'Bạc Liêu']},
    {'name': 'An Giang',         'sub_names': ['An Giang', 'Kiên Giang']},
]


def normalize_province_name(original_location: str) -> str:
    """
    Chuẩn hoá tên tỉnh thành cũ/chi tiết về tên Tỉnh Thành Mới (sau sáp nhập 34 tỉnh thành).
    Ví dụ: 'Bình Dương' -> 'TP. Hồ Chí Minh'
           'Bắc Giang'  -> 'Bắc Ninh'
           'Hải Dương'  -> 'TP. Hải Phòng'
    """
    if not original_location:
        return 'Toàn Quốc'
    
    for item in MERGED_34_PROVINCES:
        merged_name = item['name']
        for sub in item['sub_names']:
            if sub.lower() in original_location.lower():
                return merged_name
                
    return original_location


def get_provinces(mode: str = '34') -> list[dict]:
    """
    Lấy danh sách tỉnh thành theo chế độ:
      - mode='34' (default): Lấy các tỉnh thành trọng điểm
      - mode='merged34': Lấy 34 tỉnh thành theo quy hoạch SÁP NHẬP MỚI
      - mode='all': Lấy toàn bộ tỉnh thành Việt Nam
    """
    if mode == 'all':
        return PROVINCES_DATA
    return [p for p in PROVINCES_DATA if p.get('is_top34', True)]


def get_topcv_cities(mode: str = '34') -> list[dict]:
    """Trả về danh sách [{'name': ..., 'slug': ...}] phục vụ TopCV."""
    provinces = get_provinces(mode)
    return [{'name': p['name'], 'slug': p['topcv_slug']} for p in provinces]


def get_jobsgo_locations(mode: str = '34') -> list[dict]:
    """Trả về danh sách [{'name': ..., 'url': ...}] phục vụ JobsGO."""
    provinces = get_provinces(mode)
    return [{'name': p['name'], 'url': f"https://jobsgo.vn/viec-lam-{p['jobsgo_slug']}.html"} for p in provinces]


def get_vietnamworks_locations(mode: str = '34') -> list[dict]:
    """Trả về danh sách [{'name': ..., 'url': ...}] phục vụ VietnamWorks."""
    provinces = get_provinces(mode)
    return [{'name': p['name'], 'url': f"https://www.vietnamworks.com/viec-lam-{p['vnw_slug']}"} for p in provinces]


VIECLAM24H_PROVINCE_MAP = {
    'Hồ Chí Minh': {'slug': 'tp-hcm', 'id': 122},
    'Hà Nội': {'slug': 'ha-noi', 'id': 73},
    'Đà Nẵng': {'slug': 'da-nang', 'id': 104},
    'Bình Dương': {'slug': 'binh-duong', 'id': 119},
    'Đồng Nai': {'slug': 'dong-nai', 'id': 120},
    'Bắc Ninh': {'slug': 'bac-ninh', 'id': 90},
    'Hải Phòng': {'slug': 'hai-phong', 'id': 92},
    'Cần Thơ': {'slug': 'can-tho', 'id': 131},
    'Bà Rịa - Vũng Tàu': {'slug': 'ba-ria-vung-tau', 'id': 121},
    'Quảng Ninh': {'slug': 'quang-ninh', 'id': 86},
    'Hải Dương': {'slug': 'hai-duong', 'id': 91},
    'Hưng Yên': {'slug': 'hung-yen', 'id': 93},
    'Nghệ An': {'slug': 'nghe-an', 'id': 99},
    'Thanh Hóa': {'slug': 'thanh-hoa', 'id': 98},
    'Thừa Thiên Huế': {'slug': 'thua-thien-hue', 'id': 103},
    'Khánh Hòa': {'slug': 'khanh-hoa', 'id': 109},
    'Long An': {'slug': 'long-an', 'id': 123},
    'Tiền Giang': {'slug': 'tien-giang', 'id': 124},
    'Lâm Đồng': {'slug': 'lam-dong', 'id': 116},
    'Vĩnh Phúc': {'slug': 'vinh-phuc', 'id': 89},
    'Thái Nguyên': {'slug': 'thai-nguyen', 'id': 84},
    'Bắc Giang': {'slug': 'bac-giang', 'id': 87},
    'Nam Định': {'slug': 'nam-dinh', 'id': 96},
    'Thái Bình': {'slug': 'thai-binh', 'id': 94},
    'Hà Nam': {'slug': 'ha-nam', 'id': 95},
    'Ninh Bình': {'slug': 'ninh-binh', 'id': 97},
    'Bình Định': {'slug': 'binh-dinh', 'id': 107},
    'Quảng Nam': {'slug': 'quang-nam', 'id': 105},
    'Quảng Ngãi': {'slug': 'quang-ngai', 'id': 106},
    'Bình Thuận': {'slug': 'binh-thuan', 'id': 111},
    'Tây Ninh': {'slug': 'tay-ninh', 'id': 118},
    'Kiên Giang': {'slug': 'kien-giang', 'id': 130},
    'An Giang': {'slug': 'an-giang', 'id': 129},
    'Đắk Lắk': {'slug': 'dak-lak', 'id': 114},
}


def get_careerviet_locations(mode: str = '34') -> list[dict]:
    """Trả về danh sách [{'name': ..., 'url': ...}] phục vụ CareerViet."""
    provinces = get_provinces(mode)
    locations = []
    # Key location mapping for CareerViet
    cv_loc_map = {
        'Hồ Chí Minh': 'ho-chi-minh-l8',
        'Hà Nội': 'ha-noi-l4',
        'Đà Nẵng': 'da-nang-l2',
        'Bình Dương': 'binh-duong-l1',
        'Đồng Nai': 'dong-nai-l3',
        'Hải Phòng': 'hai-phong-l9',
        'Cần Thơ': 'can-tho-l5',
        'Bắc Ninh': 'bac-ninh-l68',
        'Bà Rịa-Vũng Tàu': 'ba-ria-vung-tau-l63',
        'Quảng Ninh': 'quang-ninh-l52',
        'Hải Dương': 'hai-duong-l26',
        'Hưng Yên': 'hung-yen-l30',
    }
    for p in provinces:
        pname = p['name']
        slug = cv_loc_map.get(pname)
        if slug:
            url = f"https://careerviet.vn/viec-lam/tat-ca-viec-lam-tai-{slug}-vi.html"
        else:
            url = "https://careerviet.vn/viec-lam/tat-ca-viec-lam-vi.html"
        locations.append({'name': pname, 'url': url})
    return locations


def get_vieclam24h_locations(mode: str = '34') -> list[dict]:
    """Trả về danh sách [{'name': ..., 'url': ...}] phục vụ Vieclam24h."""
    provinces = get_provinces(mode)
    locations = []
    for p in provinces:
        pname = p['name']
        v24h = VIECLAM24H_PROVINCE_MAP.get(pname)
        if v24h:
            url = f"https://vieclam24h.vn/viec-lam-tai-{v24h['slug']}-p{v24h['id']}.html"
            locations.append({'name': pname, 'url': url})
    return locations


def check_all_urls():
    """Kiểm tra tổng quan các URL đã sinh ra cho 3 trang."""
    print("=== DANH SÁCH TỈNH THÀNH HỆ THỐNG ===")
    p34 = get_provinces('34')
    pall = get_provinces('all')
    print(f"Tổng số tỉnh thành mẫu: {len(pall)} tỉnh thành")
    print(f"Số tỉnh thành trọng điểm (mode 34): {len(p34)} tỉnh thành")
    print(f"Danh sách tỉnh thành SAU SÁP NHẬP: {len(MERGED_34_PROVINCES)} tỉnh thành\n")

    print("Mẫu 5 Tỉnh thành sau sáp nhập kèm các tỉnh cũ được hợp nhất:")
    for m in MERGED_34_PROVINCES[:5]:
        print(f"  📌 {m['name']} -> Bao gồm: {', '.join(m['sub_names'])}")


if __name__ == '__main__':
    check_all_urls()

