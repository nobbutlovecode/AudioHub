import psycopg2
from config import settings

DATABASE_URL = settings.DATABASE_URL

def rename_column():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Lệnh SQL để đổi tên cột
        print("Đang đổi tên cột 'sensity_db' thành 'sensitivity_db'...")
        cur.execute("ALTER TABLE audio_gear RENAME COLUMN sensity_db TO sensitivity_db;")
        
        conn.commit()
        print("✅ Thành công! Cột đã được đổi tên.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    rename_column()