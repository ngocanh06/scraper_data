import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from db_manager import JobDB

db = JobDB()
c = db._conn.cursor()
c.execute("""
    DELETE FROM jobsgo 
    WHERE tinh_thanh LIKE N'%Khương Đình%' 
       OR loai_hinh_cong_viec LIKE N'%triệu%'
       OR chuc_vu LIKE N'%triệu%'
       OR cong_viec LIKE N'%Công Ty%'
""")
db._conn.commit()
print("✅ Đã lọc sạch toàn bộ các bản ghi chưa chuẩn trong SQL Server!")
print("Số bản ghi chuẩn còn lại:", db.count('jobsgo'))
