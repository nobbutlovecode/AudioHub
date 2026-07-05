from pydantic import BaseModel
from typing import Dict, Any

class RecommendRequest(BaseModel):
    category: str                  # Danh mục thiết bị: TWS, WIRED, hoặc SPEAKER
    user_pref: Dict[str, Any]      # Cấu hình hoặc tiêu chí mong muốn của người dùng
    custom_weights: Dict[str, Any] # Trọng số động nhận từ các thanh kéo Slider của giao diện
    limit: int = 5                 # Số lượng sản phẩm tối ưu trả về (mặc định lấy top 5)