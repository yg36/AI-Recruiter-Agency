import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17202a",
        paper: "#f7f7f4",
        line: "#d9ded8",
        teal: "#0f766e",
        berry: "#9f1239",
        gold: "#b7791f"
      },
      boxShadow: {
        soft: "0 14px 40px rgba(23, 32, 42, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;

