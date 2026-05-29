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
        navy: { DEFAULT: "#1a2e4a", light: "#2a3f60" },
        teal: { DEFAULT: "#0d7377", light: "#14a085" },
        brand: {
          50: "#e8f4f8",
          100: "#c5e4ef",
          500: "#0d7377",
          600: "#0a5f63",
          900: "#1a2e4a",
        },
      },
    },
  },
  plugins: [],
};
export default config;
