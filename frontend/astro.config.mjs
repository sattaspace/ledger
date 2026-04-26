// @ts-check
import process from "node:process";
import { defineConfig } from "astro/config";
import vue from "@astrojs/vue";
import tailwindcss from "@tailwindcss/vite";
import node from "@astrojs/node";

// https://astro.build/config
export default defineConfig({
  output: "server",

  adapter: node({
    mode: "standalone",
  }),

  integrations: [
    vue(),
  ],

  vite: {
    plugins: [tailwindcss()],
    ssr: {
      external: ["vue"],
    },
  },

  server: {
    host: "0.0.0.0",
    port: 4321,
  },

  site: process.env.SITE_URL || "http://localhost:4321",
});
