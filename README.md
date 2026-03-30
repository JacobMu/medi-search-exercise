# medi-search-exercise

An ad creative compositor that replaces green-screen phone displays with app screenshots.

---

## Tech Stack

### Backend (`be/`)

| | |
|---|---|
| **Language** | Python ≥ 3.14 |
| **Framework** | FastAPI 0.135+ |
| **ASGI server** | Uvicorn |
| **Package manager** | `uv` |
| **Port** | `8000` |

**Key libraries:**

| Library | Purpose |
|---|---|
| `opencv-python-headless`, `numpy`, `pillow` | Image processing / green-screen compositing |
| `pydantic` | Data validation and settings |
| `python-multipart` | File upload support |
| `python-dotenv` | `.env` loading |

**Code quality:** `ruff` (line length 100, includes `flake8-bandit` security rules)  
**Tests:** `pytest` with `asyncio_mode = auto`; HTTP client via `httpx`

**Routers:** `overlay`, `save`, `stats`  
**Static files:** `/output` served from the `./output/` directory

---

### Frontend (`fe/`)

| | |
|---|---|
| **Framework** | Next.js 15 (App Router) |
| **Runtime** | Node 22 |
| **Language** | TypeScript 5 |
| **Styling** | Tailwind CSS 3 + PostCSS |
| **Linter / Formatter** | Biome 1.9.4 |
| **Test runner** | Jest 29 + Testing Library |
| **Port** | `3000` |

**Key dependencies:** React 19

The frontend proxies all `/api/*` and `/output/*` requests to the backend via Next.js rewrites, controlled by the `BACKEND_URL` environment variable.

---

## Project Structure

```
be/           # FastAPI backend
  src/
    models/   # Pydantic models
    overlay/  # Image overlay processing
    routers/  # API route handlers (overlay, save, stats)
    services/ # Business logic (compositor, analytics)
    store/    # In-memory job store
  tests/      # pytest test suite
fe/           # Next.js frontend
  src/
    app/      # Next.js App Router pages
    composer/ # Composer UI components and hooks
    admin/    # Admin dashboard components
    lib/      # API client and shared types
```

---

## Starting the Application

### With Docker Compose (recommended)

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

To stop:

```bash
docker-compose down
```

---

### Without Docker

**Backend:**

```bash
cd be
uv sync                                                        # install dependencies
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload   # start dev server
```

**Frontend** (in a separate terminal):

```bash
cd fe
npm install
BACKEND_URL=http://localhost:8000 npm run dev
```

---

## Environment Variables

| Variable | Used by | Default | Purpose |
|---|---|---|---|
| `BACKEND_URL` | Frontend (build + runtime) | `http://localhost:8000` | Proxy target for `/api/*` and `/output/*` rewrites |

When running with Docker Compose, `BACKEND_URL` is automatically set to `http://be:8000` (the internal Docker network address).

---

## Running Tests

**Backend:**

```bash
cd be
uv run pytest
```

**Frontend:**

```bash
cd fe
npm test
```
