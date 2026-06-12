/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta principal — identidade jurídica premium
        sidebar: {
          DEFAULT: "#1a1a1a",
          hover: "#2a2a2a",
          active: "#f5f3ef",
        },
        juridico: {
          // Off-white quente — fundo principal
          bg: "#f5f3ef",
          // Bege/areia — cards secundários, fundos de input
          bege: "#ede8e0",
          // Dourado/oliva — acentos premium, bordas ativas, badges
          ouro: "#8B7355",
          "ouro-claro": "#c4a882",
          // Verde suave — crédito, sucesso
          verde: "#166534",
          "verde-bg": "#dcfce7",
          // Vermelho suave — despesa, alerta
          vermelho: "#991b1b",
          "vermelho-bg": "#fee2e2",
          // Laranja urgente — prazos curtos
          urgente: "#c2410c",
          "urgente-bg": "#ffedd5",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "0.75rem",
        "2xl": "1rem",
      },
    },
  },
  plugins: [],
};
