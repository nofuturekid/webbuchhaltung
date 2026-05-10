# Frontend Context

You are working in the frontend of WebBuchhaltung (German accounting software).

## Stack
- React 18 — functional components only, no class components
- TypeScript 5 — strict mode, no `any`, explicit return types on all functions
- Vite — build tool, use `import.meta.env` for env vars
- React Query (TanStack Query) — for all server state, no manual fetch in components
- Zustand or React Context — for local UI state only
- React Hook Form + Zod — for all forms with validation

## Project Layout (to be created)
```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/      # Shared reusable components
│   │   └── ui/          # Base UI primitives (Button, Input, Table, etc.)
│   ├── features/        # Feature modules (invoices/, accounts/, etc.)
│   │   └── invoices/
│   │       ├── components/
│   │       ├── hooks/
│   │       └── api.ts   # React Query hooks for this feature
│   ├── lib/
│   │   ├── api.ts       # Axios instance with base URL + auth headers
│   │   └── formatters.ts  # German number/date formatters
│   └── types/           # Shared TypeScript types (auto-generated from OpenAPI)
├── tests/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

## Coding Standards
- All code, comments, and type definitions in English
- UI-facing text in German (the target user is German-speaking)
- Components in PascalCase files; hooks in camelCase files starting with `use`
- No inline styles — use CSS modules or Tailwind
- Every component exports its props type: `export type InvoiceCardProps = {...}`

## German Localization (non-negotiable)
```typescript
// Amounts — always format as German locale
const formatAmount = (value: number): string =>
  new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(value);
// Result: "1.234,56 €"

// Dates — DD.MM.YYYY
const formatDate = (date: Date): string =>
  new Intl.DateTimeFormat('de-DE').format(date);
// Result: "08.05.2026"
```

## API Types
TypeScript types for API responses are auto-generated from the OpenAPI schema:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts
```
Never manually write types that should be auto-generated. Run this after any backend change.

## Accounting UI Patterns
- Amounts: always right-aligned in tables, monospace font, 2 decimal places
- Account numbers (SKR03/04): always 4 digits, left-padded with zeros, e.g., "0800"
- Document numbers: fixed-width display, sortable columns
- Debit/Credit columns side-by-side (T-account style for journal view)
