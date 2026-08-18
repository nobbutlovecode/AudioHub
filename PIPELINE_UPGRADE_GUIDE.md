# Nâng cấp Pipeline Frontend AudioHub — Tailwind CDN → Tailwind Build Thật

## 1. Vấn đề gốc (nhắc lại ngắn gọn)

Giao diện trước đây dùng **Tailwind Play CDN** (`<script src="https://cdn.tailwindcss.com">`) —
bản này biên dịch class ngay trên trình duyệt người dùng, **không đọc được file cấu hình
`tailwind.config.js`** để định nghĩa token thiết kế riêng (màu, spacing, shadow...). Hệ quả:

- Mọi màu/hiệu ứng phải viết tay bằng cú pháp "arbitrary value" (`bg-[var(--x)]`) lặp đi lặp lại.
- Không có khái niệm "1 component Button dùng ở mọi nơi" — mỗi file HTML tự viết lại nút bấm,
  dẫn tới các khối điều khiển không đồng bộ, không khớp bản thiết kế "Black Gold / Clean Light".
- Thiếu hoàn toàn thư viện vẽ biểu đồ (radar, tần số) cho các trang như Product Detail sau này.

## 2. Giải pháp: dựng lại pipeline bằng Tailwind CLI thật

### File mới được thêm vào `html/`

| File | Vai trò |
|---|---|
| `html/package.json` | Khai báo dependency `tailwindcss` + 2 lệnh: `npm run build` (build 1 lần, nén) và `npm run watch` (build lại mỗi khi sửa CSS, dùng lúc code local) |
| `html/tailwind.config.js` | **Nguồn sự thật duy nhất** cho token thiết kế: màu `primary`/`primary-soft`/`primary-deep` (đọc trực tiếp từ biến `--primary-h/-s/-l` đã có sẵn cho slider độ sáng), font `Sora`/`Inter`, box-shadow `glow`, easing riêng |
| `html/src/input.css` | File nguồn Tailwind — toàn bộ CSS từng nằm trong thẻ `<style>` của `index.html` đã dọn vào đây, cộng thêm **hệ thống component mới**: `.btn-primary/.btn-secondary/.btn-ghost/.btn-icon` (đủ 4 trạng thái Default/Hover/Pressed/Disabled), `.toggle-switch`, `.slider-control`, `.input-field`, `.chip`, `.stepper` |
| `html/dist/output.css` | File CSS đã biên dịch, tối ưu — đây là file thật sự được `index.html` load qua `<link>` |

### File đã sửa

- **`html/index.html`**: gỡ `<script src="cdn.tailwindcss.com">` + toàn bộ `<style>` inline, thay bằng
  `<link rel="stylesheet" href="/html/dist/output.css">`. Thêm Chart.js qua CDN
  (`chart.umd.min.js`) để sẵn sàng cho biểu đồ radar/tần số ở các trang sau. Các nút chính
  (Run, C-List, nút đóng modal) đã đổi sang class mới (`btn-primary`, `btn-secondary`, `btn-icon`)
  thay vì chuỗi utility viết tay.
- **`html/components/{about,clist,donate}.html`**: nút đóng modal đổi sang `.btn-icon`; nút
  "Run Comparison Algorithm" trong `clist.html` đổi sang `.btn-primary`.
- **`Dockerfile`**: viết lại thành **multi-stage build** (chi tiết ở mục 4).
- **`.gitignore` / `.dockerignore`**: bỏ qua `html/node_modules/` và `html/dist/` (được build lại
  mỗi lần deploy, không cần commit).
- **`python/rename_db.py`**: xoá mật khẩu DB hard-code, dùng chung `config.py` (bảo mật).
- Xoá file `import os.txt` — file scratch còn sót lại chứa mật khẩu DB thật, đã commit công khai.

## 3. Vì sao token màu vẫn "sống" (real-time) dù giờ đã build sẵn?

Slider chỉnh độ sáng gold/cyan trước đây hoạt động nhờ JS đổi trực tiếp biến CSS
`--primary-l` trên `<html>`. Pipeline mới **không phá vỡ điều này** — `tailwind.config.js` định
nghĩa `primary: "hsl(var(--primary-h) var(--primary-s) var(--primary-l))"`, tức là class
`bg-primary` được build ra thành CSS **vẫn tham chiếu biến CSS**, không phải giá trị màu cố định.
Vì vậy khi JS đổi `--primary-l` lúc runtime, mọi nơi dùng `bg-primary`/`text-primary`/`.btn-primary`
vẫn tự động đổi màu theo — không cần build lại.

## 4. Cách Docker/Render build hoạt động bây giờ

```
Stage 1 (node:20-slim)          Stage 2 (python:3.10-slim)
┌─────────────────────┐         ┌──────────────────────────┐
│ npm install          │         │ pip install -r            │
│ npm run build         │  --->  │   requirements.txt        │
│ -> dist/output.css    │ copy   │ COPY . .                  │
└─────────────────────┘   dist  │ COPY --from=frontend-build │
                                  │   /build/dist ./html/dist │
                                  └──────────────────────────┘
```

Mỗi lần Render deploy, CSS **luôn được build lại từ `tailwind.config.js` + `src/input.css`** —
không lệ thuộc vào việc có ai lỡ quên build/commit `dist/output.css` cũ hay không.

### 2 bug khác phát hiện khi test Dockerfile thật (đã sửa kèm)

1. `COPY requirements.txt .` — file thật nằm ở `python/requirements.txt`, không phải gốc repo.
   Build sẽ báo lỗi "file not found" nếu Root Directory trên Render trỏ đúng gốc repo.
2. `CMD uvicorn python.main:api_service` — khi chạy thật, lệnh này ném
   `ModuleNotFoundError: No module named 'recommender'` vì thư mục `python/` chưa từng nằm
   trong `PYTHONPATH`. Đã sửa thành `uvicorn main:api_service --app-dir python` — đã test chạy
   thật (curl trả `200` cho `/`, `/html/dist/output.css`, `/health`).

## 5. Cách chạy ở máy local

```bash
# Lần đầu / khi cần cài lại dependency
cd html
npm install

# Trong lúc code, sửa src/input.css hoặc tailwind.config.js
npm run watch          # tự build lại mỗi lần lưu file

# Build 1 lần trước khi deploy thủ công (không cần nếu dùng Docker, Docker tự build)
npm run build

# Chạy backend (từ thư mục gốc repo)
cd ..
uvicorn main:api_service --app-dir python --host 0.0.0.0 --port 8000
```

Mở `http://localhost:8000` — nếu thấy giao diện load bình thường nhưng CSS trông "trần trụi"
(không có style), 90% là quên chạy `npm run build` trước.

## 6. Cách thêm component mới trong tương lai (giữ đúng kỷ luật design system)

Không viết class Tailwind rời rạc trực tiếp trong HTML cho các khối lặp lại. Thay vào đó:

1. Mở `html/src/input.css`, thêm class mới trong `@layer components { ... }`.
2. Dùng lại token đã có (`var(--primary)`, `shadow-glow`, `ease-smooth`...) thay vì số liệu tự chế.
3. Chạy `npm run build` (hoặc để `npm run watch` tự làm).
4. Dùng class đó ở HTML — ví dụ `<button class="btn-primary">...</button>`.

**Lưu ý quan trọng**: Tailwind build thật sẽ **tự động xoá (purge)** những class không được
dùng ở bất kỳ đâu trong `content` (khai báo trong `tailwind.config.js`). Một số class mình đã
viết sẵn (`.chip`, `.stepper`, `.toggle-switch`) hiện **chưa xuất hiện trong `dist/output.css`**
vì chưa có phần tử HTML nào dùng tới — đây là hành vi đúng, không phải lỗi. Chúng sẽ tự động có
mặt trong lần build kế tiếp ngay khi bạn dùng class đó ở một file HTML nào đó.

## 7. Chart.js — sẵn sàng cho Product Detail (radar/tần số)

Đã thêm CDN Chart.js vào `index.html`. Ví dụ tối thiểu để dựng biểu đồ "Sound Profile" dạng radar
(giống ảnh tham khảo Protech bạn gửi trước đó):

```html
<canvas id="soundProfileChart"></canvas>
<script>
new Chart(document.getElementById('soundProfileChart'), {
  type: 'radar',
  data: {
    labels: ['Bass', 'Mids', 'Treble', 'Soundstage', 'Detail'],
    datasets: [{
      label: 'Sound Profile',
      data: [8, 6, 7, 5, 9],
      backgroundColor: 'hsl(var(--primary-h) var(--primary-s) var(--primary-l) / 0.25)',
      borderColor: 'hsl(var(--primary-h) var(--primary-s) var(--primary-l))',
    }]
  }
});
</script>
```

Đây chỉ là điểm khởi đầu — trang Product Detail đầy đủ (gallery, rating breakdown, "in the box"...)
chưa tồn tại trong site hiện tại, cần xây mới khi bạn sẵn sàng làm trang đó.

## 8. Đã test thật, chưa test được gì

**Đã test (trong sandbox)**:
- `npm run build` chạy thành công, các class mới xuất hiện đúng trong `dist/output.css`.
- Cú pháp toàn bộ JS trong `index.html` và `app.js` hợp lệ sau khi sửa.
- Chạy `uvicorn main:api_service --app-dir python` thật, `curl` xác nhận `/`, `/html/dist/output.css`,
  `/html/js/app.js`, `/health` đều trả `200`.

**Chưa test được** (do sandbox không có Docker daemon và không có mạng ra Neon thật):
- Chưa build được Docker image thật (`docker build .`) — cấu trúc COPY đã kiểm tra thủ công kỹ,
  nhưng bạn nên tự chạy `docker build .` một lần trước khi push lên Render để chắc chắn.
- Chưa test kết nối Neon DB thật (do sandbox chặn mạng ra ngoài) — lỗi `❌ Thất bại khi nạp dữ liệu`
  trong log test chỉ vì sandbox không có Postgres thật, không phải lỗi trong code.
