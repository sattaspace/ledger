import { defineConfig } from "astro/config";
import vue from "@astrojs/vue";
import tailwindcss from "@tailwindcss/vite";

// https://astro.build/config
export default defineConfig({
  output: "static",
  integrations: [vue()],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: {
        "@": "/src",
        "firebase/app": "/src/firebase-mock.ts",
        "firebase/auth": "/src/firebase-mock.ts",
        "firebase/firestore": "/src/firebase-mock.ts",
      },
    },
  },
  // server: {
  //   port: process.env.ASTRO_PORT ? parseInt(process.env.ASTRO_PORT) : 3000,
  //   host: '0.0.0.0'
  // }
});
