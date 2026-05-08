// @ts-check
import { defineConfig } from "astro/config";

import vue from "@astrojs/vue";

import tailwindcss from "@tailwindcss/vite";

import node from "@astrojs/node";

import sitemap from "@astrojs/sitemap";

// https://astro.build/config
export default defineConfig({
  site: "https://www.my-site.dev",
  base: ".",
  trailingSlash: "never",
  output: "server",
  // security: {
  //   csp: {
  //     algorithm: "SHA-512", //added in astro 6
  //   },
  // },
  session: {
    // If set to a string, it will be used as the cookie name.
    cookie: "sattalegder-session-cookie",
  },
  integrations: [
    vue({
      appEntrypoint: "/src/pages/_app",
      jsx: {
        // treat any tag that starts with ion- as custom elements
        isCustomElement: (tag) => tag.startsWith("ldgr-"),
      },
    }),
    sitemap({
      entryLimit: 10000,
      changefreq: "weekly",
      priority: 0.7,
      lastmod: new Date(),
    }),
  ],

  vite: {
    plugins: [tailwindcss()],
  },

  adapter: node({
    mode: "standalone",
  }),
});
