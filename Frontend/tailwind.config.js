/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../Backend/templates/**/*.html",
    "../Backend/*/templates/**/*.html",
    "../Backend/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f2f6fc",
          100: "#e3ecf8",
          200: "#c7d9f0",
          300: "#9dbde3",
          400: "#6c99d1",
          500: "#4a7bb8",
          600: "#37619a",
          700: "#2d4f7d",
          800: "#1f3a5f",
          900: "#12294a",
          950: "#081a33",
        },
        accent: {
          50: "#fff7ed",
          100: "#ffedd5",
          200: "#fed7aa",
          300: "#fdba74",
          400: "#fb923c",
          500: "#f97316",
          600: "#ea580c",
          700: "#c2410c",
          800: "#9a3412",
          900: "#7c2d12",
          950: "#431407",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
