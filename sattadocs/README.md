# SattaSpace Documentation

[![Built with Starlight](https://astro.badg.es/v2/built-with-starlight/tiny.svg)](https://starlight.astro.build)

Official documentation for the SattaSpace Ecosystem, built with [Astro](https://astro.build) and [Starlight](https://starlight.astro.build).

## 🚀 Project Overview

This repository contains the documentation site for SattaSpace products and services. Currently featuring:

- **SattaBase** — Authentication and billing hub for the SattaSpace ecosystem

More products will be added as the ecosystem expands.

## 🧞 Tech Stack

- **Framework**: [Astro 6](https://astro.build)
- **Documentation**: [Starlight](https://starlight.astro.build)
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com)
- **Language**: TypeScript

## 📁 Project Structure

```
.
├── public/
│   ├── favicon.svg       # Site favicon
│   ├── logo.png          # SattaSpace logo
│   └── _headers          # Cloudflare headers config
├── src/
│   ├── assets/           # Static assets for content
│   ├── content/
│   │   └── docs/         # Documentation pages
│   │       ├── index.mdx           # Landing page
│   │       ├── introduction.md     # Introduction
│   │       ├── getting-started.md  # Getting started guide
│   │       └── sattabase/          # SattaBase documentation
│   ├── styles/
│   │   └── global.css    # Global styles and theme
│   └── content.config.ts # Content collection config
├── astro.config.mjs      # Astro configuration
├── package.json
└── tsconfig.json
```

## 🛠️ Commands

All commands are run from the root of the project, from a terminal:

| Command                   | Action                                           |
| :------------------------ | :----------------------------------------------- |
| `npm install`             | Installs dependencies                            |
| `npm run dev`             | Starts local dev server at `localhost:4321`      |
| `npm run build`           | Build your production site to `./dist/`          |
| `npm run preview`         | Preview your build locally, before deploying     |
| `npm run check`           | Run TypeScript and Astro type checking           |

## 📝 Adding Documentation

1. Create a new `.md` or `.mdx` file in `src/content/docs/`
2. Add frontmatter with `title` and `description`
3. The file will be automatically routed based on its path

### Example

```markdown
---
title: My New Page
description: A description of the page
---

# My New Page

Content goes here...
```

### Sidebar Configuration

Update `astro.config.mjs` to add navigation items:

```javascript
sidebar: [
    {
        label: 'New Section',
        autogenerate: { directory: 'new-section' },
    },
]
```

## 🎨 Customization

### Theme Colors

Edit `src/styles/global.css` to customize the color scheme. The default uses a deep purple to indigo gradient.

### Logo and Favicon

- Replace `public/logo.png` for the main logo
- Replace `public/favicon.svg` for the favicon

## 🌐 Deployment

The site is configured for deployment at `https://docs.sattaspace.com`. The `_headers` file contains caching directives for Cloudflare Pages.

### Build for Production

```bash
npm run build
```

The output will be in `./dist/`.

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Make your changes
4. Commit your changes (`git commit -am 'Add new documentation'`)
5. Push to the branch (`git push origin feature/improvement`)
6. Create a Pull Request

## 📄 License

© 2024 SattaSpace. All rights reserved.

## 🔗 Links

- **Live Site**: [docs.sattaspace.com](https://docs.sattaspace.com)
- **SattaBase**: [sattabase.sattaspace.com](https://sattabase.sattaspace.com)
- **GitHub**: [github.com/sattaspace](https://github.com/sattaspace)
