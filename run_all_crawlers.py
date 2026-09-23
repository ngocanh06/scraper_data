"""
run_all_crawlers.py
───────────────────
Script điều phối chạy tuần tự cả 3 crawler:
1. JobsGO (jobsgo/crawl_jobsgo.py)
2. TopCV (topcv/crawl_matrix.py)
3. VietnamWorks (vietnamworks/crawl_vietnamworks.py)
"""

import sys
import os
import subprocess
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable

crawlers = [
    {
        "name": "JobsGO",
        "script": os.path.join(BASE_DIR, "jobsgo", "crawl_jobsgo.py"),
        "cwd": os.path.join(BASE_DIR, "jobsgo")
    },
    {
        "name": "TopCV",
        "script": os.path.join(BASE_DIR, "topcv", "crawl_matrix.py"),
        "cwd": os.path.join(BASE_DIR, "topcv")
    },
    {
        "name": "VietnamWorks",
        "script": os.path.join(BASE_DIR, "vietnamworks", "crawl_vietnamworks.py"),
        "cwd": os.path.join(BASE_DIR, "vietnamworks")
    },
    {
        "name": "CareerViet",
        "script": os.path.join(BASE_DIR, "careerviet", "crawl_careerviet.py"),
        "cwd": os.path.join(BASE_DIR, "careerviet")
    },
    {
        "name": "Vieclam24h",
        "script": os.path.join(BASE_DIR, "vieclam24h", "crawl_vieclam24h.py"),
        "cwd": os.path.join(BASE_DIR, "vieclam24h")
    }
]

print("=" * 70)
print("🚀 BẮT ĐẦU CHẠY CÀO DỮ LIỆU ĐA NGUỒN (JobsGO -> TopCV -> VietnamWorks -> CareerViet -> Vieclam24h)")
print("=" * 70)

for idx, c in enumerate(crawlers, 1):
    print(f"\n[{idx}/{len(crawlers)}] Đang khởi động Crawler: {c['name']}...")
    print(f"    - File: {c['script']}")
    print(f"    - Working Dir: {c['cwd']}")
    start_time = time.time()

    try:
        proc = subprocess.run(
            [PYTHON_EXE, c["script"]],
            cwd=c["cwd"],
            check=False
        )
        elapsed = time.time() - start_time
        print(f"[{idx}/{len(crawlers)}] Hoàn tất {c['name']} trong {elapsed/60:.1f} phút (Mã thoát: {proc.returncode}).")
    except Exception as e:
        print(f"[!] Lỗi khi chạy {c['name']}: {e}")

    time.sleep(3)

print("\n" + "=" * 70)
print("🎉 ĐÃ HOÀN TẤT TẤT CẢ CÁC TIẾN TRÌNH CÀO DỮ LIỆU!")
print("=" * 70)
