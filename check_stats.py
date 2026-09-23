import os
import sys
import pyodbc
import pandas as pd
from datetime import datetime

# Đảm bảo in tiếng Việt và ký tự UTF-8 không bị lỗi trên terminal Windows (cp1252/cp437)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=job_market;Trusted_Connection=yes;TrustServerCertificate=yes;'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tables = [row[0] for row in cursor.fetchall() if row[0].lower() != 'sysdiagrams']
    
    print("=" * 68)
    print("📊 THỐNG KÊ DỮ LIỆU CÀO TRONG SQL SERVER (Database: job_market)")
    print("=" * 68)
    
    total_db = 0
    for t in sorted(tables):
        cursor.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cursor.fetchone()[0]
        
        # Kiểm tra cột ngày giờ cào
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{t}'")
        cols = [r[0].lower() for r in cursor.fetchall()]
        
        time_col = None
        for candidate in ['scraped_at', 'created_at', 'crawl_time', 'time']:
            if candidate in cols:
                time_col = candidate
                break
        
        today_info = ""
        latest_info = "Chưa có dữ liệu"
        if time_col:
            try:
                cursor.execute(f"SELECT MAX([{time_col}]) FROM [{t}]")
                res_max = cursor.fetchone()[0]
                if res_max:
                    latest_info = str(res_max)[:19]
                
                cursor.execute(f"SELECT COUNT(*) FROM [{t}] WHERE CAST([{time_col}] AS DATE) = CAST(GETDATE() AS DATE)")
                today_cnt = cursor.fetchone()[0]
                today_info = f" | Hôm nay: +{today_cnt:,}"
            except Exception:
                pass
                
        print(f"  🔹 Nguồn [{t.upper():<13}]: {count:>6,} việc làm{today_info:<20} (Mới nhất: {latest_info})")
        total_db += count
        
    print("-" * 68)
    print(f"👉 TỔNG CỘNG TOÀN BỘ DATABASE: {total_db:,} việc làm")
    print("=" * 68)
    conn.close()

except Exception as e:
    print(f"[!] Lỗi truy vấn Database: {e}")

# Thống kê file Excel
print("\n📁 THỐNG KÊ CÁC FILE EXCEL ĐÃ XUẤT:")
base_dir = os.path.dirname(os.path.abspath(__file__))
excel_files = [f for f in os.listdir(base_dir) if f.endswith(".xlsx") and not f.startswith("~$")]
if not excel_files:
    print("  (Chưa có file Excel nào được tạo)")
else:
    for ef in sorted(excel_files):
        fpath = os.path.join(base_dir, ef)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            df = pd.read_excel(fpath)
            print(f"  📄 {ef:<30}: {len(df):>6,} dòng ({size_mb:.2f} MB - Cập nhật: {mtime})")
        except Exception:
            print(f"  📄 {ef:<30}: {size_mb:.2f} MB - Cập nhật: {mtime}")
