"""
export_scraper_stats.py
-----------------------
Tổng hợp dữ liệu toàn diện từ SQL Server (job_market), các file Excel và Facebook Group Scraper
xuất ra file JSON 'scraper_overview.json' để hiển thị trực tiếp lên Dashboard fb-group-engine.
"""
import os
import sys
import json
import pyodbc
from datetime import datetime
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON = os.path.join(BASE_DIR, "scraper_overview.json")
FB_JOBS_FILE = os.path.join(BASE_DIR, "facebook_group", "facebook_group_jobs.json")

def generate_stats():
    stats = {
        "updated_at": datetime.now().isoformat(),
        "total_jobs": 0,
        "total_companies": 0,
        "total_sources": 0,
        "sources": [],
        "provinces": [],
        "industries": [],
        "salary_ranges": {
            "under_10m": 0,
            "10m_to_15m": 0,
            "15m_to_25m": 0,
            "above_25m": 0,
            "negotiable": 0
        },
        "recent_jobs": [],
        "facebook_leads": {
            "total": 0,
            "gold_leads": 0,
            "potential_leads": 0
        }
    }

    all_provinces = Counter()
    all_industries = Counter()
    all_companies = set()
    total_db_jobs = 0

    # 1. Kết nối SQL Server
    try:
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=job_market;Trusted_Connection=yes;TrustServerCertificate=yes;',
            timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = [r[0] for r in cur.fetchall() if r[0].lower() != 'sysdiagrams']

        source_meta = {
            'topcv': {'label': 'TopCV', 'color': '#00b14f', 'icon': 'fa-solid fa-graduation-cap'},
            'jobsgo': {'label': 'JobsGO', 'color': '#1877f2', 'icon': 'fa-solid fa-briefcase'},
            'vieclam24h': {'label': 'Vieclam24h', 'color': '#ff6b00', 'icon': 'fa-solid fa-building'},
            'careerviet': {'label': 'CareerViet', 'color': '#e00016', 'icon': 'fa-solid fa-globe'},
            'vietnamworks': {'label': 'VietnamWorks', 'color': '#005aff', 'icon': 'fa-solid fa-network-wired'}
        }

        for t in sorted(tables):
            cur.execute(f"SELECT COUNT(*) FROM [{t}]")
            cnt = cur.fetchone()[0]
            total_db_jobs += cnt

            # Đếm số công ty duy nhất
            cur.execute(f"SELECT COUNT(DISTINCT nha_tuyen_dung) FROM [{t}] WHERE nha_tuyen_dung IS NOT NULL AND nha_tuyen_dung != ''")
            comp_cnt = cur.fetchone()[0]

            # Lấy thời gian mới nhất
            cur.execute(f"SELECT MAX(scraped_at) FROM [{t}]")
            latest_time = cur.fetchone()[0]
            latest_str = str(latest_time)[:19] if latest_time else "2026-09-18"

            meta = source_meta.get(t.lower(), {'label': t.upper(), 'color': '#6b7280', 'icon': 'fa-solid fa-file-lines'})

            stats["sources"].append({
                "id": t.lower(),
                "name": meta["label"],
                "count": cnt,
                "companies_count": comp_cnt,
                "latest_time": latest_str,
                "color": meta["color"],
                "icon": meta["icon"],
                "status": "Hoạt động"
            })

            # Phân bố tỉnh thành
            cur.execute(f"SELECT tinh_thanh, COUNT(*) FROM [{t}] WHERE tinh_thanh IS NOT NULL AND tinh_thanh != '' GROUP BY tinh_thanh")
            for row in cur.fetchall():
                prov = str(row[0]).strip()
                if prov:
                    all_provinces[prov] += row[1]

            # Phân bố ngành nghề
            cur.execute(f"SELECT linh_vuc_nganh_nghe, COUNT(*) FROM [{t}] WHERE linh_vuc_nganh_nghe IS NOT NULL AND linh_vuc_nganh_nghe != '' GROUP BY linh_vuc_nganh_nghe")
            for row in cur.fetchall():
                ind = str(row[0]).strip()
                if ind and ind != 'Khác' and len(ind) > 2:
                    all_industries[ind] += row[1]

            # Lấy 3 việc làm mới nhất
            cur.execute(f"SELECT TOP 3 cong_viec, nha_tuyen_dung, tinh_thanh, muc_luong, url FROM [{t}] ORDER BY id DESC")
            for r in cur.fetchall():
                stats["recent_jobs"].append({
                    "source": meta["label"],
                    "title": str(r[0] or 'Tuyển dụng'),
                    "company": str(r[1] or 'Doanh nghiệp'),
                    "location": str(r[2] or 'Toàn quốc'),
                    "salary": str(r[3] or 'Thỏa thuận'),
                    "url": str(r[4] or '#')
                })

        conn.close()
    except Exception as e:
        print(f"Lỗi truy vấn SQL Server: {e}")

    # 2. Đọc Facebook Group Scraper JSON
    if os.path.exists(FB_JOBS_FILE):
        try:
            with open(FB_JOBS_FILE, "r", encoding="utf-8") as f:
                fb_data = json.load(f)
                posts = fb_data.get("posts", [])
                golds = fb_data.get("gold_leads", [])
                pots = fb_data.get("potential_leads", [])

                stats["facebook_leads"]["total"] = len(posts)
                stats["facebook_leads"]["gold_leads"] = len(golds)
                stats["facebook_leads"]["potential_leads"] = len(pots)

                fb_count = len(posts)
                stats["sources"].append({
                    "id": "facebook_group",
                    "name": "Facebook Group Leads",
                    "count": fb_count,
                    "companies_count": len(set(p.get("employer_name") for p in posts if p.get("employer_name"))),
                    "latest_time": fb_data.get("collected_at", datetime.now().isoformat())[:19],
                    "color": "#1877f2",
                    "icon": "fa-brands fa-facebook",
                    "status": "Lead Vàng Sẵn Sàng"
                })

                for p in posts:
                    loc = p.get("location") or "Toàn quốc"
                    all_provinces[loc] += 1
        except Exception as e:
            print(f"Lỗi đọc facebook_group_jobs.json: {e}")

    # Chuẩn hóa tỉnh thành Top 10
    top_provs = []
    for prov, count in all_provinces.most_common(8):
        clean_name = prov.replace("Thành phố", "TP.").replace("Tỉnh", "").strip()
        top_provs.append({"name": clean_name, "count": count})
    stats["provinces"] = top_provs

    # Chuẩn hóa ngành nghề Top 8
    top_inds = []
    for ind, count in all_industries.most_common(8):
        # Rút gọn tên ngành dài
        short_ind = ind.split('/')[0].split(',')[0].strip()
        top_inds.append({"name": short_ind, "count": count})
    stats["industries"] = top_inds

    stats["total_jobs"] = sum(s["count"] for s in stats["sources"])
    stats["total_companies"] = sum(s["companies_count"] for s in stats["sources"])
    stats["total_sources"] = len(stats["sources"])

    # Ghi ra file JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã xuất thành công báo cáo tổng quan ({stats['total_jobs']:,} việc làm từ {stats['total_sources']} nguồn) ra {OUTPUT_JSON}")
    return stats

if __name__ == "__main__":
    generate_stats()
