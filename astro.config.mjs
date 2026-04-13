import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";
import preact from "@astrojs/preact";

export default defineConfig({
  site: "https://newslancashire.co.uk",
  vite: {
    plugins: [tailwindcss()],
  },
  integrations: [preact({ include: ["**/islands/*"] })],
});
