/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "temple-gold": "#B8860B",
        "temple-rust": "#8B2500",
        "temple-saffron": "#FF6B35",
        "temple-deep": "#1A0A2E",
        "temple-cream": "#FFF8F0",
        indigoTemple: "#1A0A2E",
        goldTemple: "#B8860B",
        saffronTemple: "#FF6B35",
        creamTemple: "#FFF8F0",
        nightTemple: "#12071F",
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "serif"],
        sans: ["Inter", "Arial", "sans-serif"],
        mono: ["Courier New", "monospace"],
        serifTemple: ["Georgia", "Cambria", "serif"],
        sansTemple: ["Inter", "Arial", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(184, 134, 11, 0.25), 0 20px 60px rgba(0, 0, 0, 0.35)",
      },
      backgroundImage: {
        "temple-radial":
          "radial-gradient(circle at top, rgba(255, 107, 53, 0.2), transparent 30%), radial-gradient(circle at bottom right, rgba(184, 134, 11, 0.12), transparent 36%)",
      },
    },
  },
  plugins: [],
};
