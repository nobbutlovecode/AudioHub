import os
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env (khi chạy ở máy tính local)
load_dotenv()

class Settings:
    # Lấy chuỗi kết nối Database. Nếu không tìm thấy, gán giá trị rỗng để tránh báo lỗi Type.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Sau này nếu có thêm biến môi trường (như SECRET_KEY, PORT), bạn khai báo thêm ở đây

# Khởi tạo một object duy nhất để các file khác import
settings = Settings()