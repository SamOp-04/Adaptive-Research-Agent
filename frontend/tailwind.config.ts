import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
      },
      colors: {
        app: {
          bg: "var(--app-bg)",
          elevated: "var(--app-bg-elevated)",
          panel: "var(--app-panel)",
          surface: "var(--app-surface)",
          border: "var(--app-border)",
        },
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 20px 50px -20px rgba(0,0,0,0.6)",
        floating: "0 10px 40px -12px rgba(0,0,0,0.55)",
      },
      keyframes: {
        "collapse-in": {
          "0%": { opacity: "0", maxHeight: "0px" },
          "100%": { opacity: "1", maxHeight: "600px" },
        },
      },
      animation: {
        "collapse-in": "collapse-in 0.3s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
