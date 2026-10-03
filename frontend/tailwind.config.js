/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#26142F",       // aubergine
        pearl: "#F4F1F5",     // page background
        lagoon: "#1F7A78",    // primary action
        blush: "#F3D9D2",     // soft surfaces
        graphite: "#5B5063",  // secondary text
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "ui-sans-serif", "system-ui", "sans-serif"],
        body: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
