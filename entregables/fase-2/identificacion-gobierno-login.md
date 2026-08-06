# Identificación del gobierno en el login — mecanismo de resolución de tenant

Versión 1 · 4 de agosto de 2026
Entregable de diseño puro (sin código), bloqueante de F2 antes de construir las pantallas de login y panel resumen. Resuelve el vacío detectado entre `docs/ux-brief.md` (da por sentado que el sistema ya conoce el nombre del gobierno local al momento del login) y el contrato real de `POST /api/auth/login`, que exige un `tenant_id: UUID` explícito y no tiene forma de obtenerse a partir de nada legible por un funcionario de mostrador. Mismo estándar de esta casa que en `entregables/fase-2/asistente-captura-f1.md`: cada afirmación cita ruta + línea/sección verificada directamente antes de escribir este documento.

## 0. Hechos verificados antes de decidir

- `docs/ux-brief.md` línea 62-63 (pantalla 1, "Selección de gobierno (tenant) e ingreso"): "Pantalla mínima: nombre del gobierno local (o selector si el funcionario tiene acceso a más de uno — poco común en el MVP), campo de credenciales." No dice cómo se obtiene ese "nombre del gobierno local" antes del login.
- `docs/ux-brief.md` línea 8 (principio de diseño 1): "Sin jerga técnica, en ningún estado de la interfaz... Ningún texto de UI usa vocabulario de sistemas (\"endpoint\", \"token\", \"payload\")..." — un UUID pegado a mano es exactamente ese tipo de vocabulario técnico, aunque no tenga esos nombres.
- `backend/app/schemas/auth.py` líneas 6-13: `LoginRequest` exige `tenant_id: UUID`, con comentario explícito: "tenant_id explícito porque 'email' solo es único por tenant".
- `backend/app/api/auth.py` función `login` (líneas 12-33): abre la sesión RLS con `abrir_sesion_tenant(payload.tenant_id)` (línea 21) y filtra `Usuario` por `tenant_id == payload.tenant_id` (línea 24) — el `tenant_id` que llega en el request es la única fuente de verdad para abrir la sesión, sin resolverlo de ningún otro lado.
- `docs/backend-schema.md` sección `tenant` (líneas 21-29): columnas actuales `id` (uuid PK), `nombre` (text), `pais` (enum mx/uy), `created_at`; nota línea 29: "Sin RLS (es la tabla raíz que define el aislamiento, no tiene `tenant_id` propio)".
- `backend/app/models/tenant.py` líneas 12-20: el modelo ORM `Tenant` hoy solo mapea `id`, `nombre`, `pais`, `created_at` — coincide con el esquema documentado, sin columna adicional.
- Revisión de los 6 archivos de `backend/app/api/` (`auth.py`, `deps.py`, `diagnosticos.py`, `seguimiento.py`, `planes.py`, `tramites.py`) y de `backend/app/main.py` (líneas 3, 7-11): ningún router expone nada de la tabla `tenant`; los routers existentes se registran con `app.include_router(<módulo>.router)`, cada uno con `router = APIRouter(prefix="/api/...", tags=[...])` definido en su propio archivo (patrón confirmado en `backend/app/api/auth.py` línea 9 y `backend/app/api/tramites.py` línea 13).
- `backend/app/api/deps.py` líneas 24-42: los endpoints autenticados dependen de `get_current_token` (decodifica JWT vía `HTTPBearer`, líneas 24-37) y `get_db` (abre sesión con RLS ya fijado, líneas 40-42) como dependencias de FastAPI *por función*, no a nivel de router — así es como hoy `login` (que no usa ninguna de las dos) puede ser público mientras el resto de los endpoints de `tramites.py` sí las usan (ver `backend/app/api/tramites.py` líneas 16-19, 32-35, 44-47).
- `docs/app-flow.md` línea 16 (nav superior): "nombre del gobierno local (tenant, texto plano — nunca un selector visible, ver `docs/ux-brief.md` pantalla 1)" — debe reaparecer en toda pantalla con sesión (`docs/app-flow.md` líneas 11-14: rutas `/`, `/tramites/:tramiteId/diagnostico`, `/tramites/:tramiteId/plan`, `/seguimiento`, todas "Requiere sesión").
- `docs/app-flow.md` línea 64 ("Multi-tenant"): "un funcionario pertenece a un tenant... si en el futuro un usuario necesita acceso a más de uno, es un caso fuera del alcance del MVP" — confirma que el "selector" de la línea 63 de `docs/ux-brief.md` es una previsión para el futuro, no el mecanismo principal de identificación que hay que resolver ahora.
- `backend/app/core/security.py` función `create_access_token` (líneas 24-32): claim actual `{sub: usuario_id, tenant_id, rol, exp}` (armado en líneas 26-31) — sin nombre de gobierno.
- `docs/backend-schema.md` línea 115: "vida corta (sugerido 8h, una jornada laboral) sin refresh token en el MVP".
- `docs/backend-schema.md` líneas 117-119 (sección "Migraciones"): "Alembic, una migración por cambio de esquema, nunca migraciones que alteren datos de `diagnostico_tramite`/`plan_modernizacion` ya persistidos".
- `backend/alembic/versions/0001_initial_schema.py`: única migración existente hoy (revision `"0001"`, línea 14), crea `tenant` sin columna `clave` (líneas 32-37) y dos ejemplos de `UniqueConstraint` sin índice explícito adicional: `uq_usuario_tenant_email` (línea 48) y `uq_tramite_tenant_nombre` (línea 73) — Postgres crea el índice único implícito por sí solo, patrón que se reutiliza abajo.
- `frontend/src/pages/LoginPage.tsx` líneas 9-15 y 44-53: el campo ya está etiquetado "Clave del gobierno" (línea 44) y se envía tal cual como `tenant_id` (línea 36: `tenant_id: claveGobierno.trim()`), lo cual hoy solo "funciona" si el funcionario pega el UUID crudo — el comentario de líneas 9-15 ya reconoce esto como parche temporal.
- `frontend/src/lib/session.ts` líneas 1-6, 35-38, 49-52: `guardarSesion` recibe un `nombreAMostrar` de texto libre (línea 35) que la propia UI le pide al funcionario escribir a mano (`LoginPage.tsx` líneas 70-80); el comentario de líneas 3-6 dice explícitamente: "El JWT no trae el nombre del gobierno local (ver limitación conocida de F1 documentada en el reporte de entrega) — por eso 'displayName' es un campo de texto libre que el propio funcionario escribe en el login".

## 1. Mecanismo de identificación elegido

**Decisión: opción (a) — una `clave` corta y legible por gobierno, agregada como columna nueva a `tenant`, que el funcionario escribe en un solo campo de texto en vez del UUID.** Se descarta la opción (b) (endpoint público que lista gobiernos por nombre/país para elegir de una lista).

Justificación contra `docs/ux-brief.md` sección "Principios de diseño":

- **Principio 1, línea 8** ("Sin jerga técnica... sin distractores" — la palabra "distractores" aparece explícitamente también en línea 63, "Sin branding de terceros, sin distractores"): un campo de texto único, del mismo tipo que ya existe hoy en `LoginPage.tsx` línea 44 ("Clave del gobierno"), no agrega ningún elemento visual nuevo a la pantalla — solo hace que ese campo, que ya existía como parche, resuelva correctamente contra el backend. Una lista para elegir es, por definición, un elemento adicional en pantalla (una lista/buscador) antes de llegar a las credenciales — más "distractor", no menos, frente a un mandato explícito de pantalla "mínima" (línea 63: "Pantalla mínima").
- **Exposición pública innecesaria.** Un endpoint que lista gobiernos por nombre/país expondría sin autenticación el nombre completo de todos los gobiernos que usan DiagMuni a cualquier tráfico anónimo — no es una fuga catastrófica (el nombre de un municipio no es secreto), pero es una superficie de exposición que la opción (a) no necesita: con la `clave` el funcionario debe ya conocer el identificador de su propio gobierno (se lo entrega su propio gobierno al darlo de alta, igual que hoy se le entrega su correo y contraseña), y el endpoint de resolución nunca lista nada, solo confirma una `clave` puntual ya escrita.
- **No escala como "distractor" cuando crezca el número de gobiernos.** El MVP es un piloto con pocos gobiernos (`docs/PRD.md`, alcance MVP), pero una lista pública de gobiernos es una función que degrada (necesita buscador, paginación) exactamente cuando el proyecto tenga éxito y se sume más de un gobierno por país — la `clave` de texto no tiene ese problema, es plana sin importar cuántos gobiernos existan.
- **Consistencia con lo ya construido.** El parche de F1 (`frontend/src/pages/LoginPage.tsx` línea 44, `frontend/src/lib/session.ts` líneas 3-6) ya anticipó este mecanismo con la etiqueta "Clave del gobierno" y ya documentó como limitación conocida que falta resolverlo contra el backend — la opción (a) es la que hace verdadero ese texto ya escrito, sin necesidad de rediseñar el campo. Esto es una observación de consistencia práctica, no el argumento principal (el argumento principal es el de principios de diseño arriba).

**Sin diferencia MX/UY en este mecanismo.** La `clave` y el endpoint de resolución aplican igual a ambos países — la columna `pais` de `tenant` (`docs/backend-schema.md` línea 26) sigue existiendo sin cambios y sigue siendo la que determina la capa de parámetros normativos; la identificación del tenant en el login es un problema de UX/autenticación, no un problema normativo, así que no hay parametrización por país que declarar aquí.

## 2. Impacto de esquema — columna `tenant.clave`

Columna nueva en `tenant`:

| Columna | Tipo | Notas |
|---|---|---|
| `clave` | `text` | Identificador corto y legible del gobierno (ej. `canelones`, `morelia`), único, escrito y normalizado en minúsculas antes de guardar/comparar (`trim()` + `lower()`), sin agregar la extensión `citext` de Postgres — normalización en capa de aplicación, no en el motor de base de datos, para no sumar una dependencia nueva. `NOT NULL` tras el backfill (ver migración abajo). Restricción `UNIQUE` global (no por país — el campo de login no pregunta país antes de la clave, así que la unicidad debe ser global; si dos gobiernos de países distintos eligieran el mismo nombre de base, el equipo que da de alta el tenant debe elegir una variante, ej. sufijo de país, como convención operativa, no como regla de esquema). |

No se agrega ninguna columna a `usuario`, `tramite`, `diagnostico_tramite`, `plan_modernizacion`, `accion_seguimiento` ni `job` — cambio acotado a `tenant`.

**Migración `0002`** (Alembic, `revision = "0002"`, `down_revision = "0001"`, siguiendo el patrón de cabecera de `backend/alembic/versions/0001_initial_schema.py` líneas 1-17), aditiva, en tres pasos dentro de `upgrade()` (necesarios porque `tenant` puede ya tener filas del piloto — `docs/backend-schema.md` líneas 117-119 exige que la migración no altere datos ya persistidos, y aquí el equivalente es no dejar ninguna fila de `tenant` en un estado roto):

1. `op.add_column("tenant", sa.Column("clave", sa.String(), nullable=True))` — nullable primero, porque agregar una columna `NOT NULL` a una tabla con filas existentes sin valor por defecto rompe la migración.
2. Backfill de las filas ya existentes: `op.execute(...)` con una actualización tipo `UPDATE tenant SET clave = lower(regexp_replace(regexp_replace(trim(nombre), '[^a-zA-Z0-9]+', '-', 'g'), '-+$', '')) WHERE clave IS NULL;` — genera una clave provisional a partir de `nombre` para cualquier tenant ya sembrado del piloto. Si dos tenants existentes generan la misma clave provisional (colisión improbable con pocos gobiernos en un piloto), es una corrección manual de datos antes de continuar (un `UPDATE` puntual de quien opera la migración), no una regla que la migración deba automatizar con sufijos.
3. `op.alter_column("tenant", "clave", nullable=False)` seguido de `op.create_unique_constraint("uq_tenant_clave", "tenant", ["clave"])` — mismo patrón que `uq_usuario_tenant_email` y `uq_tramite_tenant_nombre` en `0001_initial_schema.py` (líneas 48 y 73): la restricción `UNIQUE` ya crea su índice único implícito, sin necesitar un `op.create_index` adicional.

`downgrade()` simétrico: `op.drop_constraint("uq_tenant_clave", "tenant")` y `op.drop_column("tenant", "clave")`.

El modelo ORM `backend/app/models/tenant.py` (hoy líneas 12-20) necesita el campo `clave: Mapped[str] = mapped_column(String, nullable=False, unique=True)` agregado en la implementación de F2 — no se edita en este entregable de diseño, solo se especifica.

## 3. Contrato del endpoint nuevo

**Ruta:** `GET /api/gobiernos/{clave}` — nuevo router `backend/app/api/gobiernos.py` (a implementar en F2), registrado en `backend/app/main.py` con el mismo patrón que los routers existentes (línea 3: import; líneas 7-11: `app.include_router(...)`), agregando `from app.api import gobiernos` y `app.include_router(gobiernos.router)`.

**Público (sin JWT).** No depende de `get_current_token` ni `get_db` de `backend/app/api/deps.py` (líneas 24-42) — mismo estatus que `POST /api/auth/login` hoy (`backend/app/api/auth.py`, función `login`, sin ninguna de esas dos dependencias), porque su único propósito es ayudar a completar el `tenant_id` que el login va a necesitar; nunca devuelve nada sensible (nunca un `password_hash`, nunca datos de `usuario`).

**Request:** parámetro de ruta `clave` (string). El backend normaliza (`trim()` + `lower()`) antes de comparar contra la columna `tenant.clave` ya normalizada — así el funcionario puede escribir con mayúsculas o espacios sin que falle la búsqueda por eso.

**Response 200** (esquema nuevo, ej. `backend/app/schemas/gobierno.py`, mismo patrón de ubicación que `backend/app/schemas/auth.py`):
```
{
  "tenant_id": "<uuid>",
  "nombre": "<string>"
}
```
Solo lo necesario para el paso siguiente del flujo: `tenant_id` para armar el `LoginRequest` real (`backend/app/schemas/auth.py` líneas 6-13, sin tocar ese contrato), y `nombre` para que la pantalla confirme al funcionario a qué gobierno está a punto de entrar antes de pedirle contraseña.

**Response 404** si ninguna `clave` normalizada coincide: `HTTPException` con `detail` en lenguaje llano (mismo patrón que `backend/app/api/auth.py` línea 31, `"Las credenciales no coinciden"`) — la redacción exacta del texto queda para la implementación de F2 siguiendo el principio de `docs/ux-brief.md` línea 63 ("Mensaje de error en lenguaje llano... nunca un código de error técnico"), este documento solo fija que el código de estado es 404 y el cuerpo sigue el mismo shape `{"detail": "..."}` que ya usa FastAPI en el resto del backend.

**Conexión con el flujo de `POST /api/auth/login` (sin romper su contrato actual):**
1. El funcionario escribe su `clave` en el único campo de identificación de gobierno.
2. El frontend llama `GET /api/gobiernos/{clave}`.
3. Si 404: error en lenguaje llano en el mismo campo, el funcionario corrige la clave — los campos de correo/contraseña todavía no se muestran o quedan deshabilitados (decisión de interacción, no de layout: no se revela el resto del formulario hasta tener un gobierno confirmado, evitando que alguien envíe credenciales contra un `tenant_id` inexistente).
4. Si 200: el frontend guarda el `tenant_id` y el `nombre` recibidos (nunca el `tenant_id` que el funcionario haya podido escribir a mano, porque nunca lo escribe — solo escribe la `clave`), y muestra el `nombre` como confirmación antes de revelar los campos de correo y contraseña.
5. Al enviar el formulario, el frontend llama `POST /api/auth/login` con el `tenant_id` ya resuelto en el paso 4 + `email` + `password` — el `LoginRequest` (`backend/app/schemas/auth.py` líneas 6-13) no cambia en absoluto: sigue recibiendo `tenant_id: UUID`, `email: str`, `password: str`, solo que ahora el `tenant_id` lo puso el frontend a partir de una respuesta de backend, nunca de un campo que el funcionario haya tecleado directamente.

Nota para la implementación de F2: dado que el endpoint es público y sin autenticación, aplicar rate-limiting básico (ej. por IP) igual que en `POST /api/auth/login`, para mitigar enumeración de `clave` por fuerza bruta.

## 4. Cómo se resuelve el nombre del gobierno después del login, para la nav

**Decisión: el nombre viaja en el JWT, como un claim nuevo `nombre_gobierno`.** El claim pasa de `{sub, tenant_id, rol, exp}` (`backend/app/core/security.py` líneas 26-31) a `{sub, tenant_id, nombre_gobierno, rol, exp}`. Esto implica que `create_access_token` (misma función, líneas 24-32) reciba un parámetro adicional, y que `login` en `backend/app/api/auth.py` (líneas 12-33) obtenga el `nombre` del `Tenant` correspondiente antes de llamar a `create_access_token` — ya sea con un `db.get(Tenant, payload.tenant_id)` adicional o un join con `Usuario` en la misma consulta de la línea 23-25. Ninguno de estos cambios se implementa en este documento — quedan especificados para la tarea de código de F2.

Justificación frente a la alternativa (llamada autenticada aparte, ej. un endpoint `GET /api/gobiernos/actual` que resuelva el nombre del tenant del usuario en sesión):

- **Costo marginal por pantalla.** La nav aparece en las 4 rutas con sesión (`docs/app-flow.md` línea 11) — una llamada aparte significa una petición de red adicional en cada carga de la SPA, con su propio estado de carga (¿qué muestra la nav mientras esa llamada resuelve? ¿un parpadeo, un texto genérico?) solo para un dato que no cambia durante la sesión. El JWT ya se decodifica del lado del cliente hoy sin llamada de red (`frontend/src/lib/session.ts` función `decodeJwtClaims`, líneas 20-33, usada por `sesionValida`, líneas 57-64) — agregar `nombre_gobierno` al mismo claim aprovecha exactamente ese mecanismo ya existente, sin sumar una petición.
- **El nombre del gobierno es, en la práctica, estático dentro de una sesión.** No existe hoy ningún endpoint de administración que permita renombrar un `tenant` (`docs/backend-schema.md`, tabla `tenant`, líneas 21-29, sin mención de un endpoint de edición; confirmado también por la revisión de los 6 archivos de `backend/app/api/` en la sección 0 de este documento) — es un dato de referencia sembrado por quien opera la plataforma, no algo que cambie durante la jornada de un funcionario. El riesgo de que el nombre quede "stale" en un JWT ya emitido solo existiría si alguien renombrara el tenant a mitad de una sesión activa, y aun en ese caso el JWT expira en el máximo de 8 horas ya fijado (`docs/backend-schema.md` línea 115) — ventana de staleness aceptable para un dato que hoy ni siquiera es editable.
- **Tamaño del JWT.** Un nombre de gobierno (texto corto, ej. "Intendencia de Canelones") agrega unas pocas decenas de bytes al token — insignificante frente al límite práctico de tamaño de un JWT en un header HTTP, y consistente con que el propio claim ya lleva otros campos de texto (`rol`).

## 5. Actualización de `docs/ux-brief.md`

Se edita únicamente la sección "1. Selección de gobierno (tenant) e ingreso" (antes en la línea 62-63 del archivo), reemplazando el texto que daba por sentado el mecanismo sin explicarlo por una descripción que remite a este documento para el detalle completo — mismo patrón que la línea 71 de ese archivo cita `entregables/fase-2/asistente-captura-f1.md` para el detalle del asistente de captura. No se toca ninguna otra sección del archivo (ni "2. Panel resumen", ni el resto).

## 6. Resumen de archivos entregados

- `entregables/fase-2/identificacion-gobierno-login.md` (nuevo) — este documento.
- `docs/ux-brief.md` (editado) — sección "1. Selección de gobierno (tenant) e ingreso" actualizada para describir el campo "Clave del gobierno" y su resolución contra el backend, citando este documento para el mecanismo completo.

Ningún archivo de `frontend/` ni `backend/` fue modificado — quedan como especificación para la tarea de código de F2.
