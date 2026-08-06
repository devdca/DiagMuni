# Plan de implementación — DiagMuni

Versión 1 · 21 de julio de 2026
Sexto y último de los 6 documentos de blueprint de producto. Secuencia exacta de construcción del código, paso a paso, con dependencias explícitas — para que la implementación (humana o de agente) sepa en qué orden construir, no solo qué construir. No confundir con `docs/plan-trabajo.md`, que es el cronograma de la *postulación* (fases de investigación/diseño/evaluación con el kit de agentes) — este documento es el plan de construcción del *código*, y corresponde a la tarea 2.4 de ese cronograma ("Scaffolding del código").

## Principio de secuencia: determinista primero, IA después — también en el orden de construcción

No solo en runtime — el motor determinista se construye y se valida **completo, de punta a punta, sin ninguna llamada a LLM**, antes de agregar la capa de IA (fases A-D antes que fase E). Esto obliga a probar en código, no solo en teoría, que el producto tiene valor sustantivo sin IA (ver el ejercicio de la tabla brecha→acción sin LLM, discutido y validado en esta sesión) — si algo no funciona sin IA en la fase D, agregar IA en la fase E no lo arregla, lo disfraza.

## Fase A — Scaffolding base

| # | Tarea | Bloquea |
|---|---|---|
| A1 | Estructura de carpetas backend/frontend (`docs/TRD.md`) | Todo lo demás |
| A2 | Docker Compose esqueleto: 3 servicios (nginx + backend + db), aunque backend/frontend estén vacíos — valida la forma de despliegue desde el día 1 | A5 |
| A3 | CI: lint + type-check + test + chequeo de licencias (en ese orden, `docs/TRD.md`) — activo desde el primer commit con código, no al final | Ninguna task de código subsiguiente se acepta sin pasar A3 |
| A4 | `.env.example` documentado; secretos reales nunca commiteados | B3, E1 |

## Fase B — Modelo de datos y autenticación

| # | Tarea | Depende de | Bloquea |
|---|---|---|---|
| B1 | Modelos SQLAlchemy + migración inicial Alembic de las 7 tablas (`docs/backend-schema.md`) | A1 | B2, C1 |
| B2 | Políticas RLS por tabla (SQL, `docs/backend-schema.md`) | B1 | C1 (sin RLS, no se prueba nada multi-tenant) |
| B3 | Auth: `POST /api/auth/login`, JWT, middleware `SET app.tenant_id` | B2, A4 | D1 |
| B4 | Script de datos semilla: 1 tenant, 1 usuario, 3-5 trámites de prueba (MX y UY) — fixture de desarrollo, no fuente de verdad; `app/seed.py` aborta si `ENVIRONMENT=production` para no crear el usuario de password fijo fuera de dev/test | B1 | C1, D1 |

## Fase C — Motor determinista (cero LLM en toda esta fase)

| # | Tarea | Depende de | Bloquea |
|---|---|---|---|
| C1 | `engine/`: cálculo del índice de madurez (F2), puro, con tests basados en tabla (mismos datos → mismo índice, MX y UY) | B4 | C2 |
| C2 | Catálogo `engine/reglas/*.yaml` — arrancar con las ~10-15 entradas del catálogo finito (una por variable de diagnóstico × país), citando `entregables/fase-1/matriz-normativa.md` | C1 | C3 |
| C3 | Motor de plantillas deterministas: convierte el `contenido` de brecha→acción en el texto que vería el funcionario, **sin ningún LLM** — este es el "camino feliz" que debe funcionar solo, de principio a fin, antes de tocar la fase E | C2 | D2, E2 |

**Punto de control obligatorio al final de la fase C**: generar un plan completo para un trámite de prueba usando solo C1-C3, sin ninguna key de API configurada, y verificar que es sustantivamente útil (mismo ejercicio que se hizo manualmente en esta sesión, ahora en código real).

## Fase D — API

| # | Tarea | Depende de | Bloquea |
|---|---|---|---|
| D1 | Endpoints REST: trámites, diagnóstico (capturar/consultar respuestas), seguimiento (`accion_seguimiento`) | B3, B4 | D2, F2 |
| D2 | Tabla `job` + `BackgroundTasks`: disparar generación de plan de forma asíncrona, en modo degradado (fase C únicamente) | C3, D1 | F3 |

## Fase E — Capa de IA (F1, F3, F9) — recién aquí entra el LLM

| # | Tarea | Depende de | Bloquea |
|---|---|---|---|
| E1 | Config LiteLLM (`docs/TRD.md`): rutas `economico` (DeepSeek) y `calidad` (Claude), manejo de ausencia de key | A4, D2 | E2 |
| E2 | Generador de plan con LLM (F3): redacta sobre el `contenido` ya producido por C2-C3 — nunca decide la acción, solo la prosa | E1, D2 | E3 |
| E3 | Verificador (F9): audita la salida de E2 contra el `contenido` estructurado antes de marcar `verificado=true`; si falla, el plan se muestra en modo degradado (fase C), nunca sin verificar | E2 | F4 |
| E4 | Asistente de captura (F1): clasificación de texto libre durante el cuestionario | E1 | F2 (mejora la UX, no bloquea el flujo funcional) |

## Fase F — Frontend

| # | Tarea | Depende de | Bloquea |
|---|---|---|---|
| F1 | Shell de la SPA: rutas de `docs/app-flow.md`, nav, guard de sesión | A1 | F2-F5 |
| F2 | Pantallas 1-2: login + panel resumen | D1, F1 | F3 |
| F3 | Pantalla 3: cuestionario (F1 producto) con ramificación | D2, F2 | F4 |
| F4 | Pantalla 4: plan generado, con aviso de modo degradado si aplica | E3, F3 | F5 |
| F5 | Pantalla 5: seguimiento (F6) | D1, F4 | G1 |

## Fase G — Endurecimiento y entrega

| # | Tarea | Depende de |
|---|---|---|
| G1 | Pruebas end-to-end del flujo completo (login → diagnóstico → plan → seguimiento), en modo degradado y en modo LLM | F5 |
| G2 | Observabilidad: logs a stdout, `/health`, log de auditoría del diagnóstico (`docs/stack-tecnologico.md`) | G1 |
| G3 | Documentación técnica pública limpia (sin nombres/estrategia interna) para el repo público | G1 |
| G4 | Deploy de staging/demo en el servidor de oficina (FusionCube) — solo como demo, nunca como estándar de replicabilidad (`docs/stack-tecnologico.md`) | G1, G2 |

## Qué NO hacer en ningún punto de esta secuencia

- No adelantar la fase E antes de completar y validar la fase C — es la garantía en código, no solo en documento, de que el producto no depende de un proveedor privativo para tener valor.
- No hardcodear el catálogo brecha→acción en Python en ningún momento, ni siquiera "temporalmente" — el formato de archivo estructurado (C2) es la primera versión, no un placeholder a reemplazar después.
- No saltarse el punto de control de la fase C — es la validación más barata de todo el plan y la que más protege contra construir algo frágil sin darse cuenta.

## Documentos relacionados

`docs/PRD.md`, `docs/TRD.md`, `docs/ux-brief.md`, `docs/app-flow.md`, `docs/backend-schema.md`, `docs/plan-trabajo.md` (cronograma de la postulación, no de construcción).
