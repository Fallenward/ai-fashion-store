/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#14110f",
        cream: "#f4efe6",
        ink: "#4a3f36",
        stone: "#ddd2c6",
        line: "#6d6258",
        wine: "#7d3544",
        clay: "#e4c79a",
        white: "#241f1b",
      },
      fontFamily: {
        serif: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 16px 40px rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};
