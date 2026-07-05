import psycopg2

# Chuỗi kết nối của bạn
DATABASE_URL = "postgresql://neondb_owner:npg_WtqHZU8VIAz4@ep-lucky-flower-at6syakw-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

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