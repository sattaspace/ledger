# DealerCore Frontend

Vue 3 + Astro frontend for the DealerCore dealer management system.

## Local Development Setup

### Prerequisites
- Node.js 18+
- npm or yarn
- Running dealerbackend on port 8088

### Port Configuration

This project uses **port 4323** for local development to avoid conflicts with SattaBase frontend (port 4321).

```
SattaBase Frontend: http://localhost:4321
DealerCore Frontend: http://localhost:4323
SattaBase Backend: http://localhost:8086
DealerCore Backend: http://localhost:8088
```

### Installation

```bash
npm install
```

### Environment Variables

Create `.env` file:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8088/api
PUBLIC_API_BASE_URL=http://localhost:8088/api

# SattaBase Integration (for SSO)
PUBLIC_BASE_DOMAIN_URL=http://localhost:4321
PUBLIC_SERVICE_DOMAIN=dealer.sattaspace.com
```

### Development

```bash
npm run dev
# Server runs on http://localhost:4323
```

### Build

```bash
npm run build
npm start
# Server runs on http://localhost:4323
```

## Authentication

The frontend integrates with SattaBase for authentication:
- Login credentials are sent to dealerbackend
- dealerbackend proxies to SattaBase
- JWT access token stored in memory
- Refresh token in httpOnly cookie
- Auto-refresh every 5 minutes

## Project Structure

```
src/
  components/     # Vue components
  composables/    # Vue composables (useAuth, useFormatters)
  lib/            # Utility libraries (auth.ts)
  services/       # API service layer
  styles/         # Shared CSS utilities
  types.ts        # TypeScript types
```

## CORS Configuration

dealerbackend is configured to accept requests from:
- `http://localhost:4323`
- `http://127.0.0.1:4323`
