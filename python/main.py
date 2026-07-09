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