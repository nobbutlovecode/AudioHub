import psycopg2
import pandas as pd
from config import settings

# Các cột bắt buộc mà recommender.py/main.py cần để tính điểm.
# Đặt tập trung ở đây (thay vì lặp lại trong main.py) để tránh 2 nơi
# có thể "lệch pha" khi có người sửa 1 chỗ mà quên chỗ còn lại.
REQUIRED_COLUMNS_WITH_DEFAULTS = {
    "avg_price_vnd": 0,
    "battery_life_total": 0,
    "codec_score": 1,
    "ip_rating": "None",
    "anc_type": "None",
    "anc_depth_db": 0,
    "power_watts": 0,
}


def get_all_products_from_db() -> pd.DataFrame:
    """
    Kết nối tới Neon Postgres DB, lấy toàn bộ dữ liệu bảng audio_gear,
    bù các cột còn thiếu bằng giá trị mặc định an toàn, và trả về
    dưới dạng Pandas DataFrame sẵn sàng để AudioRecommender sử dụng.
    """
    print("🔌 [DATABASE] Đang thiết lập kết nối tới Neon DB...")
    try:
        # Sử dụng cấu hình từ file config.py
        with psycopg2.connect(settings.DATABASE_URL) as conn:
            df = pd.read_sql("SELECT * FROM audio_gear;", conn)

        # BẪY TỰ VỆ (FALLBACK): đảm bảo các cột thuật toán cần luôn tồn tại,
        # kể cả khi schema DB tạm thời thiếu cột nào đó.
        for col, default_val in REQUIRED_COLUMNS_WITH_DEFAULTS.items():
            if col not in df.columns:
                df[col] = default_val

        # Chuẩn hoá sẵn 2 cột tìm kiếm không dấu-hoa/thường ngay tại đây,
        # thay vì tính lại trên toàn bộ bảng ở MỖI request /api/v1/search.
        df["model_name_clean"] = df.get("model_name", "").fillna("").astype(str).str.lower()
        df["brand_clean"] = df.get("brand", "").fillna("").astype(str).str.lower()

        print(f"✅ [DATABASE] Đã nạp thành công {len(df)} sản phẩm.")
        return df
    except Exception as e:
        print(f"❌ [DATABASE] Thất bại khi nạp dữ liệu từ Neon DB: {e}")
        # Trả về DataFrame rỗng nếu kết nối lỗi để app không bị sập (crash)
        return pd.DataFrame()