/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./*.html",
    "./components/*.html",
    "./js/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: "var(--primary)",
        "primary-soft": "var(--primary-soft)",
        "primary-deep": "var(--primary-deep)",
        surface: "var(--surface)",
        "surface-alt": "var(--surface-alt)",
        "surface-glass": "var(--surface-glass)",
        "bg-body": "var(--bg-body)",
        "text-main": "var(--text-main)",
        "text-sub": "var(--text-sub)",
        "text-heading": "var(--text-heading)",
        "b-color": "var(--b-color)",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Inter", "sans-serif"],
        display: ["Sora", "Plus Jakarta Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};
