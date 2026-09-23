## Qué cambia y por qué

<!-- Una o dos frases. Si corrige un bug, describe el escenario real que
fallaba, no solo "arregla X". -->

## Cómo se verificó

<!-- ¿Qué corriste, contra qué? "pytest local" no es suficiente si el cambio
toca algo que solo se ejercita con Postgres real -- dilo explícitamente. -->

- [ ] `ruff check .` / `mypy app` (backend) o `eslint .` / `tsc -b` (frontend)
- [ ] `pytest --cov=app` (backend) -- ¿cambia la cobertura medida?
- [ ] Probado contra Postgres real, no solo con los tests que se saltan sin él
- [ ] E2E (`npx playwright test`) si tocaste una de las 6 pantallas

## ¿Toca algo sensible?

- [ ] Seguridad (auth, RLS, secretos, rate limiting)
- [ ] Capa de IA / BYOK (`app/adaptadores/llm/`)
- [ ] Migraciones (`backend/alembic/`) -- ¿tiene `downgrade()` real?
- [ ] Infraestructura de despliegue (`docker-compose*.yml`, `.github/workflows/`)

Si marcaste alguna, etiqueta a quien corresponda según `CODEOWNERS`.

## Checklist de licencias

- [ ] Ninguna dependencia nueva, o si la hay: licencia verificada (MIT/BSD/Apache)
      y documentada en `requirements.txt`/`package.json` (ver `CONTRIBUTING.md`).
