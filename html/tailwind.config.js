/** @type {import('tailwindcss').Config} */
module.exports = {
  // Quét toàn bộ HTML + JS để biết class nào thực sự được dùng (giữ file CSS output nhỏ gọn)
  content: [
    "./*.html",
    "./components/*.html",
    "./js/*.js",
  ],
  theme: {
    extend: {
      // Màu chủ đạo lấy trực tiếp từ biến CSS --primary-h/-s/-l (đã có sẵn cho slider độ sáng).
      // Nhờ khai báo ở đây, HTML có thể viết "bg-primary", "text-primary", "hover:bg-primary-soft"
      // thay vì phải gõ tay "bg-[var(--primary)]" ở mọi nơi.
      colors: {
        primary: "hsl(var(--primary-h) var(--primary-s) var(--primary-l))",
        "primary-soft": "hsl(var(--primary-h) var(--primary-s) calc(var(--primary-l) + 18%))",
        "primary-deep": "hsl(var(--primary-h) var(--primary-s) calc(var(--primary-l) - 16%))",
        surface: "var(--surface)",
        "surface-glass": "var(--surface-glass)",
        "bg-body": "var(--bg-body)",
        "text-sub": "var(--text-sub)",
        "b-color": "var(--b-color)",
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "sans-serif"],
        display: ["Sora", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 15px var(--fx-glow)",
        "glow-lg": "0 0 25px var(--fx-glow)",
        "glow-xl": "0 0 50px var(--fx-glow)",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(.4, 0, .2, 1)",
        pop: "cubic-bezier(.2, .8, .2, 1)",
      },
      borderRadius: {
        card: "1rem",
      },
    },
  },
  plugins: [],
};
