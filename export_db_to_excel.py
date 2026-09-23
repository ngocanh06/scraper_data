"""
Xuất toàn bộ dữ liệu hiện có trong bảng [dbo].[topcv] ra file Excel topcv_matrix_jobs.xlsx
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
from db_manager import JobDB

if __name__ == '__main__':
    print("[DB] Đang kết nối SQL Server để xuất file Excel...")
    db = JobDB()
    table_name = 'topcv'
    
    cursor = db._conn.cursor()
    cursor.execute(f"SELECT * FROM [dbo].[{table_name}] ORDER BY id DESC")
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    
    print(f"[DB] Tìm thấy {len(rows)} bản ghi trong SQL Server.")
    
    if rows:
        data = [dict(zip(columns, row)) for row in rows]
        df = pd.DataFrame(data)
        
        output_file = 'topcv_matrix_jobs.xlsx'
        try:
            df.to_excel(output_file, index=False)
            print(f"✅ Đã xuất thành công {len(rows)} bản ghi ra file: {output_file}")
        except PermissionError:
            alt_output = 'topcv_matrix_jobs_out.xlsx'
            df.to_excel(alt_output, index=False)
            print(f"⚠️ File {output_file} đang mở trong Excel! Đã xuất ra file phụ: {alt_output}")
    else:
        print("Chưa có bản ghi nào trong Database.")
        
    db.close()
