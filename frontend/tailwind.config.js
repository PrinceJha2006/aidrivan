/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        mist: "#e2e8f0",
        lime: "#84cc16",
        sky: "#0ea5e9",
        coral: "#fb7185",
        ocean: "#0f766e",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(2, 6, 23, 0.12)",
        glow: "0 18px 40px rgba(14, 165, 233, 0.22)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        floaty: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-7px)" },
        },
      },
      animation: {
        rise: "rise 0.6s ease-out forwards",
        floaty: "floaty 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
