# Sakshi dashboard

## Local development

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. Vite proxies `/v1/*` and `/healthz` to the lender API at `http://localhost:8000`.

- `/` — lender operations dashboard (live API data only)
- `/borrower` — borrower application UI preview; live submission stays disabled until a secure backend/LSP application contract exists
- `/receipt/:id` — receipt based on `GET /v1/decisions/{id}/status`
- `/ledger` — read-only view of the documented lender ledger endpoint
- `/demo` — isolated browser-only scenarios; it does not post proofs, alter API state, write ledger entries, or call disbursal endpoints

## Production build

```bash
npm run build
```

The compiled SPA is written to `dist/`. The Dev 3 integration `node/Dockerfile` copies it into `dashboard/dist` in the lender container. Dev 2's FastAPI app must mount that directory with `StaticFiles` and serve the SPA for non-API routes.

## UI safety note

Demo outcomes are fixtures, not cryptographic verification. The live dashboard and receipt only display backend-returned state. The borrower form does not call the documented `/v1/demo/apply` shortcut because that endpoint directly creates a simulated `VERIFIED` record.
