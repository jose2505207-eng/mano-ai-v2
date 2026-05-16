import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        mano: {
          primary: "#6366f1",
          secondary: "#8b5cf6",
          accent: "#f59e0b",
          dark: "#0f172a",
          darker: "#020617",
          surface: "#1e293b",
          border: "#334155",
          text: "#f8fafc",
          muted: "#94a3b8",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
