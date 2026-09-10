# Contribuir a DiagMuni

Gracias por tu interés en contribuir. Este documento cubre lo mínimo para que
tu primer PR pase el CI a la primera.

## Idioma

Código, comentarios, mensajes de commit y documentación están en **español**
— es la convención ya establecida en todo el repo, mantenla en tus cambios.

## Poner el proyecto a correr

```
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
```

Guía completa, con verificación de que quedó arriba y solución a errores
comunes, en `docs/runbook-despliegue.md`.

## Antes de abrir un PR

El CI corre esto mismo en cada PR (`.github/workflows/ci.yml`) — córrelo
localmente primero, te ahorra una vuelta:

**Backend** (`cd backend`):
```
pip install -r requirements-dev.txt
ruff check .
mypy app
pytest --cov=app --cov-report=term-missing   # umbral mínimo: 70% (pyproject.toml)
```

**Frontend** (`cd frontend`):
```
npm install
npx eslint .
npx tsc -b
```

**E2E** (stack Docker completo, más lento — el job `e2e` de CI lo corre
siempre, pero si tocaste una de las 6 pantallas vale la pena correrlo local):
```
docker compose up -d --build
docker compose exec backend alembic upgrade head
cd frontend && npx playwright test
```

## Arquitectura

Backend hexagonal — antes de agregar código nuevo, ubica en qué capa entra:

- `app/dominio/` — reglas normativas y motor de madurez, código puro, sin IA
  ni base de datos. Principio rector del proyecto: **motor determinista
  primero, IA después** — el LLM nunca decide el diagnóstico, solo redacta
  bajo verificación.
- `app/aplicacion/` — casos de uso, orquesta dominio + adaptadores.
- `app/adaptadores/http/` — routers de FastAPI, solo traducen HTTP a casos de
  uso, sin lógica de negocio.
- `app/adaptadores/llm/` — todo lo que llama a un LLM (LiteLLM), incluye BYOK
  por tenant.
- `app/models/` / `app/schemas/` — SQLAlchemy / Pydantic.

Frontend: React + TypeScript estricto, TanStack Query para data fetching
(nunca un cliente HTTP nuevo), shadcn/ui copiado al repo (ver `NOTICE`).

## Estilo de commits

Mensajes descriptivos en español, uno por cambio lógico — revisa `git log`
para el tono esperado. No hay un formato tipo Conventional Commits impuesto
todavía.

## Licencias de dependencias

Toda dependencia nueva necesita licencia compatible (MIT, BSD, Apache) —
GPL solo como servicio independiente sin linking de código, AGPL nunca como
dependencia integrada (ver "Licencia" en `README.md`). El CI bloquea
GPL/AGPL automáticamente (`pip-licenses` / `license-checker-rseidelsohn`),
pero repasa la licencia antes de proponerla si no es MIT/BSD/Apache — deja un
comentario en `requirements.txt`/`package.json` documentando la verificación,
mismo patrón que ya usan `litellm`, `psycopg`, `fpdf2`, `cryptography` ahí.

## Seguridad

Nunca abras un issue público para una vulnerabilidad — ver `SECURITY.md`.

## Código de conducta

Este proyecto sigue el `CODE_OF_CONDUCT.md` — lo esperado es simple: trata a
los demás con respeto.
