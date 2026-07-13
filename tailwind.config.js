/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/**/*.js"],
  theme: {
    extend: {
      colors: {
        cream: "#FDF6E3",
        paper: "#F5EDE3",
        mahogany: { DEFAULT: "#8B5A2B", dark: "#6F4621", light: "#A9744A" },
        sage: "#8A9A5B",
        charcoal: "#2C2C2C",
        gold: "#D4A437",
      },
      fontFamily: {
        serif: ['"Playfair Display"', "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: { lg: "14px", md: "10px", sm: "8px" },
      boxShadow: {
        card: "0 1px 2px rgba(44,44,44,0.06), 0 10px 28px -14px rgba(139,90,43,0.22)",
        lift: "0 18px 40px -16px rgba(139,90,43,0.32)",
      },
    },
  },
  plugins: [],
};
