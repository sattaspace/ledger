// @ts-check
import { defineConfig } from "astro/config";
import vue from "@astrojs/vue";
import tailwindcss from "@tailwindcss/vite";
import node from "@astrojs/node";
import sitemap from "@astrojs/sitemap";

// https://astro.build/config
export default defineConfig({
  site: "https://sattaspace.com",
  base: "/",
  trailingSlash: "never",
  output: "server",

  // ── Security Configuration ───────────────────────────────────────────
  security: {
    // CSRF protection — validates Origin header on mutating requests
    checkOrigin: true,

    // Host header injection prevention
    // TODO: Update with your actual production domains
    allowedDomains: [
      { hostname: "sattaspace.com", protocol: "https" },
      { hostname: "**.sattaspace.com", protocol: "https" },
    ],

    // Content Security Policy (stable since Astro 6)
    //
    // In PRODUCTION (`astro build` + `astro preview`): Astro auto-generates
    // SHA hashes for all inline scripts/styles from Vue islands and Astro
    // components. The directives below enforce strict CSP with those hashes.
    //
    // In DEVELOPMENT (`astro dev`): CSP is disabled because Vite HMR and
    // Astro's dev toolbar inject dynamic inline styles/scripts that cannot
    // be hashed at build time.
    //   → Test production CSP with:  npm run build && npm run preview
    //
    // NOTE: process.env.NODE_ENV is used here (available at config time),
    // not import.meta.env (only available at runtime inside components).
    csp:
      process.env.NODE_ENV === "production"
        ? {
            algorithm: "SHA-512",
            directives: [
              "default-src 'self'",
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "connect-src 'self'",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ],
            styleDirective: {
              resources: ["'self'"],
            },
            scriptDirective: {
              resources: ["'self'"],
              strictDynamic: false,
            },
          }
        : false,
  },

  // ── Session Configuration ────────────────────────────────────────────
  session: {
    cookie: {
      name: "satta-ledger-session",
      sameSite: "lax",
      secure: true,
      path: "/",
    },
    ttl: 3600, // 1 hour
  },

  // ── Image Optimization (Astro built-in Sharp) ───────────────────────
  image: {
    service: {
      entrypoint: "astro/assets/services/sharp",
      config: {
        limitInputPixels: 50_000_000, // 50MP max
      },
    },
    domains: [],
    remotePatterns: [],
    responsiveStyles: true,
    layout: "constrained",
    breakpoints: [640, 750, 828, 1080, 1280, 1668, 2048],
  },

  // ── Markdown / Syntax Highlighting ───────────────────────────────────
  // Shiki uses inline styles which conflict with CSP.
  // Disabled for now — enable Prism later if code blocks are needed.
  markdown: {
    syntaxHighlight: false,
  },

  // ── Integrations ────────────────────────────────────────────────────
  integrations: [
    vue({
      appEntrypoint: "/src/pages/_app",
      jsx: {
        isCustomElement: (tag) => tag.startsWith("ldgr-"),
      },
      // NOTE: Vue DevTools disabled — vite-plugin-inspect (pulled in by
      // vite-plugin-vue-devtools@8.x) is incompatible with Vite 7 and
      // causes "Cannot read properties of undefined (reading 'get')" errors.
      // Re-enable once vite-plugin-inspect releases a Vite 7-compatible update.
      devtools: false,
    }),
    sitemap({
      entryLimit: 10000,
      changefreq: "weekly",
      priority: 0.7,
      lastmod: new Date(),
    }),
  ],

  // ── Vite Configuration ──────────────────────────────────────────────
  vite: {
    plugins: [tailwindcss()],
    build: {
      cssMinify: true,
      minify: true,
    },
  },

  // ── Node Adapter (Server Mode) ──────────────────────────────────────
  adapter: node({
    mode: "standalone",
    // Serve CSP headers via Response object (not just <meta> tags)
    staticHeaders: true,
    // Limit request body to 10MB
    bodySizeLimit: 10 * 1024 * 1024,
  }),
});
