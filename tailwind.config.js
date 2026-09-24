/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.html",
    "./apps/**/*.py",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // Texto de apoio: o gray-500 padrão (#6b7280) não chega a 4,5:1
        // sobre o papel quente e a areia; este tom chega nos dois.
        gray: {
          500: "#5f6773",
        },
        // Paleta principal — identidade jurídica premium
        // Cores do escritório (white label): variáveis definidas em
        // templates/base/base.html a partir de ConfiguracaoVisual.
        primaria: {
          DEFAULT: "rgb(var(--cor-primaria-rgb, 26 26 26) / <alpha-value>)",
          hover: "rgb(var(--cor-primaria-hover-rgb, 42 42 42) / <alpha-value>)",
        },
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
          ouro: "rgb(var(--cor-secundaria-rgb, 139 115 85) / <alpha-value>)",
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
