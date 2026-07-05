# Supabase CLI Setup

This repo uses the local `supabase` CLI package instead of requiring a global
install.

## Installed Workflow

- CLI package: `supabase` in `devDependencies`
- project config: [config.toml](/Users/tuliomonteirodasilva/projects/controlgastos-web/supabase/config.toml)
- migrations: [migrations](/Users/tuliomonteirodasilva/projects/controlgastos-web/supabase/migrations)
- seed file: [seed.sql](/Users/tuliomonteirodasilva/projects/controlgastos-web/supabase/seed.sql)
- generated types target: [database.types.ts](/Users/tuliomonteirodasilva/projects/controlgastos-web/src/lib/database.types.ts)

## Remote Project

Current hosted project ref inferred from `.env.local`:

- `ghckqkkfpyzvcehmdtsq`

Link once:

```bash
npm run supabase:login
npm run supabase:link -- --project-ref ghckqkkfpyzvcehmdtsq
```

Then push migrations and generate remote types:

```bash
npm run db:push
npm run types:remote
```

## Local Project

Requires Docker-compatible tooling:

```bash
npm run supabase:start
npm run db:reset
npm run types:local
```

## Notes

- `supabase init` has already been run for this repo.
- Shared categories are seeded in the initial migration, not in `seed.sql`.
- Accounts are intentionally not seeded because they are user-specific.
