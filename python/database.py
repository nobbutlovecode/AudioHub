import psycopg2
import pandas as pd
from config import settings

def get_all_products_from_db():
    """
    Kết nối tới Neon Postgres DB, lấy toàn bộ dữ liệu bảng audio_gear
    và trả về dưới dạng Pandas DataFrame.
    """
    print("🔌 [DATABASE] Đang thiết lập kết nối tới Neon DB...")
    try:
        # Sử dụng cấu hình từ file config.py
        conn = psycopg2.connect(settings.DATABASE_URL)
        query = "SELECT * FROM audio_gear;"
        
        # Đọc thẳng dữ liệu từ SQL vào Pandas DataFrame
        df = pd.read_sql(query, conn)
        conn.close()
        
        return df
    except Exception as e:
        print(f"❌ [DATABASE] Thất bại khi nạp dữ liệu từ Neon DB: {e}")
        # Trả về DataFrame rỗng nếu kết nối lỗi để app không bị sập (crash)
        return pd.DataFrame()