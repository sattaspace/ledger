import { defineConfig } from "astro/config";
import { fileURLToPath } from "node:url";
import vue from "@astrojs/vue";
import node from "@astrojs/node";
import tailwindcss from "@tailwindcss/vite";

// https://astro.build/config
export default defineConfig({
  output: "server",
  adapter: node({
    mode: "standalone",
  }),
  integrations: [vue()],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
  },
  server: {
    port: 4323,
    host: "0.0.0.0",
  },
});
