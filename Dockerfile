# =====================================================================
# STAGE 1 — Build CSS thật bằng Tailwind CLI (thay cho Play CDN)
# Mỗi lần deploy, Render sẽ tự chạy lại bước này để dist/output.css
# luôn khớp với tailwind.config.js + src/input.css mới nhất — không
# cần commit file CSS đã build vào git.
# =====================================================================
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY html/package.json ./
RUN npm install
COPY html/tailwind.config.js ./
COPY html/src ./src
COPY html/*.html ./
COPY html/components ./components
COPY html/js ./js
RUN npm run build

# =====================================================================
# STAGE 2 — Chạy backend Python, phục vụ luôn CSS đã build ở Stage 1
# =====================================================================
FROM python:3.10-slim
WORKDIR /app

# FIX #1: requirements.txt thật sự nằm ở python/requirements.txt, không phải ở gốc repo
COPY python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Ghi đè bằng bản CSS vừa build ở Stage 1 (đảm bảo luôn mới nhất)
COPY --from=frontend-build /build/dist ./html/dist

# FIX #2 + #3: "uvicorn python.main:api_service" (bản gốc) ném ModuleNotFoundError
# cho 'recommender' vì thư mục python/ chưa từng nằm trong sys.path. Dùng --app-dir
# để uvicorn tự thêm python/ vào PYTHONPATH trước khi import main — đã test chạy
# thật (curl trả 200) trong quá trình sửa.
CMD ["sh", "-c", "uvicorn main:api_service --app-dir python --host 0.0.0.0 --port ${PORT:-8000}"]
