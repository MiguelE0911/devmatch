/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./apps/**/*.py",
  ],
  theme: {
    extend: {
      fontFamily: {
        /* Montserrat: tipografía estándar de DevMatch (scoped: solo se aplica
           donde se cargue la fuente, p. ej. la landing). */
        montserrat: ["Montserrat", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        /* Escala violeta de marca (#6D28D9 primario, #A78CFA secundario) */
        "violet-track": "#A380D9",
        "violet-fill-start": "#C6B2E7",
        "violet-fill-end": "#F4F8FA",
        "violet-ray": "#7C4FE0",
        "violet-deep": "#5B21C7",
        /* Claro y tinta de la paleta declarada */
        paper: "#F5F9FA",
        ink: "#3A455B",
        /* Shell interno (app, no landing) — ver DEVMATCH-DESIGN sección de detalle de proyecto */
        "app-navbar": "#333074",   /* navbar superior interna */
        "app-search": "#5B56A5",   /* fondo del buscador interno */
        "app-disabled": "#C4A7EF", /* botones "Postularme" deshabilitados */
        "placeholder-gray": "#E3E3E3", /* celdas vacías de la Galería */
      },
      boxShadow: {
        "hero": "0 40px 80px -20px rgba(91, 33, 198, 0.55)",
        "navbar": "0 18px 50px -20px rgba(91, 33, 198, 0.5)",
        "card": "0 18px 45px -18px rgba(109, 40, 217, 0.35)",
        "card-violet": "0 35px 70px -22px rgba(32, 10, 70, 0.65)",
      },
    },
  },
  plugins: [],
};