import eslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import vueParser from "vue-eslint-parser";
import vuePlugin from "eslint-plugin-vue";
import astroPlugin from "eslint-plugin-astro";

/**
 * ESLint flat config for the Ledger Frontend project.
 * Supports TypeScript, Vue 3, and Astro files.
 */
export default [
  // Global ignores
  {
    ignores: ["dist/**", ".astro/**", "node_modules/**", "*.d.ts"],
  },

  // TypeScript files
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    plugins: {
      "@typescript-eslint": eslint,
    },
    rules: {
      ...eslint.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports" },
      ],
    },
  },

  // Vue files
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
        extraFileExtensions: [".vue"],
      },
    },
    plugins: {
      vue: vuePlugin,
      "@typescript-eslint": eslint,
    },
    rules: {
      ...vuePlugin.configs["vue3-recommended"].rules,
      "vue/multi-word-component-names": "off",
      "vue/no-v-html": "error",
    },
  },

  // Astro files
  {
    files: ["**/*.astro"],
    languageOptions: {
      parser: astroPlugin.parser,
      parserOptions: {
        parser: tsParser,
        extraFileExtensions: [".astro"],
      },
    },
    plugins: {
      astro: astroPlugin,
    },
    rules: {
      ...astroPlugin.configs.recommended.rules,
    },
  },
];
