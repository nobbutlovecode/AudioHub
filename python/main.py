# python/main.py
import os
import pandas as pd
import psycopg2
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Đảm bảo đường dẫn gói chính xác theo cấu trúc thư mục python/ của bạn
from python.recommender import AudioRecommender
from python.schemas import RecommendRequest

# Nạp biến môi trường từ file .env (ở local) hoặc cấu hình hệ thống (ở Cloud Render)
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Bộ nhớ đệm toàn cục trên RAM để lưu trữ dữ liệu thiết bị thô từ Neon DB
GLOBAL_PRODUCT_DF = None


@asynccontextmanager
async def lifespan(api_python: FastAPI):
    """
    Lifespan event: Chạy duy nhất 1 lần khi Web Server khởi động.
    Kéo toàn bộ dữ liệu từ Neon DB lên RAM để tối ưu hóa tốc độ tính toán MCDM (< 10ms/request)
    """
    global GLOBAL_PRODUCT_DF
    print(
        "🔌 [WEB SERVER] Đang kết nối Neon DB để đồng bộ dữ liệu thiết bị..."
    )
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # SỬA ĐỔI: Sử dụng chính xác tên bảng 'audio_gear' của dự án AudioHub
        query = "SELECT * FROM audio_gear;"
        GLOBAL_PRODUCT_DF = pd.read_sql_query(query, conn)
        conn.close()
        # SỬA ĐỔI: Bổ sung chữ f-string để hiển thị chính xác số lượng bản ghi
        print(
            f"✅ [WEB SERVER] Đã nạp thành công {len(GLOBAL_PRODUCT_DF)} sản phẩm vào RAM Cache!"
        )
    except Exception as e:
        print(
            f"❌ [WEB SERVER] Thất bại khi đồng bộ dữ liệu từ Cloud DB: {e}"
        )
        # Dự phòng phương án DB sập: Khởi tạo DataFrame rỗng để tránh crash sập toàn bộ Web Server
        GLOBAL_PRODUCT_DF = pd.DataFrame()
    yield
    print("🛑 [WEB SERVER] Đang giải phóng tài nguyên hệ thống...")


# Khởi tạo instance của Web API Service (Đã sửa lỗi thiếu dấu phẩy)
api_service = FastAPI(
    title="AudioHub Web API Engine", version="1.0.0", lifespan=lifespan
)

# Cấu hình CORS - Bắt buộc phải có đối với mô hình Web Application biệt lập Frontend-Backend
# Giúp trình duyệt cho phép Frontend (React/Next.js) gọi API sang Backend an toàn
api_service.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Trong môi trường Production chạy lâu dài sẽ cấu hình domain cụ thể của Web Frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api_service.get("/")
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
        # 1. Khởi tạo lõi thuật toán từ dữ liệu cached trên RAM
        engine = AudioRecommender(GLOBAL_PRODUCT_DF)

        category = payload.category.upper()
        user_pref = payload.user_pref
        weights = payload.custom_weights

        # 2. Phân luồng xử lý ma trận toán học dựa theo phân loại thiết bị âm thanh
        if category == "TWS":
            result_df = engine.score_tws(
                user_pref=user_pref, custom_weights=weights
            )
        elif category == "WIRED":
            result_df = engine.score_wired(
                user_pref=user_pref, custom_weights=weights
            )
        elif category == "SPEAKER":
            result_df = engine.score_speaker(
                user_pref=user_pref, custom_weights=weights
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Danh mục '{category}' không hợp lệ. Hệ thống chỉ hỗ trợ: TWS, WIRED, SPEAKER.",
            )

        if result_df.empty:
            return {"status": "empty", "count": 0, "data": []}

        # 3. Giới hạn số lượng bản ghi tối ưu trả về hiển thị lên giao diện Web UI (Mặc định top 5)
        top_results = result_df.head(payload.limit)

        # 4. Chuyển đổi Pandas DataFrame thành cấu trúc List[Dict] chuẩn mã hóa JSON
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