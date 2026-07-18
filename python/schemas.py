from pydantic import BaseModel
from typing import Dict, Any, Optional

class RecommendRequest(BaseModel):
    category: str                  # Danh mục thiết bị: "TWS", "WIRED", hoặc "SPEAKER"
    user_pref: str                 # ĐÃ SỬA: Kiểu str để nhận trực tiếp gu âm thanh (e.g., "Warm", "Neutral", "V-Shape")
    custom_weights: Optional[Dict[str, Any]] = None  # FIX: Optional — frontend hiện tại không gửi field này,
                                                      # nếu để required sẽ bị FastAPI trả 422 và thuật toán
                                                      # không bao giờ được gọi tới (đây chính là bug C-List).
    price_min: Optional[float] = None  # FIX: được frontend gửi lên nhưng trước đây không có trong schema
    price_max: Optional[float] = None  # -> Pydantic mặc định bỏ qua field lạ, filter giá coi như vô dụng.
    limit: int = 5                 # Số lượng sản phẩm tối ưu trả về (mặc định lấy top 5)