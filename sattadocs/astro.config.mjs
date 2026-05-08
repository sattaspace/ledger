// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import sitemap from '@astrojs/sitemap';

import tailwindcss from '@tailwindcss/vite';

import node from '@astrojs/node';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load environment variables from parent directory (sattabase root)
// where the main .env file lives alongside backend and frontend configs.
const env = loadEnv(
  process.env.NODE_ENV || 'development',
  path.resolve(__dirname, '../'),
  '',
);

// Pass backend URL as a server-side env var so middleware and API
// routes can reach the Sattabase Django Ninja API.
// In production, override via a real .env or container env.
process.env.SB_BACKEND_PUBLIC_API_URL =
  env.SB_BACKEND_PUBLIC_API_URL ||
  env.PUBLIC_API_BASE_URL ||
  process.env.SB_BACKEND_PUBLIC_API_URL ||
  'http://localhost:8000/api/v1';

// https://astro.build/config
export default defineConfig({
  site: 'https://docs.sattaspace.com',

  // Static output configuration
  output: "server",

  // Build configuration
  build: {
      // Clean output directory before build
      inlineStylesheets: 'auto',
  },

  integrations: [
      // Sitemap integration with SEO-friendly settings
      sitemap({
          changefreq: 'weekly',
          priority: 0.7,
          lastmod: new Date(),
          // Filter out 404 page from sitemap
          filter: (page) => !page.includes('/404') && !page.includes('/dev_docs'),
          // Add custom pages if needed
          customPages: [],
          // i18n support for future localization
          i18n: {
              defaultLocale: 'en',
              locales: {
                  en: 'en-US',
              },
          },
      }),

      starlight({
          title: 'SattaSpace Docs',
          description: 'Official documentation for SattaSpace Ecosystem - SattaBase and more',
          // Server-render all pages so that the middleware can intercept
          // /dev_docs/* requests for staff authentication.
          // Without this, Starlight prerenders pages as static HTML at build time,
          // bypassing the middleware entirely.
          prerender: false,
          // Edit link for contributions
          editLink: {
              baseUrl: 'https://github.com/sattaspace/sattadocs/edit/main/docs/',
          },

          // Last updated timestamp
          lastUpdated: true,

          // Favicon
          favicon: '/favicon.ico',

          // Custom CSS with Tailwind
          customCss: [
              './src/styles/global.css',
          ],

          // Social links
          social: [
              { icon: 'github', label: 'GitHub', href: 'https://github.com/sattaspace' },
          ],

          // Sidebar navigation
          sidebar: [
              {
                  label: 'Overview',
                  items: [
                      { label: 'Introduction', slug: 'introduction' },
                      { label: 'Getting Started', slug: 'getting-started' },
                  ],
              },
              {
                  label: 'SattaBase',
                  autogenerate: { directory: 'sattabase' },
              },
              {
                  label: 'Dev Docs',
                  autogenerate: { directory: 'dev_docs' },
              },
              // Future products will be added here:
              // {
              //     label: 'Product Name',
              //     autogenerate: { directory: 'product-name' },
              // },
          ],

          // Table of contents configuration
          tableOfContents: {
              minHeadingLevel: 2,
              maxHeadingLevel: 4,
          },

          // Pagination labels
          pagination: true,

          // Custom components for enhanced SEO
          components: {
              Head: './src/components/Head.astro',        
              TableOfContents: './src/components/TableOfContents.astro',
              MobileTableOfContents: './src/components/MobileTableOfContents.astro',
              LastUpdated: './src/components/LastUpdated.astro',  // Add this
          },

          // Banner for announcements (uncomment when needed)
          // banner: {
          //     content: '🎉 New feature released! Check out the latest updates.',
          //     dismissible: true,
          // },

          // Head elements for SEO and meta tags
          head: [
              // Primary Meta Tags
              { tag: 'meta', attrs: { name: 'author', content: 'SattaSpace' } },
              { tag: 'meta', attrs: { name: 'robots', content: 'index, follow' } },
              { tag: 'meta', attrs: { name: 'googlebot', content: 'index, follow, max-video-preview:-1, max-image-preview:large, max-snippet:-1' } },

              // Open Graph / Facebook
              { tag: 'meta', attrs: { property: 'og:type', content: 'website' } },
              { tag: 'meta', attrs: { property: 'og:site_name', content: 'SattaSpace Docs' } },
              { tag: 'meta', attrs: { property: 'og:locale', content: 'en_US' } },
              { tag: 'meta', attrs: { property: 'og:image', content: 'https://docs.sattaspace.com/logo.png' } },
              { tag: 'meta', attrs: { property: 'og:image:width', content: '1024' } },
              { tag: 'meta', attrs: { property: 'og:image:height', content: '1024' } },
              { tag: 'meta', attrs: { property: 'og:image:alt', content: 'SattaSpace Documentation' } },

              // Twitter
              { tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
              { tag: 'meta', attrs: { name: 'twitter:site', content: '@sattaspace' } },
              { tag: 'meta', attrs: { name: 'twitter:image', content: 'https://docs.sattaspace.com/logo.png' } },

              // Canonical URL (set per-page, but this is a fallback)
              { tag: 'link', attrs: { rel: 'canonical', href: 'https://docs.sattaspace.com/' } },

              // Additional SEO
              { tag: 'meta', attrs: { name: 'theme-color', content: '#6366f1' } },
              { tag: 'meta', attrs: { name: 'msapplication-TileColor', content: '#6366f1' } },

              // RSS Feed (for future use)
              // { tag: 'link', attrs: { rel: 'alternate', type: 'application/rss+xml', title: 'SattaSpace Docs RSS Feed', href: '/rss.xml' } },
          ],
      }),
  ],

  // Vite configuration
  vite: {
      plugins: [tailwindcss()],
      build: {
          // Optimize chunk size
          cssMinify: true,
          minify: 'esbuild',
      },
    //   server: {
    //         fs: {
    //             // Allow serving files from one level up from the project root
    //             allow: ['../../../'] 
    //         }
    //     }
  },

  // Image optimization
  image: {
      // Service for image optimization
      service: {
          entrypoint: 'astro/assets/services/sharp',
      },
  },

  // Prefetch configuration for faster navigation
  prefetch: {
      prefetchAll: true,
      defaultStrategy: 'viewport',
  },

  // Redirects (if needed in future)
  // redirects: {
  //     '/old-path': '/new-path',
  // },

  // Trailing slash configuration (consistent URLs)
  trailingSlash: 'never',

  // i18n configuration for future localization
  i18n: {
      defaultLocale: 'en',
      locales: ['en'],
      routing: {
          prefixDefaultLocale: false,
      },
  },

  adapter: node({
    mode: 'standalone',
    staticHeaders: true,
  }),
});