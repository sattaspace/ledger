# Port Configuration - DEALERCORE v3.0

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BASE PROJECT (SattaBase)                       │
│  ┌──────────────────────────────┐      ┌──────────────────────────────┐    │
│  │   Base Frontend              │      │   Base Backend               │    │
│  │   (SattaBase UI)             │◄────►│   (Auth & Billing)           │    │
│  │   Port: 4321                 │      │   Port: 8086                 │    │
│  └──────────────┬───────────────┘      └──────────┬───────────────────┘    │
└─────────────────┼──────────────────────────────────┼────────────────────────┘
                  │                                  │
                  │ SSO / Auth                       │ API Key Auth
                  │                                  │
                  ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEALER PROJECT (DealerCore)                    │
│  ┌──────────────────────────────┐      ┌──────────────────────────────┐    │
│  │   DealerFrontend             │      │   DealerBackend              │    │
│  │   (Dealer UI)                │◄────►│   (Dealer API)               │    │
│  │   Port: 4323                 │      │   Port: 8088                 │    │
│  └──────────────────────────────┘      │                              │    │
│                                        │  • Proxies to SattaBase      │    │
│                                        │  • Handles dealer logic      │    │
│                                        │  • Serves dealerfrontend     │    │
│                                        └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Port Mapping Summary

| Service | Port | Purpose | Default URL |
|---------|------|---------|-------------|
| **Base Backend** | 8086 | SattaBase auth & subscription API | `http://localhost:8086/api/v1` |
| **Base Frontend** | 4321 | SattaBase user interface | `http://localhost:4321` |
| **DealerBackend** | 8088 | Dealer API (sister service) | `http://localhost:8088/api/v1` |
| **DealerFrontend** | 4323 | Dealer UI (sister service) | `http://localhost:4323` |

---

## Configuration Files

### DealerBackend Environment Variables (.env)

```env
# ─── SattaBase Integration ─────────────────────────────────────────────────
# Base backend URL (provides authentication & subscription)
SB_API_BASE_URL=http://localhost:8086/api/v1
SB_SERVICE_DOMAIN=dealer.sattaspace.com
SB_API_KEY=sb_live_xxxxxxxxxxxx

# ─── CORS Configuration ─────────────────────────────────────────────────────
# Must include dealerfrontend and base frontend URLs
SL_CORS_ALLOWED_ORIGINS=http://localhost:4323,http://127.0.0.1:4323,http://localhost:4321

# ─── Database ───────────────────────────────────────────────────────────────
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dealercore
DB_USER=postgres
DB_PASSWORD=your_password
```

### DealerFrontend Environment Variables (.env)

```env
# ─── API Configuration ──────────────────────────────────────────────────────
# Points to dealerbackend (sister backend)
VITE_API_BASE_URL=http://localhost:8088/api
PUBLIC_API_BASE_URL=http://localhost:8088/api/v1

# ─── SattaBase Integration ──────────────────────────────────────────────────
# Points to base frontend (for SSO)
PUBLIC_BASE_DOMAIN_URL=http://localhost:4321
PUBLIC_SERVICE_DOMAIN=dealer.sattaspace.com
```

---

## Communication Flows

### 1. Authentication Flow

```
[User] ──► [DealerFrontend:4323] ──► [DealerBackend:8088] ──► [BaseBackend:8086]
Login         Login Form              Proxy Request              Authenticate
```

### 2. SSO Flow (Manage Billing)

```
[User] ──► [DealerFrontend:4323] ──► [DealerBackend:8088] ──► [BaseBackend:8086]
              Click Billing              Get Auth Code
                                              │
                                              ▼
[User] ◄─────────────────────────────────── [BaseFrontend:4321]
     Redirect to SattaBase                      Auth Callback
```

### 3. API Flow (Normal Operations)

```
[DealerFrontend:4323] ──► [DealerBackend:8088]
      API Request                Local Processing
          JWT                          │
          ▼                          ╱╲
                              [Database]
```

---

## Ready to Use Configuration

### Start Base Project (if not running)
```bash
# Base Backend
cd backend
uvicorn base.asgi:application --port 8086 --reload

# Base Frontend
cd frontend
npm run dev  # Runs on port 4321
```

### Start Dealer Project
```bash
# DealerBackend
cd dealerbackend
uvicorn dealercore.asgi:application --port 8088 --reload

# DealerFrontend
cd dealerfrontend
npm run dev  # Runs on port 4323 (configured in astro.config.mjs)
```

---

## Verification Checklist

- [ ] Base Backend running on port 8086
- [ ] Base Frontend running on port 4321
- [ ] DealerBackend running on port 8088
- [ ] DealerFrontend running on port 4323
- [ ] DealerBackend can reach Base Backend:8086
- [ ] DealerFrontend can reach DealerBackend:8088
- [ ] CORS configured to allow 4323 and 4321

---

**Last Updated**: June 10, 2026  
**Status**: Production Ready ✅
