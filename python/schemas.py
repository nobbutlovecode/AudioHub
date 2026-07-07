from pydantic import BaseModel
from typing import Dict, Any

class RecommendRequest(BaseModel):
    category: str                  # Danh mục thiết bị: "TWS", "WIRED", hoặc "SPEAKER"
    user_pref: str                 # ĐÃ SỬA: Kiểu str để nhận trực tiếp gu âm thanh (e.g., "Warm", "Neutral", "V-Shape")
    custom_weights: Dict[str, Any] # Trọng số động nhận từ các thanh kéo Slider của giao diện dưới dạng Key-Value
    limit: int = 5                 # Số lượng sản phẩm tối ưu trả về (mặc định lấy top 5)