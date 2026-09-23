/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          950: "#060913",
          900: "#0B1120",
          850: "#0F172A",
          800: "#1E293B",
          700: "#334155",
          600: "#475569",
        },
        risk: {
          critical: "#EF4444",
          high: "#F97316",
          medium: "#FBBF24",
          low: "#10B981",
        },
        accent: {
          indigo: "#6366F1",
          cyan: "#06B6D4",
          purple: "#A855F7",
        },
      },
      boxShadow: {
        "glow-indigo": "0 0 20px -5px rgba(99, 102, 241, 0.4)",
        "glow-cyan": "0 0 20px -5px rgba(6, 182, 212, 0.4)",
        "glow-risk-critical": "0 0 25px -5px rgba(239, 68, 68, 0.5)",
        "glow-risk-high": "0 0 25px -5px rgba(249, 115, 22, 0.5)",
        "glow-risk-low": "0 0 25px -5px rgba(16, 185, 129, 0.5)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
