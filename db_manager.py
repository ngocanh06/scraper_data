"""
db_manager.py
─────────────
Module quản lý SQL Server cho hệ thống cào dữ liệu đa nguồn.

Dùng Windows Authentication (Trusted_Connection=yes) → không cần mật khẩu.

Mỗi website tuyển dụng sẽ có 1 bảng riêng trong cùng 1 database:
  - topcv          → bảng [dbo].[topcv]
  - vietnamworks   → bảng [dbo].[vietnamworks]
  - careerbuilder  → bảng [dbo].[careerbuilder]
  - v.v.

Cách dùng:
  from db_manager import JobDB

  db = JobDB()
  db.ensure_table('topcv')          # tạo bảng nếu chưa có
  db.insert('topcv', record_dict)   # chèn 1 bản ghi
  db.close()
"""

import os
import re
from pathlib import Path

import pyodbc


def _load_env_file() -> None:
    env_path = Path(__file__).with_name('.env')
    if not env_path.is_file():
        return

    for line_number, raw_line in enumerate(
        env_path.read_text(encoding='utf-8-sig').splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or not key.strip():
            raise ValueError(f'Cau hinh .env khong hop le tai dong {line_number}.')
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


_load_env_file()

# ──────────────────────────────────────────────
#  CẤU HÌNH KẾT NỐI SQL SERVER
#  Dùng Windows Authentication → không cần user/password
# ──────────────────────────────────────────────
SQL_SERVER = os.environ.get('SQL_SERVER', 'localhost')
DATABASE = os.environ.get('SQL_DATABASE', 'job_market')
DRIVER = os.environ.get('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')


class DatabasePersistenceError(RuntimeError):
    """Raised when a crawler cannot reliably persist or retrieve SQL data."""


class DatabaseWriteError(DatabasePersistenceError):
    """Raised when a crawler record could not be committed to SQL Server."""


class DatabaseReadError(DatabasePersistenceError):
    """Raised when existing SQL records could not be retrieved."""


def _get_connection_string(database: str = 'master') -> str:
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


# ──────────────────────────────────────────────
#  SQL TẠO DATABASE
# ──────────────────────────────────────────────
_CREATE_DB_SQL = f"""
IF NOT EXISTS (
    SELECT name FROM sys.databases WHERE name = N'{DATABASE}'
)
BEGIN
    CREATE DATABASE [{DATABASE}];
END
"""

# ──────────────────────────────────────────────
#  TEMPLATE TẠO BẢNG (thay {{table}} bằng tên nguồn)
# ──────────────────────────────────────────────
_CREATE_TABLE_TPL = """
IF NOT EXISTS (
    SELECT * FROM sys.tables WHERE name = N'{table}'
)
BEGIN
    CREATE TABLE [dbo].[{table}] (
        [id]                    INT IDENTITY(1,1) PRIMARY KEY,
        [url]                   NVARCHAR(600)  NOT NULL UNIQUE,
        [tinh_thanh]            NVARCHAR(200),
        [loai_hinh_cong_viec]   NVARCHAR(200),
        [linh_vuc_nganh_nghe]   NVARCHAR(300),
        [nha_tuyen_dung]        NVARCHAR(300),
        [cong_viec]             NVARCHAR(500),
        [chuc_vu]               NVARCHAR(200),
        [so_luong]              NVARCHAR(100),
        [gioi_tinh]             NVARCHAR(100),
        [do_tuoi]               NVARCHAR(100),
        [muc_luong]             NVARCHAR(200),
        [thoi_gian_lam_viec]    NVARCHAR(200),
        [dia_diem_chi_tiet]     NVARCHAR(MAX),
        [mo_ta_cong_viec]       NVARCHAR(MAX),
        [quyen_loi]             NVARCHAR(MAX),
        [kinh_nghiem]           NVARCHAR(MAX),
        [ky_nang]               NVARCHAR(MAX),
        [bang_cap]              NVARCHAR(500),
        [han_nop_ho_so]         NVARCHAR(100),
        [thong_tin_lien_he]     NVARCHAR(MAX),
        [scraped_at]            DATETIME2 DEFAULT GETDATE()
    );
    CREATE INDEX [idx_{table}_company]  ON [dbo].[{table}] ([nha_tuyen_dung]);
    CREATE INDEX [idx_{table}_location] ON [dbo].[{table}] ([tinh_thanh]);
    CREATE INDEX [idx_{table}_salary]   ON [dbo].[{table}] ([muc_luong]);
END
"""

# ──────────────────────────────────────────────
#  TEMPLATE INSERT (dùng MERGE để tránh trùng URL)
# ──────────────────────────────────────────────
_INSERT_TPL = """
MERGE [dbo].[{table}] AS target
USING (SELECT ? AS url) AS src ON target.url = src.url
WHEN MATCHED THEN
    UPDATE SET
        tinh_thanh            = ?,
        loai_hinh_cong_viec   = ?,
        linh_vuc_nganh_nghe   = ?,
        nha_tuyen_dung        = ?,
        cong_viec             = ?,
        chuc_vu               = ?,
        so_luong              = ?,
        gioi_tinh             = ?,
        do_tuoi               = ?,
        muc_luong             = ?,
        thoi_gian_lam_viec    = ?,
        dia_diem_chi_tiet     = ?,
        mo_ta_cong_viec       = ?,
        quyen_loi             = ?,
        kinh_nghiem           = ?,
        ky_nang               = ?,
        bang_cap              = ?,
        han_nop_ho_so         = ?,
        thong_tin_lien_he     = ?,
        scraped_at            = GETDATE()
WHEN NOT MATCHED THEN
    INSERT (
        url, tinh_thanh, loai_hinh_cong_viec, linh_vuc_nganh_nghe,
        nha_tuyen_dung, cong_viec, chuc_vu, so_luong, gioi_tinh, do_tuoi,
        muc_luong, thoi_gian_lam_viec, dia_diem_chi_tiet, mo_ta_cong_viec,
        quyen_loi, kinh_nghiem, ky_nang, bang_cap, han_nop_ho_so, thong_tin_lien_he
    ) VALUES (
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?
    );
"""

# Giới hạn độ dài cho cột NVARCHAR(n) — cột MAX không nằm trong map này
_FIELD_LIMITS = {
    'Ghi chú': 600,
    'Tỉnh thành': 200,
    'Loại hình công việc': 200,
    'Lĩnh vực/ngành nghề': 300,
    'Nhà tuyển dụng': 300,
    'Công việc': 500,
    'Chức vụ': 200,
    'Số lượng': 100,
    'Giới tính': 100,
    'Độ tuổi': 100,
    'Mức lương': 200,
    'Thời gian làm việc': 200,
    'Bằng cấp': 500,
    'Hạn nộp Hồ sơ': 100,
}

_WIDEN_COLUMNS_SQL = """
IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[{table}]') AND name = N'kinh_nghiem' AND max_length NOT IN (-1, 0))
    ALTER TABLE [dbo].[{table}] ALTER COLUMN [kinh_nghiem] NVARCHAR(MAX);
IF EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[{table}]') AND name = N'bang_cap' AND max_length NOT IN (-1, 0) AND max_length < 1000)
    ALTER TABLE [dbo].[{table}] ALTER COLUMN [bang_cap] NVARCHAR(500);
"""


def _clip(value, limit: int | None):
    if value is None:
        return ''
    text = str(value)
    if limit and len(text) > limit:
        return text[:limit]
    return text


# Ánh xạ key tiếng Việt trong dict → tên cột DB
_FIELD_MAP = [
    ('Ghi chú',              'url'),
    ('Tỉnh thành',           'tinh_thanh'),
    ('Loại hình công việc',  'loai_hinh_cong_viec'),
    ('Lĩnh vực/ngành nghề',  'linh_vuc_nganh_nghe'),
    ('Nhà tuyển dụng',       'nha_tuyen_dung'),
    ('Công việc',            'cong_viec'),
    ('Chức vụ',              'chuc_vu'),
    ('Số lượng',             'so_luong'),
    ('Giới tính',            'gioi_tinh'),
    ('Độ tuổi',              'do_tuoi'),
    ('Mức lương',            'muc_luong'),
    ('Thời gian làm việc',   'thoi_gian_lam_viec'),
    ('Địa điểm chi tiết',    'dia_diem_chi_tiet'),
    ('Mô tả công việc',      'mo_ta_cong_viec'),
    ('Quyền lợi',            'quyen_loi'),
    ('Kinh nghiệm',          'kinh_nghiem'),
    ('Kỹ năng',              'ky_nang'),
    ('Bằng cấp',             'bang_cap'),
    ('Hạn nộp Hồ sơ',        'han_nop_ho_so'),
    ('Thông tin liên hệ',    'thong_tin_lien_he'),
]


def _sanitize_table_name(name: str) -> str:
    """Chuẩn hoá tên nguồn thành tên bảng SQL Server hợp lệ."""
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9_]', '', name.replace(' ', '_').replace('-', '_'))
    if not name:
        raise ValueError(f"Ten nguon khong hop le: '{name}'")
    return name


def _detect_driver() -> str:
    """Tự động chọn ODBC driver SQL Server có sẵn trên máy."""
    preferred = list(dict.fromkeys([
        DRIVER,
        'ODBC Driver 17 for SQL Server',
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 13 for SQL Server',
        'SQL Server Native Client 11.0',
    ]))
    available = pyodbc.drivers()
    for drv in preferred:
        if drv in available:
            return drv
    raise RuntimeError(
        f"Khong tim thay ODBC driver SQL Server duoc ho tro: {preferred}.\n"
        f"Drivers co san: {available}"
    )


class JobDB:
    """
    Lớp quản lý kết nối SQL Server cho hệ thống đa nguồn.

    Ví dụ sử dụng:
        db = JobDB()
        db.ensure_table('topcv')
        db.insert('topcv', record)
        db.close()

        # Hoặc dùng context manager:
        with JobDB() as db:
            db.ensure_table('topcv')
            db.insert('topcv', record)
    """

    def __init__(self):
        self._driver = _detect_driver()
        print(f'[DB] Su dung driver: {self._driver}')
        self._conn = self._connect()
        self._tables_created: set[str] = set()

    # ── Kết nối ──────────────────────────────────────────────────────
    def _connect(self):
        """Tạo database nếu chưa có, rồi kết nối vào."""
        # Bước 1: kết nối vào master để tạo database
        conn_str_master = (
            f"DRIVER={{{self._driver}}};"
            f"SERVER={SQL_SERVER};"
            "DATABASE=master;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str_master, autocommit=True)
        cursor = conn.cursor()
        cursor.execute(_CREATE_DB_SQL)
        cursor.close()
        conn.close()

        # Bước 2: kết nối vào database chính
        conn_str = (
            f"DRIVER={{{self._driver}}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={DATABASE};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str)
        conn.autocommit = False
        print(f'[DB] Ket noi SQL Server thanh cong - database: {DATABASE}')
        return conn

    # ── Quản lý bảng ─────────────────────────────────────────────────
    def ensure_table(self, source: str) -> str:
        """Tạo bảng cho nguồn `source` nếu chưa tồn tại."""
        table = _sanitize_table_name(source)
        if table in self._tables_created:
            return table

        cursor = self._conn.cursor()
        cursor.execute(_CREATE_TABLE_TPL.format(table=table))
        for stmt in _WIDEN_COLUMNS_SQL.format(table=table).split(';'):
            sql = stmt.strip()
            if sql:
                cursor.execute(sql)
        self._conn.commit()
        cursor.close()
        self._tables_created.add(table)
        print(f'[DB] San sang bang: [{table}]')
        return table

    def list_tables(self) -> list[str]:
        """Liệt kê tất cả bảng trong database."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME;")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables

    def count(self, source: str) -> int:
        """Đếm số bản ghi trong bảng của nguồn."""
        table = _sanitize_table_name(source)
        cursor = self._conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM [dbo].[{table}];")
        n = cursor.fetchone()[0]
        cursor.close()
        return n

    def get_all_records(self, source: str) -> list[dict]:
        """Return all stored jobs in the crawler's Vietnamese field format."""
        table = self.ensure_table(source)
        columns = ', '.join(f'[{column}]' for _, column in _FIELD_MAP)
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                f"SELECT {columns} FROM [dbo].[{table}] ORDER BY [id];"
            )
            rows = cursor.fetchall()
        except pyodbc.Error as exc:
            raise DatabaseReadError(
                f"Khong the doc du lieu tu SQL Server table [{table}]."
            ) from exc
        finally:
            cursor.close()

        return [
            {
                field: value if value is not None else ''
                for (field, _), value in zip(_FIELD_MAP, row)
            }
            for row in rows
        ]

    # ── Insert ───────────────────────────────────────────────────────
    def insert(self, source: str, record: dict) -> bool:
        """
        Chèn 1 bản ghi vào bảng tương ứng với `source`.
        Dùng MERGE → bỏ qua nếu URL đã tồn tại.

        Returns True nếu insert thành công, False nếu bỏ qua (trùng).
        """
        table = self.ensure_table(source)
        url = record.get('Ghi chú', '') or record.get('url', '')
        if not url:
            raise DatabaseWriteError(
                f"Khong the luu ban ghi vao [{table}]: thieu URL trong truong "
                "'Ghi chú' hoac 'url'."
            )

        # Lấy giá trị theo thứ tự cột, cắt ngắn cột NVARCHAR(n) để tránh lỗi 2628
        values = [
            _clip(record.get(vi_key, '') or '', _FIELD_LIMITS.get(vi_key))
            for vi_key, _ in _FIELD_MAP
        ]
        # MERGE cần url (USING) + 19 values (UPDATE) + 20 values (INSERT)
        params = [url] + values[1:] + values

        cursor = self._conn.cursor()
        try:
            cursor.execute(_INSERT_TPL.format(table=table), params)
            affected = cursor.rowcount
            self._conn.commit()
        except pyodbc.Error as exc:
            self._conn.rollback()
            raise DatabaseWriteError(
                f"Khong the ghi ban ghi vao SQL Server table [{table}], URL: {url}"
            ) from exc
        finally:
            cursor.close()
        return affected >= 1

    def insert_many(self, source: str, records: list[dict]) -> tuple[int, int]:
        """Chèn nhiều bản ghi. Trả về (số inserted, số bỏ qua trùng)."""
        inserted = skipped = 0
        for r in records:
            if self.insert(source, r):
                inserted += 1
            else:
                skipped += 1
        return inserted, skipped

    # ── Đóng kết nối ─────────────────────────────────────────────────
    def close(self):
        if self._conn:
            self._conn.close()
            print('[DB] Da dong ket noi SQL Server.')

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
