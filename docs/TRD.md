# TRD — Documento de Requerimientos Técnicos — DiagMuni

Versión 1 · 21 de julio de 2026
Segundo de los 6 documentos de blueprint de producto. No repite decisiones ya cerradas en `docs/stack-tecnologico.md` (qué tecnología y por qué) ni en `docs/PRD.md` (qué construye el producto) — especifica el **cómo**: estructura, contratos, convenciones y formatos concretos, para que quien implemente no tenga que adivinar. Ninguna decisión aquí reabre lo ya fijado en `docs/stack-tecnologico.md`.

## Estructura de carpetas

```
backend/
  app/
    main.py                 # entrypoint FastAPI
    core/                    # config, seguridad (JWT), RLS session helper
    models/                  # SQLAlchemy models
    schemas/                 # Pydantic schemas (espejo de zod del frontend)
    api/                     # routers por recurso (tenants, tramites, diagnosticos, planes)
    engine/                  # motor determinista — índice de madurez, reglas normativas
      reglas/                # catálogo brecha→acción, texto estructurado (ver sección "Catálogo de reglas")
    ia/                      # las 3 piezas de IA del producto (Guía sec. 6)
      asistente_captura.py   # F1
      generador_plan.py      # F3
      verificador.py         # F9
      litellm_config.yaml    # ver sección "Capa de IA"
    jobs/                    # BackgroundTasks + tabla job
    db/                      # sesión, migraciones Alembic
  tests/
  alembic/
frontend/
  src/
    pages/
    components/
    api/                     # cliente TanStack Query
    schemas/                 # zod, espejo de backend/app/schemas
docker-compose.yml
.env.example
```

Regla dura: nada dentro de `engine/` importa nada de `ia/` — el motor determinista no puede depender de la capa de IA ni siquiera indirectamente. La dependencia va en un solo sentido: `ia/` lee del `engine/`, nunca al revés.

## Convenciones de nombres

- Python: `snake_case` para módulos, funciones, variables; `PascalCase` para clases/modelos.
- Base de datos: tablas y columnas en `snake_case`, singular (`tramite`, no `tramites`).
- API REST: recursos en plural, kebab-case en la URL (`/api/tramites`, `/api/planes-modernizacion`).
- TypeScript/React: `camelCase` para variables/funciones, `PascalCase` para componentes.
- Archivos de reglas del catálogo (ver abajo): `snake_case`, un archivo por variable de brecha (`firma_electronica.yaml`, no un archivo monolítico).

## Catálogo de reglas brecha→acción — formato concreto

Fiel a lo acordado con `transformacion-digital.md`: texto estructurado, editable sin programar, nunca hardcodeado en Python. Un archivo YAML por variable, bajo `backend/app/engine/reglas/`:

```yaml
# backend/app/engine/reglas/firma_electronica.yaml
variable: firma_electronica_habilitada
criterio_deteccion: "valor == false"
acciones:
  mx:
    paso_administrativo: "Suscribir convenio de homologación con la e.firma del SAT"
    paso_tecnico: "Integrar verificación de firma con estándar abierto (PAdES/XAdES)"
    paso_organizacional: "Capacitar a funcionarios de mostrador en uso del certificado"
    prerrequisitos: ["conectividad estable"]
    por_que_importa: "Bloquea el paso de índice 2 a 3 (transaccional completo)"
    fuente_normativa: "LNETB art. 25; ley estatal + convenio e.firma SAT"
    categoria_catalogo: "modulo_firma_electronica"   # apunta a docs/stack-tecnologico.md, catálogo OSS — nunca una marca
  uy:
    paso_administrativo: "Acogerse a la habilitación del art. 8 de la Ley 18.600"
    paso_tecnico: "Integrar verificación de firma con estándar abierto (PAdES/XAdES)"
    paso_organizacional: "Capacitar a funcionarios de mostrador en uso del certificado"
    prerrequisitos: ["conectividad estable"]
    por_que_importa: "Bloquea el paso de índice 2 a 3 (transaccional completo)"
    fuente_normativa: "Ley 18.600 art. 8; firma con custodia centralizada (Ley 19.535)"
    categoria_catalogo: "modulo_firma_electronica"
```

El motor (`engine/`) carga estos archivos en tiempo de ejecución — nunca los transcribe a código. `costo` y `tiempo` no viven aquí: los añade `infraestructura-costos` en una capa de costeo paramétrico separada (por país/moneda), para no mezclar contenido normativo-técnico (estable) con precios (volátiles).

## Capa de IA — configuración concreta

Una sola capa de abstracción (LiteLLM, u otro runtime OSS equivalente con interfaz OpenAI-compatible) para las 3 piezas de IA del producto (F1, F3, F9), conforme al diseño original de la Guía:

```yaml
# backend/app/ia/litellm_config.yaml
model_list:
  - model_name: economico
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
  - model_name: calidad
    litellm_params:
      model: anthropic/claude-sonnet-4-5
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: calidad_respaldo
    litellm_params:
      model: anthropic/claude-fable-5
      api_key: os.environ/ANTHROPIC_API_KEY
```

- F1 (asistente de captura, clasificación de texto libre) usa `economico` (DeepSeek).
- F3 (generador de plan) usa `calidad` (Claude Sonnet) — la pieza donde la redacción compleja y la trazabilidad normativa importan más. Si `calidad` falla (timeout, red, API, respuesta vacía), F3 intenta `calidad_respaldo` (Claude Fable) antes de degradar; ambas rutas comparten la misma `ANTHROPIC_API_KEY`, así que la disponibilidad se evalúa una sola vez.
- F9 (verificador) usa `economico` (DeepSeek) — solo compara la salida de F3 contra la estructura de `engine/`, tarea liviana.
- Si la API no responde, no hay conectividad, o la llamada falla por timeout: excepción capturada en `ia/`. En F3 el orden de degradación es Sonnet (`calidad`) -> Fable (`calidad_respaldo`) -> plantilla determinista (string templating simple sobre la misma estructura YAML del catálogo); en F1 y F9 el fallo de `economico` cae directo a plantilla/heurística determinista. Nunca un error visible al funcionario.
- **Variable `LLM_PROVIDER` — quién elige el proveedor:** decisión de Mario Alberto Quintana (responsable del Laboratorio de Innovación Pública del INAP): el operador de cada despliegue debe poder elegir el proveedor de IA sin tocar código, y la plataforma nunca debe gastar en una API de pago sin que se lo pidan a propósito. Implementación en `backend/app/ia/config.py` (`obtener_proveedor_llm()`): valores válidos `anthropic` / `deepseek` / `local`. Sin `LLM_PROVIDER` fijado explícitamente, el default es siempre `local` (Ollama/phi3) si `OLLAMA_API_BASE` está poblada — nunca se auto-elige `anthropic`/`deepseek` solo porque su API key esté presente; si `local` tampoco está disponible, el resultado es `None` y quien llama degrada a plantilla determinista. Fijar `LLM_PROVIDER=anthropic` o `=deepseek` explícitamente es la única forma de que el sistema use una API de pago en producción; esa ruta explícita conserva su propia cadena de fallback normal (incluida una caída adicional a `local` como red de contención, ver `_PROVEEDORES_RUTAS` en `backend/app/ia/config.py`).
- **Modelo local (Ollama/phi3) — estado de implementación:** el wiring de código ya está construido, no es una alternativa manual futura — `backend/app/ia/litellm_config.yaml` define la ruta `local` y `backend/app/ia/config.py` la resuelve como default según lo descrito arriba. Evaluado a fondo contra un benchmark comparativo real (API ~20-30x más rápida, costo marginal insignificante para el volumen de un piloto — ver `entregables/fase-2/dimensionamiento-costos.md`), por lo que DeepSeek + Claude vía API sigue siendo la arquitectura de producción documentada cuando el operador fija `LLM_PROVIDER` a propósito. **E1bis-2 cerrado:** la instalación real de Ollama (`ollama pull phi3`) y la prueba de integración end-to-end sin mocks contra un Ollama corriendo de verdad ya se ejecutaron -- `backend/tests/test_generador_plan_ollama_real.py` (skip limpio si Ollama no es alcanzable, mismo patrón que `_postgres_real_disponible()` de `test_api_seguimiento.py`) corrió dos veces contra un Ollama real con `phi3` descargado: 76.38s y 57.8s, narrativa capturada y confirmada distinta de la plantilla determinista.

## Job asíncrono — ciclo de vida

Tabla `job`: `id, tenant_id, tipo (generacion_plan), estado (pending|running|done|failed), diagnostico_id, resultado, creado_en, actualizado_en`. `BackgroundTasks` de FastAPI dispara el job; si el proceso reinicia a medio job, el estado `running` sin actualización en N minutos se reintenta (no se asume éxito silencioso). Salto a Celery: mismo contrato de tabla, cambia solo el disparador — no exige tocar el modelo de datos si el volumen lo exige después.

## Multi-tenancy — mecanismo concreto de RLS

1. JWT incluye claim `tenant_id`, validado server-side en cada request.
2. Al abrir la sesión de base de datos por request, el backend ejecuta `SET app.tenant_id = '<valor del claim>'` (session-local, nunca global).
3. Cada tabla con datos de tenant tiene policy RLS: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`.
4. Ninguna query de aplicación filtra por `tenant_id` manualmente — la policy es la única barrera; esto es intencional: una columna sola "puede olvidarse" en un query, una policy de RLS no.
5. `SET LOCAL` (session-local con `is_local=true`) se resetea automáticamente al terminar la transacción — cualquier `db.commit()` o `db.rollback()` lo limpia. Todo código que haga más de un commit en la misma sesión debe volver a llamar a `fijar_contexto_tenant` antes de la siguiente consulta contra una tabla con RLS (ver `backend/tests/test_api_seguimiento.py` y `backend/tests/test_api_diagnosticos.py`).

## Alta de un gobierno nuevo

Sin onboarding self-service (`docs/PRD.md`, "Fuera de alcance"): el alta de un gobierno la ejecuta siempre la contraparte técnica u operador del despliegue, nunca un flujo público. Herramienta: `backend/app/bootstrap_tenant.py`, corrida como `python -m app.bootstrap_tenant <comando>` (dentro del contenedor: `docker compose exec backend python -m app.bootstrap_tenant <comando>`) — paso a paso operativo completo en `docs/runbook-alta-gobierno.md`.

- `crear-gobierno --nombre --clave --pais {mx,uy} --email --nombre-funcionario`: crea el `Tenant` y su primer `Usuario`. Idempotente por `clave` duplicada (no-op limpio, no falla ni duplica). Transaccional todo-o-nada.
- `resetear-password --clave --email`: genera una contraseña nueva para un usuario ya existente, sin crear nada.
- Ninguno de los dos comandos acepta una contraseña como argumento — ambos la generan siempre con `generar_password_legible()` (`backend/app/core/security.py`: alfabeto de 55 símbolos sin ambigüedad visual, 16 caracteres, ~92.5 bits de entropía) y la imprimen una sola vez en la salida del comando. Sin variable de entorno nueva.
- `backend/app/seed.py` (fixture de desarrollo, nunca fuente de verdad de datos reales) reutiliza `crear_gobierno()` de este mismo módulo en vez de construir `Tenant`/`Usuario` por su cuenta — un solo camino de creación de usuarios en todo el proyecto.

## Versionado del motor de reglas

Cada archivo en `engine/reglas/` y el módulo de índice de madurez llevan un campo `version` (semver simple: `1.0`, `1.1`...). Cada `diagnostico_tramite` persiste qué `version` del motor lo calculó. Cambiar una regla normativa (ej. reforma legal) sube la versión — nunca se sobreescribe una versión ya usada por un diagnóstico existente, para no romper reproducibilidad retroactiva.

## CI/CD

GitHub Actions, pasos en este orden: (1) lint (ruff/eslint), (2) type-check (mypy/tsc), (3) tests (pytest/vitest), (4) chequeo de licencias de dependencias (pip-licenses/licensecheck — falla el build si aparece algo fuera de MIT/BSD/Apache/GPL-separado), (5) build de imágenes Docker, (6) deploy de preview a Cloudflare Pages (solo en PRs, nunca en `main`).

## Variables de entorno

`.env` (nunca commiteado, ya cubierto por `.gitignore`): `DATABASE_URL`, `JWT_SECRET`, `OLLAMA_API_BASE` (opcional — su ausencia, o que el proceso de Ollama no responda, degrada a plantillas, no rompe el arranque), `LLM_PROVIDER` (opcional — valores válidos `anthropic`/`deepseek`/`local`; ausente o vacía cae al default `local` si `OLLAMA_API_BASE` está poblada, o a plantilla determinista si no; ver "Capa de IA — configuración concreta" arriba). `.env.example` documenta cada variable sin valores reales.

## Testing

Motor determinista (`engine/`): cobertura alta, tests basados en tabla (mismos datos de entrada → mismo índice, por país). Capa de IA (`ia/`): tests de que la degradación a plantilla ocurre correctamente cuando la API no responde o falla — no se testea la calidad de la prosa del LLM, eso no es determinista por naturaleza.

## Documentos relacionados

`docs/PRD.md` (qué y por qué), `docs/stack-tecnologico.md` (qué tecnología, decisiones fijadas), `docs/backend-schema.md` (detalle exhaustivo de tablas/columnas), `docs/app-flow.md`, `docs/ux-brief.md`, `docs/plan-implementacion.md`.
