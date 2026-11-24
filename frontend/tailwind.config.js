/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f3eee6",
        cream: "#fbf7f2",
        ink: "#1c1917",
        stone: "#6f675f",
        line: "#e4dbd1",
        wine: "#6d2a38",
        clay: "#a68456",
      },
      fontFamily: {
        serif: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 16px 40px rgba(28, 25, 23, 0.06)",
      },
    },
  },
  plugins: [],
};
