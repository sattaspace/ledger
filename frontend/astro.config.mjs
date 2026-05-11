// @ts-check
import process from "node:process";
import { defineConfig } from "astro/config";
import vue from "@astrojs/vue";
import tailwindcss from "@tailwindcss/vite";
import node from "@astrojs/node";
import { loadEnv } from "vite"; // Add this
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 1. Determine mode manually
const mode = process.env.NODE_ENV || "development";

// 2. Load env variables
const env = loadEnv(mode, path.resolve(__dirname, "../"), "");

// https://astro.build/config
export default defineConfig({
  output: "server",
  // Use manually loaded env for the site property
  site:
    mode === "development" ? "http://localhost:4321" : env.PUBLIC_SITE_URL_SB,
  trailingSlash: "never",

  adapter: node({
    mode: "standalone",
  }),

  integrations: [vue()],

  vite: {
    envDir: path.resolve(__dirname, "../"),
    plugins: [tailwindcss()],
    ssr: {
      external: ["vue"],
    },
    // Useful for debugging env issues in the terminal
    define: {
      "process.env.APP_VERSION": JSON.stringify(
        process.env.npm_package_version,
      ),
    },
  },

  server: {
    host: "0.0.0.0",
    port: 4321,
  },
});
