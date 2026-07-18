import os
import pandas as pd
import psycopg2
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Cấu hình đường dẫn tuyệt đối cho HTML
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_DIR = os.path.abspath(os.path.join(BASE_DIR,"..", "html"))

# Đảm bảo đường dẫn gói chính xác theo cấu trúc thư mục python/ của bạn
from recommender import AudioRecommender
from schemas import RecommendRequest

from fastapi import Query


# Nạp biến môi trường từ file .env (ở local) hoặc cấu hình hệ thống (ở Cloud Render)
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Bộ nhớ đệm toàn cục trên RAM để lưu trữ dữ liệu thiết bị thô từ Neon DB
GLOBAL_PRODUCT_DF = None


@asynccontextmanager
async def lifespan(api_python: FastAPI):
    global GLOBAL_PRODUCT_DF
    print("🔌 [WEB SERVER] Đang kết nối Neon DB và nạp dữ liệu lên RAM Cache...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        query = "SELECT * FROM audio_gear;"
        raw_df = pd.read_sql(query, conn)
        conn.close()

        # BẪY TỰ VỆ (FALLBACK)
        required_cols = {
            "avg_price_vnd": 0, 
            "battery_life_total": 0,
            "codec_score": 1,
            "ip_rating": "None",
            "anc_type": "None",
            "anc_depth_db": 0,
            "power_watts": 0
        }
        for col, default_val in required_cols.items():
            if col not in raw_df.columns:
                raw_df[col] = default_val

        GLOBAL_PRODUCT_DF = raw_df
        print(f"✅ [RAM CACHE] Đã nạp thành công {len(raw_df)} sản phẩm. Hệ thống sẵn sàng tính toán!")
    except Exception as e:
        print(f"❌ Thất bại khi nạp dữ liệu từ Neon DB: {e}")
        GLOBAL_PRODUCT_DF = pd.DataFrame()
    yield


# Khởi tạo instance của Web API Service
api_service = FastAPI(
    title="AudioHub Web API Engine", version="1.0.0", lifespan=lifespan
)

# Cấu hình CORS
api_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount thư mục tĩnh và phục vụ file HTML cho trang chủ "/"
api_service.mount("/html", StaticFiles(directory=HTML_DIR), name="html")

@api_service.get("/")
async def serve_frontend():
    """Trả về giao diện Web tĩnh khi truy cập domain gốc"""
    return FileResponse(os.path.join(HTML_DIR, "index.html"))


# ĐÃ SỬA TỪ "/" THÀNH "/health" ĐỂ KHÔNG BỊ TRÙNG VỚI GIAO DIỆN WEB Ở TRÊN
@api_service.get("/health")
def read_root():
    """Endpoint kiểm tra trạng thái hoạt động của Web Server (Health Check)"""
    return {"status": "healthy", "service": "AudioHub Web API Engine"}

@api_service.get("/api/v1/search", status_code=status.HTTP_200_OK)
async def search_products(q: str = Query("", description="Từ khóa tìm kiếm")):
    """
    Endpoint tìm kiếm sản phẩm theo tên (Model) hoặc Hãng (Brand).
    Phục vụ cho thanh Search Bar Autocomplete trên Frontend.
    """
    if GLOBAL_PRODUCT_DF is None or GLOBAL_PRODUCT_DF.empty:
        return {"status": "empty", "data": []}
    
    query = q.strip().lower()
    if not query:
        return {"status": "success", "data": []}

    try:
        df = GLOBAL_PRODUCT_DF.copy()
        
        # Tiền xử lý: Ép kiểu string và xử lý NaN để tránh crash thuật toán tìm kiếm
        df['model_name_clean'] = df['model_name'].fillna('').astype(str).str.lower()
        df['brand_clean'] = df['brand'].fillna('').astype(str).str.lower()
        
        # Tìm kiếm chuỗi con (contains)
        mask = df['model_name_clean'].str.contains(query) | df['brand_clean'].str.contains(query)
               
        search_result = df[mask].head(6) # Trả về tối đa 6 kết quả để UI không bị tràn
        
        # Kiểm tra nếu DB của bạn không có cột 'id' thì lấy index làm ID tạm
        if 'id' not in search_result.columns:
            search_result = search_result.reset_index().rename(columns={'index': 'id'})
            
        # Chỉ lấy các cột cần thiết gửi về Frontend cho nhẹ
        cols_to_return = ['id', 'brand', 'model_name', 'price_vnd', 'category']
        # Lọc các cột thực sự tồn tại trong DB để tránh lỗi KeyError
        valid_cols = [col for col in cols_to_return if col in search_result.columns]
        
        result_list = search_result[valid_cols].to_dict(orient="records")
        
        return {
            "status": "success", 
            "data": result_list
        }
    except Exception as e:
        print(f"❌ Lỗi API Search: {str(e)}") # Báo lỗi ra log của Render
        return {"status": "error", "message": "Lỗi xử lý tìm kiếm", "data": []}
    
@api_service.post("/api/v1/recommend", status_code=status.HTTP_200_OK)
async def get_recommendations(payload: RecommendRequest):
    """
    Endpoint tiếp nhận trọng số động từ thanh kéo Slider của người dùng,
    thực thi thuật toán MCDM thời gian thực và trả ra kết quả xếp hạng.
    """
    if GLOBAL_PRODUCT_DF is None or GLOBAL_PRODUCT_DF.empty:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dữ liệu hệ thống chưa sẵn sàng hoặc kết nối Database thất bại.",
        )

    try:
        engine = AudioRecommender(GLOBAL_PRODUCT_DF)

        category = payload.category.upper()
        user_pref = payload.user_pref
        weights = payload.custom_weights

        if category == "TWS":
            result_df = engine.score_tws(user_pref=user_pref, custom_weights=weights)
        elif category == "WIRED":
            result_df = engine.score_wired(user_pref=user_pref, custom_weights=weights)
        elif category == "SPEAKER":
            result_df = engine.score_speaker(user_pref=user_pref, custom_weights=weights)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Danh mục '{category}' không hợp lệ. Hệ thống chỉ hỗ trợ: TWS, WIRED, SPEAKER.",
            )

        if payload.price_min is not None:
            result_df = result_df[result_df["avg_price_vnd"] >= payload.price_min]
        if payload.price_max is not None:
            result_df = result_df[result_df["avg_price_vnd"] <= payload.price_max]

        if result_df.empty:
            return {"status": "empty", "count": 0, "data": []}

        top_results = result_df.head(payload.limit)
        json_compatible_data = top_results.to_dict(orient="records")

        return {
            "status": "success",
            "count": len(json_compatible_data),
            "data": json_compatible_data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi xử lý toán học trên Web Server: {str(e)}",
        )