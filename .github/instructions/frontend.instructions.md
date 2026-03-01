---
applyTo: "frontend/src/**/*.ts,frontend/src/**/*.tsx"
---

# Frontend — Path-Specific Instructions

## Structure

- `frontend/src/main.tsx` — App entry point
- `frontend/src/App.tsx` — Root component with router setup
- `frontend/src/pages/` — Page-level components (one per route)
- `frontend/src/components/` — Shared UI components
- `frontend/src/hooks/` — Custom React hooks
- `frontend/src/stores/` — Zustand state stores
- `frontend/src/api/` — API client functions (typed, fetch-based)
- `frontend/src/actions/` — Form/mutation actions
- `frontend/src/config/` — App configuration constants
- `frontend/src/i18n.ts` — i18next configuration (EN + PT-BR)

## Rules

- TypeScript strict mode; all props, parameters, and return values must be typed
- React 19 with functional components and hooks only; no class components
- ESLint with `eslint-plugin-react-hooks` — ensure all hook dependencies are correct; warnings are OK, errors fail CI
- State management via Zustand (`stores/`); no Redux
- Routing via `react-router` v7
- Graph visualization via `react-force-graph-2d`
- i18n: all user-visible strings must use `useTranslation()` hook — no hardcoded English strings
- `VITE_PUBLIC_MODE` and `VITE_PATTERNS_ENABLED` env vars gate features in the UI (mirror server-side flags)
- Do not add personal data fields to any public-facing component or demo data

## Build & Test

- `npm ci` always before building or testing (do not use `npm install`)
- Build: `npm run build` (runs `tsc -b && vite build`)
- Tests: `npm test -- --run` (Vitest, ~154 tests, ~5s)
- Lint: `npx eslint src/` (0 errors required; warnings allowed)
- Type check: `npx tsc --noEmit`
- Dev server: `npm run dev` (proxies API at `VITE_API_URL`, default `http://localhost:8000`)
