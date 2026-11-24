# Atelier

Atelier is a fashion shop with a shopping agent at the center. Customers can browse, filter, and check out, or ask the stylist for a piece, an outfit, or a store policy. The agent searches the live catalog, so prices, sizes, and stock come from PostgreSQL rather than from the model’s memory. Administrators can manage the catalog and ask the agent to draft pages. A page stays a draft until an admin publishes it.

## Features

- Editorial storefront: home, shop, product, cart, wishlist, checkout, account, and policy pages.
- Customer style profile that can be edited, cleared, or turned off.
- Admin studio for products, inventory, orders, customers, pages, messages, and the stylist.
- Shopping agent with tool calling, Gemini or Ollama, and a local fallback when no model is configured.
- Retrieval over store policies and the catalog with pgvector, plus keyword search when vectors are unavailable.
- Stripe Checkout in test mode, or a labeled development mock when Stripe is not configured.
- JSON page drafts rendered by fixed React blocks. The model cannot emit HTML or code.

## Screenshots

The interface is the running shop at `http://localhost:5173`. The home page opens with the charcoal coat, collection tiles, and a stylist button. Product pages show sizes, stock, and pieces to wear with the item. The stylist sits in a panel at the lower right and returns product cards that link into the catalog. The studio at `/admin` shows sales, low stock, and page drafts.

## Architecture

```text
Browser (React, Vite, Tailwind)
        |  /api, /static, /uploads
        v
FastAPI
  auth, catalog, cart, checkout, admin
  shopping agent
    provider: Gemini or Ollama
    tools: products, style, orders, knowledge, page drafts
        |
        v
PostgreSQL + pgvector
  catalog, orders, conversations, knowledge chunks
```

Live price and inventory always come from SQL. The vector index is for policies and product descriptions. Retrieved text is treated as untrusted and cannot change the agent’s permissions.

## Stack

React, TypeScript, Vite, Tailwind CSS, shadcn-style components, React Router, TanStack Query, Zustand, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, pgvector, JWT, Stripe.

## Layout

```text
backend/          FastAPI app, Alembic, seed, tests
frontend/         React storefront and studio
docker-compose.yml
.env.example
```

## Run with Docker Compose

Docker Compose starts Postgres with pgvector, the API, and the Vite dev server.

```bash
cp .env.example .env
# Optional: put a Gemini key in .env. The shop runs without one.
docker compose up --build
```

- Shop: http://localhost:5173
- API docs: http://localhost:8000/docs

The API container runs migrations and the seed on startup. Compose points the API at the `db` service even if `.env` uses `127.0.0.1`.

## Run without Docker

You need PostgreSQL 16 with the `vector` extension, Python 3.12, and Node 22.

```bash
# Example local database
createuser fashion --pwprompt
createdb -O fashion fashion
psql -d fashion -c "CREATE EXTENSION IF NOT EXISTS vector;"

cp .env.example .env
# DATABASE_URL=postgresql+psycopg://fashion:fashion@127.0.0.1:5432/fashion

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload

# second terminal
cd frontend
npm install
npm run dev
```

## Demo accounts

Created by the seed. These are obvious local passwords, not real credentials.

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@atelier.test | AtelierAdmin!2026 |
| Customer | customer@atelier.test | AtelierCustomer!2026 |

Promo code `WELCOME10` takes 10% off merchandise. Shipping is $8, and orders of $150 or more ship free before the promo is applied.

## Gemini

1. Create a key in [Google AI Studio](https://aistudio.google.com/).
2. Set `GEMINI_API_KEY` in `.env` or in the API container environment.
3. Leave `GEMINI_MODEL=gemini-3.8-flash`, or set another model id. The name is read from configuration, not hardcoded through the agent.
4. For hosted embeddings, set `EMBEDDING_PROVIDER=gemini`. The default model is `gemini-embedding-001` at 768 dimensions.

Restart the API after changing keys. The key never goes to the browser.

If the key is empty, the API still starts. The stylist replies that Gemini is not configured.

## Ollama

```bash
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.2
# EMBEDDING_PROVIDER=ollama
```

Inside Compose, point `OLLAMA_BASE_URL` at the host, for example `http://host.docker.internal:11434`. The business logic does not change between providers.

## Stripe test mode

Leave the Stripe variables empty to use the mock checkout. The checkout page says that no card is charged, and the mock endpoint is rejected once `STRIPE_SECRET_KEY` is set.

For Stripe test mode:

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
PUBLIC_APP_URL=http://localhost:5173
```

Use the Stripe CLI to forward webhooks:

```bash
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

Pay with Stripe’s test card `4242 4242 4242 4242`. The order becomes paid only after the signed webhook is verified. The success page reads the order from the API.

Card numbers are never stored.

## Environment variables

See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `JWT_SECRET` | Signs access tokens. Change it before any shared deployment. |
| `DATABASE_URL` | SQLAlchemy URL. Compose overrides this to the `db` service. |
| `LLM_PROVIDER` | `gemini`, `ollama`, or `none`. |
| `GEMINI_API_KEY` | Server-only Gemini key. |
| `GEMINI_MODEL` | Defaults to `gemini-3.8-flash`. |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Local model. |
| `EMBEDDING_PROVIDER` | `local` (default), `gemini`, or `ollama`. |
| `GEMINI_EMBEDDING_MODEL` | Defaults to `gemini-embedding-001`. |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Test-mode payments. Empty means mock checkout. |
| `SHIPPING_FLAT`, `FREE_SHIPPING_OVER` | `8.00` and `150.00`. |
| `PUBLIC_APP_URL` | Used for Stripe return URLs. |

## Tests

```bash
cd backend && .venv/bin/pytest
cd frontend && npm test
```

Backend tests expect PostgreSQL with pgvector at `postgresql+psycopg://fashion:fashion@127.0.0.1:5432/fashion_test`. They create that schema themselves and do not use the demo database.

## Security

- Passwords are hashed with bcrypt. Refresh tokens are random and stored hashed.
- Admin routes and admin agent tools check the role on the server.
- Customer conversations are not offered admin tools, and the executor rejects them if a model asks anyway.
- Page publishing from the agent also requires the administrator’s own message to ask for publication.
- Page content is validated JSON. HTML and script are rejected.
- Uploads are limited to JPEG, PNG, and WebP and checked with Pillow.
- Retrieved documents and product text are marked untrusted in the prompt and cannot grant permissions.
- Do not commit `.env`. It is gitignored.

## Limitations

- Password reset does not send email. In development and test, the API returns the reset token so the flow can be finished. Production does not return it.
- The default embedding provider is a local hashing embedder so the index works offline. It is not a semantic model. Switch to Gemini or Ollama embeddings for real similarity.
- Vector size is fixed at 768. Changing `EMBEDDING_DIMENSIONS` requires a new migration.
- One currency (USD), no tax, and shipping only inside the United States.
- Product pictures are original SVG color studies, not photography.
- Rate limits are stored in process memory.
- Access tokens live in `localStorage`.
