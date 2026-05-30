import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#0a0f1e", light: "#111827", card: "#0d1424", border: "#1e2d45" },
        teal: { DEFAULT: "#00d4aa", light: "#00f0c0", muted: "rgba(0,212,170,0.1)" },
        blue: { accent: "#3b82f6", muted: "rgba(59,130,246,0.1)" },
        amber: { accent: "#f59e0b", muted: "rgba(245,158,11,0.1)" },
        red: { accent: "#ef4444", muted: "rgba(239,68,68,0.1)" },
        green: { accent: "#22c55e", muted: "rgba(34,197,94,0.1)" },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "hero-gradient": "linear-gradient(135deg, #0a0f1e 0%, #0d1a2e 50%, #0a1628 100%)",
        "card-gradient": "linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)",
        "teal-gradient": "linear-gradient(135deg, #00d4aa 0%, #3b82f6 100%)",
      },
      boxShadow: {
        "glow-teal": "0 0 20px rgba(0,212,170,0.15)",
        "glow-blue": "0 0 20px rgba(59,130,246,0.15)",
        "card": "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-up": "slideUp 0.3s ease-out",
        "fade-in": "fadeIn 0.4s ease-out",
      },
      keyframes: {
        slideUp: { "0%": { transform: "translateY(8px)", opacity: "0" }, "100%": { transform: "translateY(0)", opacity: "1" } },
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
      },
    },
  },
  plugins: [],
};
export default config;
