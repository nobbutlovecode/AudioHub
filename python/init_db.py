import psycopg2
import pandas as pd
import numpy as np

# Chuỗi kết nối tới Neon Cloud của bạn
DATABASE_URL = "postgresql://neondb_owner:npg_WtqHZU8VIAz4@ep-lucky-flower-at6syakw-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Giữ nguyên CODEC_MAPPING theo logic hệ thống của bạn
CODEC_MAPPING = {
    'sbc': 1, 'aac': 2, 'aptx': 3, 'aptx hd': 3, 'aptx adaptive': 4, 'ldac': 5, 'lhdc': 5
}

def clean_val(val, target_type):
    """Ép kiểu dữ liệu an toàn, bẫy lỗi các ô trống hoặc text lỗi"""
    if pd.isna(val) or str(val).strip().lower() in ['none', 'null', 'nan', '']:
        return 0 if target_type in [int, float] else "None"
    try:
        if target_type == int:
            return int(float(str(val).strip().replace('Ω', '').replace('dB', '').replace('.', '').replace(',', '')))
        if target_type == float:
            return float(str(val).strip().replace('mm', ''))
        return str(val).strip()
    except:
        return 0 if target_type in [int, float] else "None"

def init_database():
    file_path = "audio_gear.csv" 
    sheets = ['Wired', 'TWS', 'Speaker']
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 1. TỰ ĐỘNG RESET BẢNG CŨ ĐỂ TRÁNH XUNG ĐỘT RÀNG BUỘC
        print("[->] Đang khởi tạo lại cấu trúc bảng chuẩn...")
        cur.execute("DROP TABLE IF EXISTS audio_gear CASCADE;")
        
        # 2. TẠO BẢNG MỚI VỚI RÀNG BUỘC UNIQUE(model_name) ĐỂ ON CONFLICT HOẠT ĐỘNG
        cur.execute("""
            CREATE TABLE audio_gear (
                id SERIAL PRIMARY KEY,
                category VARCHAR(50),
                model_name VARCHAR(100) UNIQUE NOT NULL,
                brand VARCHAR(50),
                price_vnd BIGINT DEFAULT 0,
                sound_signature VARCHAR(50) DEFAULT 'Neutral',
                driver_type VARCHAR(50) DEFAULT 'Dynamic',
                driver_material VARCHAR(100) DEFAULT 'Standard',
                driver_size_mm NUMERIC(5,2) DEFAULT 0.0,
                impedance_ohm INTEGER DEFAULT 0,
                sensitivity_db INTEGER DEFAULT 0
            );
        """)
        conn.commit()
        print("[✓] Cấu trúc bảng audio_gear với khóa UNIQUE đã sẵn sàng.")

        # 3. ĐỌC FILE ĐA SHEET VÀ NẠP DỮ LIỆU
        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        
        for sheet in sheets:
            if sheet not in excel_file.sheet_names:
                print(f"⚠️ Không tìm thấy sheet '{sheet}' trong file, bỏ qua.")
                continue
                
            print(f"--- Đang nạp sheet: {sheet} ---")
            df = excel_file.parse(sheet)
            
            for _, row in df.iterrows():
                model_name = str(row.get('model_name', '')).strip()
                if not model_name or model_name.lower() in ['none', 'nan', '']:
                    continue
                    
                brand = str(row.get('brand', 'Unknown')).strip()
                price = clean_val(row.get('price_vnd', row.get('avg_price_vnd', 0)), int)
                sound = str(row.get('sound_signature', 'Neutral')).strip()
                dtype = str(row.get('driver_type', 'Dynamic')).strip()
                dmat = str(row.get('driver_material', 'Standard')).strip()
                dsize = clean_val(row.get('driver_size_mm', 0.0), float)
                impedance = clean_val(row.get('impedance_ohm', 0), int)
                sensitivity = clean_val(row.get('sensity_db', row.get('sensitivity_db', 110)), int)
                
                # Thực thi ghi dữ liệu an toàn (Upsert)
                cur.execute("""
                    INSERT INTO audio_gear (category, model_name, brand, price_vnd, sound_signature, driver_type, driver_material, driver_size_mm, impedance_ohm, sensitivity_db)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (model_name) DO UPDATE SET
                        category = EXCLUDED.category,
                        brand = EXCLUDED.brand,
                        price_vnd = EXCLUDED.price_vnd,
                        sound_signature = EXCLUDED.sound_signature,
                        driver_type = EXCLUDED.driver_type,
                        driver_material = EXCLUDED.driver_material,
                        driver_size_mm = EXCLUDED.driver_size_mm,
                        impedance_ohm = EXCLUDED.impedance_ohm,
                        sensitivity_db = EXCLUDED.sensitivity_db;
                """, (sheet, model_name, brand, price, sound, dtype, dmat, dsize, impedance, sensitivity))
            
            conn.commit()
            print(f"✅ Đã nạp xong hoàn toàn phân vùng sheet: {sheet}")
            
        cur.close()
        conn.close()
        print("\n[✓✓✓] QUÁ TRÌNH MIGRATION HOÀN THÀNH TUYỆT ĐỐI VÀO NEON CLOUD VỚI ĐA SHEET!")
        
    except Exception as e:
        print(f"❌ Lỗi hệ thống trong quá trình thực thi: {e}")

if __name__ == "__main__":
    init_database()