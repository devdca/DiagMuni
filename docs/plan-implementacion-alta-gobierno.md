# Plan de implementación — Alta del primer gobierno (tenant + usuario) al adoptar DiagMuni

Versión 1 · 6 de agosto de 2026. Producido por el coordinador (corriendo sobre el modelo Fable), por instrucción directa del usuario: "me gusta el concepto del primer usuario con contraseña aleatoria, pero debemos afinarlo, recuerda que es un proyecto para los gobiernos open source, no puede ser frágil este paso." Cierra una brecha de producto (no una fase ya aprobada) detectada en conversación directa con el usuario, no una disputa de auditoría.

Este documento es **solo planeación**. Ninguna tarea que aquí se describe se ha ejecutado. No pasa por el auditor en sí mismo (es planeación, no código); cualquier tarea de código que aquí se defina sí deberá pasar por el loop normal de auditoría (`.claude/README.md`: máx. 2 iteraciones, luego escalar a Mario Alberto Quintana) cuando se ejecute. Criterio rector explícito de esta sesión: **no fragilidad operativa por encima de elegancia de código** — cada alternativa se evalúa contra ese criterio, no contra facilidad de implementación.

## 0. La brecha exacta (verificada contra código real de `feature/frontend`)

- `backend/app/seed.py` (archivo completo) es un fixture de desarrollo explícito: docstring líneas 1-8 ("Fixture de desarrollo/pruebas únicamente — nunca fuente de verdad para datos de un municipio o intendencia real"); línea 17 fija `PASSWORD_PRUEBA = "cambiar123"` (pública en el repo, compartida por los dos usuarios de prueba); líneas 27-32 abortan con `RuntimeError` si `settings.environment == "production"`. Ese guard es parte del diseño original de la tarea B4 (`docs/plan-implementacion.md` línea 26: "`app/seed.py` aborta si `ENVIRONMENT=production` para no crear el usuario de password fijo fuera de dev/test"), aprobada como completa (`entregables/plan.md` línea 26, "B. Modelo de datos y auth ... Aprobada — completa") y no se toca aquí — es precedente de diseño, no algo a rediscutir.
- `backend/app/api/auth.py` (líneas 1-38): el único endpoint es `POST /api/auth/login`. `backend/app/schemas/auth.py` (líneas 6-12) confirma que `LoginRequest` exige `tenant_id: UUID`, `email: str`, `password: str`. No existe `POST /api/auth/register` ni nada equivalente en ningún archivo de `backend/app/api/`.
- `docs/PRD.md` línea 44, "Fuera de alcance": "Onboarding self-service sin asistencia — el piloto asume una contraparte técnica designada por la intendencia (requisito de la convocatoria), no un funcionario anónimo llegando sin contexto." Restricción de producto real y vigente: quien ejecuta el alta es siempre la contraparte técnica designada u operador del despliegue, nunca un flujo público sin asistencia. Cada alternativa de la sección 1 se justifica contra esta restricción.
- `backend/app/models/usuario.py` (26 líneas): campos `id`, `tenant_id`, `email`, `password_hash`, `nombre`, `rol` (enum con un solo valor, `"funcionario"`), `created_at`. No existe ningún campo tipo "debe cambiar password en el próximo login" — un flujo de "temporal + forzar cambio" es alcance nuevo (columna + migración + lógica de login + pantalla de frontend), no algo parcialmente construido.
- `backend/app/models/tenant.py` (24 líneas): campos `id`, `nombre`, `clave` (`String`, `unique=True` — identificador corto que el funcionario escribe en login, ver comentario líneas 19-21 y `entregables/fase-2/identificacion-gobierno-login.md`), `pais` (`Enum("mx", "uy", ...)`, línea 23), `created_at`. La columna `clave` y su migración (`0002_tenant_clave.py`) ya existen — no es trabajo pendiente de este plan, es un insumo que este plan reutiliza tal cual.
- `backend/app/core/security.py` (43 líneas): `hash_password`/`verify_password` usan `argon2.PasswordHasher()` (línea 10) — se usa tal cual, sin proponer otro hasher.
- `backend/app/db/rls.py` (43 líneas): `fijar_contexto_tenant(db, tenant_id)` (líneas 10-25) es el único mecanismo real para poblar `app.tenant_id` vía `set_config(..., is_local=true)` antes de cualquier insert/select en tablas con RLS forzado; `abrir_sesion_tenant(tenant_id)` (líneas 28-33) abre sesión + fija contexto en un paso. `backend/app/seed.py` (líneas 20-24) usa su propia copia `_set_tenant` con el mismo patrón, marcada como tal ("Mismo mecanismo que app/db/rls.py") — aceptable en un fixture descartable, no aceptable en una herramienta que va a tocar datos reales de un gobierno (ver sección 6).
- `backend/alembic/versions/0001_initial_schema.py` (líneas 156-168): 6 tablas con `tenant_id` (incluida `usuario`) reciben `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + policy `tenant_id = current_setting('app.tenant_id')::uuid`. `tenant` no tiene RLS propio (es la tabla raíz de aislamiento, `models/tenant.py` línea 13) — puede insertarse sin fijar `app.tenant_id` antes, igual que hace `seed.py` línea 39.
- `backend/app/core/config.py` (30 líneas): patrón ya establecido para variables de entorno nuevas — `Settings(BaseSettings)` con default explícito y comentario que justifica el default. Este plan no necesita ninguna variable nueva (ver sección 3 y 8) — se documenta explícitamente como decisión, no como omisión.
- Verificado con `grep -n "^## " docs/TRD.md`: no existe ninguna sección de alta/onboarding/registro/bootstrap hoy. Se propone una sección nueva (sección 9).
- Verificado con `ls docs/*.md`: no existe ningún `docs/runbook*.md` hoy. Se propone `docs/runbook-alta-gobierno.md` (sección 9), sin abrir carpeta nueva.
- `docker-compose.yml` línea 18: el servicio de backend se llama `backend` — confirma que el ejemplo de comando `docker compose exec backend python -m app.<módulo>` (mismo patrón ya usado para `python -m app.seed`, docstring de `seed.py` línea 7) es ejecutable tal cual contra el despliegue de referencia de este proyecto.
- `frontend/src/pages/LoginPage.tsx`: el campo `password` (líneas 133-135) es un `<input type="password">` de texto libre, sin `maxLength` ni `pattern` — cualquier contraseña generada (incluidos guiones como caracteres literales) funciona sin cambios de frontend.
- `entregables/fase-2/identificacion-gobierno-login.md` (documento completo): fija que `clave` se normaliza en capa de aplicación (`trim()` + `lower()`, sección 1) antes de comparar/guardar, y que el patrón de slug válido (sección 2, migración `0002`) es `[a-z0-9-]` derivado de `nombre` solo como *backfill* de tenants ya existentes en el piloto — para un tenant nuevo la `clave` la declara el operador explícitamente, no se deriva automáticamente. Este plan reutiliza esa misma normalización y ese mismo criterio de charset (sección 5).

## 1. Mecanismo elegido y alternativas evaluadas

**Alternativas evaluadas:**

**(a) Script CLI de administración**, corrido por el operador del servidor: `docker compose exec backend python -m app.bootstrap_tenant crear-gobierno --nombre "..." --clave "..." --pais mx --email "..." --nombre-funcionario "..."`. Mismo estilo de invocación que `python -m app.seed` (ya documentado, `seed.py` línea 7), pero como herramienta de producción, no como fixture de desarrollo.

**(b) Endpoint HTTP protegido por un secreto de arranque de un solo uso** (`SETUP_TOKEN` en `.env`, consumido y quemado tras el primer uso), del estilo `POST /api/setup/bootstrap`.

**(c) Combinación**: CLI como mecanismo real, con un endpoint delgado opcional en el futuro que reutilice la misma función interna, para un escenario de despliegue centralizado sin acceso a shell — explícitamente diferido, no se construye ahora (ver sección 7).

**Decisión: (a), CLI.** Comparación explícita contra el criterio de no-fragilidad (no contra facilidad de codificar, que sería casi idéntica en ambos casos):

| Criterio de fragilidad | (a) CLI | (b) Endpoint + `SETUP_TOKEN` |
|---|---|---|
| Superficie de red nueva | Ninguna — requiere la misma sesión de shell que el operador ya necesita para `docker compose up`, migraciones y (hoy) `python -m app.seed`. | Sí — un endpoint no autenticado alcanzable por cualquier tráfico entrante mientras el token esté activo; el riesgo real no es teórico: el propio diseño original del proyecto ya trató como inaceptable una credencial predecible en manos equivocadas — `docs/plan-implementacion.md` línea 26 documenta que `app/seed.py` aborta explícitamente si `ENVIRONMENT=production` para que su password fijo (`cambiar123`) nunca llegue a un despliegue real (ver sección 0). |
| Estado nuevo a mantener sincronizado con la realidad | Ninguno. | Requiere un mecanismo de "ya se usó" (flag en memoria se pierde en cada reinicio del contenedor — reabre el endpoint sin que nadie lo note; flag persistido en BD exige columna/tabla nueva, o un heurístico "¿ya existe algún tenant?" que rompe el requisito de multi-tenant día uno, `docs/PRD.md` sección "Dentro de alcance" punto 5, porque bloquearía onboardear un segundo gobierno en el mismo despliegue). |
| Consistencia con patrones ya existentes en el repo | Exactamente el patrón ya usado y aprobado de `seed.py` (`python -m app.<módulo>`), solo que apuntando a datos reales en vez de datos de prueba. | Ningún endpoint hoy en `backend/app/api/` crea datos sin autenticación — `POST /api/auth/login` (el único público) solo lee. Introducir el primer endpoint público de escritura es un patrón nuevo en la superficie HTTP, exactamente donde más cuidado hay que tener. |
| Ajuste al usuario real (`docs/PRD.md` línea 44) | Quien levanta `docker compose` ya tiene terminal en ese host — cero herramienta nueva que aprender. | Exige que la contraparte técnica sepa armar una llamada HTTP autenticada por token (curl/Postman) y sepa dónde vive/cómo protege ese token en `.env` — más piezas para un "operador nervioso" (mismo perfil de riesgo ya nombrado en el precedente de `seed.py`). |
| Auditoría | La salida se imprime en la terminal que ejecuta el comando; repetible/documentable en un runbook paso a paso. | Requiere logging HTTP aparte para tener el mismo nivel de rastro. |

(b) se descarta explícitamente: agrega justo la clase de fragilidad que el usuario señaló (un secreto nuevo que gestionar/perder/olvidar desactivar, un estado "usado" que puede desincronizarse de la realidad tras un reinicio) a cambio de una ventaja que el usuario objetivo (contraparte técnica con acceso al servidor, `docs/PRD.md` línea 44) no necesita. (c) queda como posibilidad futura explícita, no cerrada por este diseño (la función interna del CLI puede reutilizarse detrás de un endpoint más adelante si un despliegue centralizado sin shell lo justifica) pero no se construye ahora.

## 2. Generación de la contraseña

**Librería:** `secrets` de la biblioteca estándar de Python — PSF License 2.0 (permisiva, sin cláusulas de copyleft, compatible con Apache 2.0; no es una dependencia nueva a declarar en `requirements.txt`, ya viene con el intérprete). Se descarta cualquier librería de terceros para esto: no hay necesidad real que `secrets` no cubra.

**Alfabeto legible para dictar por teléfono:** se excluyen caracteres visualmente ambiguos — dígitos `2-9` (se excluyen `0`/`1`), mayúsculas sin `I`/`O`, minúsculas sin `i`/`l`/`o`. Alfabeto resultante: 8 dígitos + 24 mayúsculas + 23 minúsculas = 55 símbolos.

**Longitud:** 16 caracteres → entropía ≈ 16 × log₂(55) ≈ 16 × 5.78 ≈ **92.5 bits** — muy por encima del piso de 80 bits razonable para una credencial de arranque de alto valor (varias veces el mínimo de ~20 bits que NIST SP 800-63B exige para secretos generados aleatoriamente).

**Formato de presentación:** agrupada en 4 bloques de 4 caracteres separados por guion (ej. `k7Ht-4mQs-2wZp-9bKf`), solo para legibilidad al dictar o transcribir — los guiones son parte literal de la contraseña (no se limpian antes de enviarla al backend), evitando un paso manual de "quite los guiones antes de escribirla" que un operador podría olvidar. Verificado que esto funciona sin cambios de frontend: `frontend/src/pages/LoginPage.tsx` no aplica `pattern` ni `maxLength` al campo `password`.

**Decisión: contraseña final, sin "temporal + forzar cambio".** Construir esa alternativa exigiría: (1) columna nueva en `usuario` (no existe hoy, `models/usuario.py` 26 líneas) + migración Alembic; (2) lógica nueva en `POST /api/auth/login` o un endpoint adicional para detectar/redirigir; (3) una pantalla nueva en `frontend/src/pages/`. Más piezas que mantener sincronizadas = más fragilidad, no menos, por una ganancia marginal: un flujo de "el propio funcionario cambia su password" es, en espíritu, autoservicio — justo lo que `docs/PRD.md` línea 44 excluye para el alta. La contraseña generada por el operador **es** la contraseña operativa desde el primer login; si el gobierno quiere cambiarla más adelante, lo hace pidiéndole al operador del despliegue que corra el reseteo (sección 3) — misma postura asistida que el resto del producto, sin inventar una superficie de autoservicio nueva.

## 3. Entrega de la contraseña al operador y reseteo

**Entrega:** se imprime una sola vez en la salida de la terminal del comando `crear-gobierno`, con una advertencia explícita inmediatamente antes, del estilo:

```
====================================================================
ADVERTENCIA: esta contraseña no se vuelve a mostrar. Anótela ahora
y entréguela a la contraparte técnica por un canal seguro.
====================================================================
Gobierno: Intendencia de Canelones (clave: canelones)
Funcionario: María Pérez <maria.perez@canelones.gub.uy>
Contraseña temporal de arranque: k7Ht-4mQs-2wZp-9bKf
====================================================================
```

Sin dependencia de SMTP: el producto no declara correo como núcleo (`.env.example` no tiene ninguna variable de correo hoy) y no se agrega aquí. Precedente ya existente en el repo del patrón "imprimir una sola vez": `seed.py` línea 85 ya imprime `PASSWORD_PRUEBA` a stdout — este diseño aplica el mismo patrón a un valor real generado, no a una constante fija.

**Supuesto explícito, no garantía:** que el operador conserve esa salida (captura de pantalla, historial de la terminal, gestor de contraseñas) es responsabilidad suya — el script no la persiste en ningún archivo ni log propio en texto plano.

**Si el operador la pierde: sí existe mecanismo de reseteo, dentro de este mismo alcance — no queda fuera.** El mismo módulo expone un segundo subcomando, `resetear-password --clave <clave-del-gobierno> --email <correo-del-funcionario>`, que localiza al usuario existente (tenant por `clave`, sin RLS; usuario por `tenant_id`+`email`, con RLS fijado según sección 6), genera una contraseña nueva con el generador de la sección 2 y sobrescribe `password_hash`. Se incluye porque no exige ninguna columna ni migración nueva (es la misma operación de `hash_password` + `UPDATE` que ya existe conceptualmente en `seed.py`) y cierra un punto de fragilidad real: un despliegue autoalojado sin este mecanismo dejaría a un gobierno fuera de su propia plataforma sin ninguna vía de recuperación más que reconstruir la base de datos. No es un "olvidé mi password" de autoservicio (eso seguiría excluido por `docs/PRD.md` línea 44) — exige el mismo acceso de shell al servidor que el alta original, mismo perímetro de confianza.

## 4. Idempotencia y manejo de errores

**Correr `crear-gobierno` dos veces con los mismos datos:** antes de escribir nada, el script busca `Tenant` por `clave` normalizada (`SELECT ... WHERE clave = :clave`, sin RLS, igual que hoy hace `seed.py` línea 39 con el flush de tenants). Si ya existe, termina con código de salida distinto de cero y un mensaje en lenguaje llano: "Ya existe un gobierno con la clave 'canelones' (Intendencia de Canelones). No se creó nada nuevo. Para agregar otro funcionario a este gobierno, ese flujo no existe todavía (ver sección 7)." — no-op seguro, cero escritura, sin necesitar que el operador razone sobre una traza de `IntegrityError`.

**Transaccionalidad todo-o-nada**, mismo patrón `try`/`finally` con `db.close()` en el `finally` que ya usa `seed.py` (líneas 34-87), con una diferencia deliberada: `seed.py` es un fixture de desarrollo que puede fallar ruidosamente (no hay datos reales que proteger); esta herramienta sí toca datos reales de un gobierno, así que agrega un `except` explícito que hace `db.rollback()` antes de re-lanzar el error, para no depender de que el cierre de la conexión por sí solo deshaga cambios no confirmados:

```python
db = SessionLocal()
try:
    # 1. valida entrada (sección 5) antes de cualquier escritura
    # 2. verifica que no exista ya un tenant con esa clave (no-op si existe)
    # 3. crea Tenant, db.flush()  (tenant no tiene RLS)
    # 4. fijar_contexto_tenant(db, tenant.id)  (app/db/rls.py, no una copia local)
    # 5. crea Usuario, db.flush()
    # 6. db.commit()
except Exception:
    db.rollback()
    raise
finally:
    db.close()
```

**Fallo a la mitad** (ej. el `Usuario` viola alguna restricción tras crear el `Tenant` en la misma transacción): el `rollback()` deshace ambas escrituras porque comparten la misma sesión/transacción sin `commit()` intermedio — no queda un `Tenant` huérfano sin `Usuario`.

## 5. Validación de entrada

- **`pais`:** `argparse` con `choices=["mx", "uy"]` — coincide exactamente con `Enum("mx", "uy", name="pais_enum")` de `models/tenant.py` línea 23; un valor fuera de esos dos se rechaza antes de tocar la base de datos, con el propio mensaje de `argparse`.
- **`email`:** validación de formato mínima con `re` de la biblioteca estándar (`^[^@\s]+@[^@\s]+\.[^@\s]+$` o equivalente) — no se agrega una librería de validación de correo nueva porque el proyecto no la usa hoy en ningún lado (`schemas/auth.py` línea 11 declara `email: str` sin `EmailStr`); suficiente para atrapar errores de tecleo obvios sin sumar una dependencia.
- **`nombre` (nombre del gobierno) y `nombre-funcionario`:** no vacíos después de `strip()` — mismo criterio que ya exige `nullable=False` en ambos modelos.
- **`clave`:** normalizada igual que el resto del sistema (`trim()` + `lower()`, mismo criterio que `entregables/fase-2/identificacion-gobierno-login.md` sección 1 y el `GET /api/gobiernos/{clave}` que ese documento especifica) y validada contra `^[a-z0-9-]+$` sin guiones al inicio/final ni dobles — mismo espíritu de charset que la migración `0002` usa para el backfill automático, aplicado aquí como validación explícita de una `clave` que el operador escribe a mano, para que un operador no técnico no la deje con espacios, acentos o mayúsculas mezcladas que después no coincidan con lo que un funcionario teclea en el login.
- **Contraseña:** no es un dato de entrada en ningún subcomando de esta herramienta — ambos (`crear-gobierno` y `resetear-password`) la generan siempre con la función de la sección 2. Decisión deliberada: elimina cualquier validación de fortaleza de contraseña que hubiera que escribir y mantener, porque nunca hay una contraseña escrita a mano por el operador que validar.

## 6. Cumplimiento de RLS

El script importa y usa **exclusivamente** `fijar_contexto_tenant`/`abrir_sesion_tenant` de `backend/app/db/rls.py` — nunca una copia local del `SELECT set_config(...)`. Esto es una desviación deliberada del patrón de `seed.py` (que sí mantiene su propia copia `_set_tenant`, aceptable en un fixture descartable de pocas líneas): duplicar la lógica de contexto de RLS en una herramienta que toca datos reales crea el riesgo de que, si `app/db/rls.py` cambia (ej. un tercer parámetro, un nombre de variable de sesión distinto), la copia quede desincronizada en silencio. Reutilizar el módulo real elimina esa clase de bug por construcción.

Secuencia concreta para `crear-gobierno`:
1. `Tenant(...)` se crea y se hace `db.flush()` sin fijar `app.tenant_id` — correcto, `tenant` no tiene RLS propio (`models/tenant.py` línea 13; `alembic/versions/0001_initial_schema.py`, `tenant` no aparece en la lista de tablas con `FORCE ROW LEVEL SECURITY`).
2. Tras el flush, `tenant.id` ya está poblado en el objeto Python (mismo comportamiento que `seed.py` usa inmediatamente después de su propio `db.flush()`, líneas 39-41).
3. `fijar_contexto_tenant(db, tenant.id)` antes de crear el `Usuario` — obligatorio porque `usuario` sí tiene `FORCE ROW LEVEL SECURITY` (`0001_initial_schema.py` líneas 156-168).
4. `Usuario(tenant_id=tenant.id, ...)` se crea y se hace `db.flush()` dentro de esa misma transacción con `app.tenant_id` ya fijado.
5. Un solo `db.commit()` al final (sección 4) — recordando la nota propia de `fijar_contexto_tenant` (`app/db/rls.py` líneas 19-23): cada `commit()`/`rollback()` resetea `app.tenant_id`, así que si en el futuro este script necesitara más de un `commit()` en la misma sesión, tendría que volver a llamar `fijar_contexto_tenant` después de cada uno — no aplica hoy porque este diseño usa un único `commit()`.

Para `resetear-password`: `Tenant` se busca por `clave` sin fijar contexto (mismo motivo del punto 1); una vez resuelto `tenant.id`, se llama `fijar_contexto_tenant(db, tenant.id)` antes del `SELECT`/`UPDATE` sobre `Usuario` (que sí tiene RLS forzado).

## 7. Alcance explícitamente excluido

- **Este mecanismo crea exactamente un tenant y un usuario por invocación de `crear-gobierno`.** No existe, en este diseño, ninguna forma de agregar un segundo/tercer funcionario a un gobierno ya existente — eso es alcance futuro explícito (un subcomando nuevo tipo `agregar-funcionario --clave <clave-existente> --email ... --nombre ...`, o un endpoint administrativo autenticado `POST /api/usuarios`), no construido ni parcialmente esbozado aquí. La única excepción deliberada es `resetear-password` (sección 3), que opera sobre un usuario **ya existente** y no crea usuarios nuevos.
- **Nada impide correr `crear-gobierno` de nuevo con una `clave` distinta para dar de alta un segundo gobierno en el mismo despliegue** — el chequeo de idempotencia de la sección 4 solo bloquea una `clave` duplicada, nunca una `clave` nueva. Esto es justamente lo que sostiene el requisito de "multi-tenant desde el día uno... un despliegue puede servir a varios municipios" (`docs/PRD.md`, "Dentro de alcance", punto 5) sin que este plan tenga que construir nada adicional para eso: ya es la forma natural en que el CLI se usa repetidamente.
- **La alternativa (c) de la sección 1** (endpoint delgado reutilizando la misma función interna, para un despliegue centralizado sin acceso a shell) queda fuera de este alcance, sin cerrarse como imposible a futuro.
- **`[NO VERIFICADO]`:** si INAP o el Laboratorio de Innovación Pública planean operar un despliegue centralizado para múltiples gobiernos sin que cada uno tenga acceso de shell al servidor (en cuyo caso la alternativa (c) dejaría de ser opcional), no hay evidencia en el repo revisado de que ese escenario esté decidido — se trata como hipótesis futura, no como requisito actual.

## 8. Tabla de tareas de construcción

| # | Tarea | Depende de | Bloquea | Especialista | Estado |
|---|---|---|---|---|---|
| ALTA-1 | Implementar `backend/app/bootstrap_tenant.py` (subcomandos `crear-gobierno` y `resetear-password`, `argparse`), reutilizando `app/db/rls.py` (sección 6), `app/core/security.py` (`hash_password`) y un generador de contraseña nuevo (`generar_password_legible()`, propuesto en `app/core/security.py` junto a `hash_password`/`verify_password`, sección 2) | Ninguna | ALTA-2 | ia-automatizacion | Pendiente de asignar |
| ALTA-2 | Tests unitarios: idempotencia (clave duplicada → no-op limpio), validaciones de entrada (sección 5), transaccionalidad/rollback (sección 4), uso real de `fijar_contexto_tenant`/`abrir_sesion_tenant` (no una copia local, sección 6), entropía/alfabeto del generador de contraseña, `resetear-password` sobre un usuario existente y sobre uno inexistente — `backend/tests/test_bootstrap_tenant.py` | ALTA-1 | ALTA-3 | ia-automatizacion | Pendiente de asignar |
| ALTA-3 | Documentación: sección nueva "Alta de un gobierno nuevo" en `docs/TRD.md`; runbook operativo nuevo `docs/runbook-alta-gobierno.md` con el comando exacto (`docker compose exec backend python -m app.bootstrap_tenant ...`) y la captura de pantalla/ejemplo de salida esperada; confirmar explícitamente en `.env.example` que este mecanismo no agrega ninguna variable nueva (sección 1, tabla) | ALTA-1 | ALTA-4 | ia-automatizacion | Pendiente de asignar |
| ALTA-4 | Auditoría conjunta de ALTA-1 + ALTA-2 + ALTA-3 como un solo entregable (código + tests + docs, un solo ciclo, máx. 2 iteraciones) | ALTA-3 | Cierre de este plan | auditor | Pendiente de asignar |

**Paralelismo real disponible:** ninguno — las tres tareas de construcción son estrictamente secuenciales (ALTA-2 necesita el código de ALTA-1; ALTA-3 necesita el comando final de ALTA-1 para documentarlo con precisión; ALTA-4 necesita las tres). No hay una tarea equivalente a la "E1bis-5 opcional" del precedente en este alcance acotado.

## 9. Documentos a actualizar cuando se ejecute

- **`docs/TRD.md`:** sección nueva "Alta de un gobierno nuevo", ubicada después de "Multi-tenancy — mecanismo concreto de RLS" (línea 108 actual) y antes de "Versionado del motor de reglas" — describe el comando `crear-gobierno`/`resetear-password`, la ausencia de variables de entorno nuevas, y remite a este documento y al runbook para el detalle operativo.
- **`docs/runbook-alta-gobierno.md` (nuevo)** — nombre decidido siguiendo la convención plana ya usada en `docs/*.md` (sin carpeta nueva), paralelo a como `docs/plan-implementacion-e1-bis-capa-ia-local.md` extiende `docs/plan-implementacion.md`. Contenido: pasos operativos paso a paso para quien opera el despliegue (comando exacto, ejemplo de salida esperada con la advertencia de la sección 3, qué hacer si el comando informa que la `clave` ya existe, cómo resetear una contraseña perdida).
- **`.env.example`:** no requiere ninguna línea nueva — se documenta explícitamente en el runbook que este mecanismo no depende de ninguna variable de entorno adicional (a diferencia de la alternativa (b) descartada en la sección 1, que hubiera necesitado `SETUP_TOKEN`). Esto en sí mismo es parte del argumento de no-fragilidad: nada nuevo que quede mal configurado.
- **`docs/backend-schema.md`:** sin cambios — este plan no modifica ningún esquema (la columna `clave` de `tenant` ya existe desde `0002_tenant_clave.py`, y este plan no agrega columnas nuevas).

## 10. Riesgos y supuestos abiertos

- El operador es responsable de la persistencia de la salida de la terminal (sección 3) — el script deliberadamente no la escribe a ningún archivo propio en texto plano, para no crear un nuevo lugar donde una contraseña real quede en reposo sin cifrar. Si esto se considera insuficiente en la práctica del piloto, la alternativa (guardar un hash de verificación aparte, o instruir al operador a usar un gestor de contraseñas) queda para una sesión posterior, no se resuelve aquí.
- `[NO VERIFICADO]` si existe o se planea un despliegue centralizado multi-gobierno sin acceso de shell por gobierno (ver sección 7) — de confirmarse, reabriría la alternativa (c) como no opcional.
- Este plan no construye `agregar-funcionario` (alta de un segundo funcionario a un gobierno ya existente) — alcance futuro explícito (sección 7), no ambiguo.
- La regex de validación de `email` (sección 5) es una validación de formato básica, no una verificación de entregabilidad real (no hay SMTP en este proyecto) — coherente con que este mecanismo nunca envía correo.
- El nombre exacto de la función `generar_password_legible()` y su ubicación en `app/core/security.py` es una propuesta de este plan, no un contrato ya fijado — el especialista que ejecute ALTA-1 puede ajustar el nombre siempre que preserve las propiedades de la sección 2 (alfabeto sin ambigüedad, ≥ 92 bits de entropía).

## 11. Documentos relacionados

`docs/PRD.md` (línea 44, restricción de alcance), `docs/TRD.md` (sección nueva a agregar), `backend/app/seed.py` (precedente de guard de producción y de "imprimir una sola vez", no se toca), `backend/app/api/auth.py`, `backend/app/schemas/auth.py`, `backend/app/models/usuario.py`, `backend/app/models/tenant.py`, `backend/app/core/security.py`, `backend/app/db/rls.py`, `backend/alembic/versions/0001_initial_schema.py`, `backend/alembic/versions/0002_tenant_clave.py`, `entregables/fase-2/identificacion-gobierno-login.md` (normalización y charset de `clave`), `entregables/plan.md` línea 26 (Fase B aprobada), `docs/plan-implementacion.md` línea 26 (especificación original del guard de `app/seed.py`), `docs/plan-implementacion-e1-bis-capa-ia-local.md` (precedente de formato de este documento).
