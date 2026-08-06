# Plan de implementación — E1-bis: wiring real de la ruta local (phi3/Ollama) en la Capa IA

Versión 1 · 5 de agosto de 2026. Producido por el coordinador (corriendo sobre el modelo Fable), por instrucción directa del usuario, para cerrar una brecha de alcance detectada en conversación directa — no una disputa de auditoría sin converger. Extiende E1 (`docs/plan-implementacion.md`, Fase E), no es una fase nueva; sigue el precedente de nomenclatura "-bis" de `sesiones/2026-07-31-e2bis-fallback-fable-f3.md`.

Este documento es **solo planeación**. Ninguna de las tareas que describe se ha ejecutado todavía. No pasa por el auditor en sí mismo (es planeación, no código); cualquier tarea de código que aquí se defina sí deberá pasar por el loop normal de auditoría (`.claude/README.md`: máx. 2 iteraciones, luego escalar a Mario Alberto Quintana) cuando se ejecute.

## 0. La brecha exacta (verificada contra código real, no especulación)

`docs/stack-tecnologico.md` líneas 31 y 80-109 (sección "Nota sobre la Capa IA — modelo local evaluado, no elegido como default") documentan un benchmark real de 5 modelos LLM locales corrido en un iMac Intel Core i5-4570 (proxy pesimista de un VPS económico) y afirman que el ganador, phi3/Phi-3-mini (MIT), "queda disponible como alternativa vía cambio de configuración de LiteLLM, sin tocar `engine/` ni el resto del backend, si el criterio cambia en el futuro". Verificado hoy contra el código real de `feature/frontend`:

- `backend/app/ia/litellm_config.yaml` solo define 3 rutas: `economico` (deepseek/deepseek-chat), `calidad` (anthropic/claude-sonnet-4-5), `calidad_respaldo` (anthropic/claude-fable-5). Ninguna ruta local/Ollama.
- `backend/app/core/config.py` línea 21 declara `ollama_api_base: str | None = None`, pero ningún módulo de `backend/app/ia/` (`config.py`, `generador_plan.py`, `verificador.py`, `asistente_captura.py`) lo lee — campo muerto.
- `.env.example` documenta `OLLAMA_API_BASE=` como si fuera funcional; no lo es.
- `backend/tests/test_ia_config.py` solo cubre las 3 rutas API; cero cobertura de una ruta local.
- Ollama no está instalado en ningún entorno de desarrollo activo hoy (Windows); el benchmark original se corrió en otro equipo (iMac), hace varios días, y nunca se ha vuelto a correr ni validar contra el código de esta rama.

La decisión de arquitectura (phi3 como candidato local, DeepSeek+Claude como default de producción) es real y está bien fundamentada — lo falso es la frase "disponible vía cambio de configuración": es aspiracional, no construido.

## 1. Decisiones de diseño

### 1.1 Nombre de la ruta: `local` (no `phi3` ni `ollama`)

Consistente con la convención ya establecida en `litellm_config.yaml` (`economico`, `calidad`, `calidad_respaldo`: nombres por **rol**, no por proveedor/modelo). Si el candidato local cambiara en el futuro (otro modelo MIT/Apache, otra versión de phi3), el nombre de la ruta no cambia — ni el código de `generador_plan.py` ni los tests ni la documentación necesitan renombrarse.

### 1.2 Disponibilidad sin API key: generalizar, no duplicar

Ollama no usa API key, usa una URL base (`OLLAMA_API_BASE`). Dos caminos posibles:
- (a) función paralela `esta_disponible_local()` específica, o
- (b) generalizar `esta_disponible()` para que despache según qué campo tenga la ruta.

**Decisión: (b).** Se generaliza `RutaLLM` (`backend/app/ia/config.py`) con dos campos opcionales y mutuamente excluyentes: `env_var_api_key: str | None` (como hoy) y `env_var_api_base: str | None` (nuevo). `esta_disponible(nombre_ruta, cfg=None)` sigue siendo la única función que llaman `generador_plan.py`/`verificador.py`/`asistente_captura.py`, sin que el llamador necesite saber si esa ruta usa key o base URL — internamente decide cuál de las dos comprobar según cuál campo tenga poblado la `RutaLLM`. Se agrega `api_base_de(ruta, cfg=None) -> str | None`, mismo contrato que `api_key_de()` (None si la variable está ausente o vacía). Justificación: mantiene un único punto de entrada booleano ya usado en 3 módulos de `ia/`, en vez de forzar a cada llamador a saber qué mecanismo de disponibilidad usar por ruta — más alineado con el principio de "una sola capa de abstracción" ya declarado en `docs/TRD.md`.

Validación de carga (`cargar_model_list()`): si una entrada del YAML no declara ni `api_key` ni `api_base`, o declara ambos, debe fallar fuerte con un `ValueError` explícito al cargar — error de configuración real, mismo criterio que el `KeyError` ya existente de `obtener_ruta()` para una ruta inexistente.

### 1.3 Timeout por ruta: config-driven, no hardcodeado por nombre

El benchmark real (`docs/stack-tecnologico.md` línea 92) midió **~123 segundos** de generación para phi3 en CPU sin GPU. El `TIMEOUT_SEGUNDOS = 30` global de `generador_plan.py` mataría cualquier llamada a la ruta local antes de que termine — este es exactamente el tipo de bug que un ciclo de solo-mocks no detectaría (ver sección 3, T2).

**Decisión:** agregar un campo opcional `timeout_segundos` a cada entrada de `litellm_config.yaml` (default `30` si se omite — retrocompatible con las 3 rutas ya existentes, que no necesitan declararlo). La ruta `local` declara explícitamente `timeout_segundos: 180` (margen sobre los 123s medidos). `RutaLLM.timeout_segundos: int = 30`; `_intentar_narrativa_via_ruta` usa `ruta.timeout_segundos` en vez de la constante global. Config-driven, igual que el catálogo de reglas normativas (`engine/reglas/*.yaml`) — nunca un `if nombre_ruta == "local": timeout = 180` hardcodeado en Python.

### 1.4 Política de selección — responde la pregunta central del encargo

El encargo plantea dos alternativas: (i) la ruta local como tercer nivel de fallback automático después de `calidad`/`calidad_respaldo`, o (ii) una alternativa manual todo-o-nada que reemplaza qué ruta usa el generador.

**Decisión: una sola cadena de fallback sirve ambos casos, gobernada enteramente por qué variables de entorno están pobladas — sin agregar un flag booleano nuevo ni una rama de código distinta.**

Cadena dentro de `_narrativa_llm` (`generador_plan.py`): **Sonnet (`calidad`) → Fable (`calidad_respaldo`) → local (phi3) → plantilla determinista.**

- Si `ANTHROPIC_API_KEY` está poblada: comportamiento actual sin cambio — Sonnet y Fable se intentan primero. `local` solo entra como tercera red de contención si ambas fallan (timeout, red, respuesta vacía). Esto cubre el escenario "sin conexión a internet" u "outage de la API" citado en `docs/stack-tecnologico.md` línea 82, sin que el operador toque nada.
- Si `ANTHROPIC_API_KEY` **no** está poblada (se retira deliberadamente — presupuesto de API o política de datos) pero `OLLAMA_API_BASE` sí: Sonnet/Fable se saltan sin intento (mismo guard `esta_disponible` ya usado hoy, sin llamada que sabemos fallará) y `local` se intenta directo. Esto **es** el "todo-o-nada por configuración" que pide `docs/stack-tecnologico.md` línea 82 ("disponible... vía cambio de configuración de LiteLLM, sin tocar `engine/` ni el resto del backend"): apagar dos variables de entorno y encender una tercera basta — cero cambio de código.
- Si ninguna de las tres rutas está disponible: plantilla determinista, comportamiento ya existente, sin cambio.

Pseudocódigo ilustrativo de la forma esperada (no código final — el especialista decide la implementación exacta):

```python
def _narrativa_llm(accion: AccionPais) -> str:
    if esta_disponible(_RUTA_LLM):          # calidad / calidad_respaldo comparten key
        try:
            return _intentar_narrativa_via_ruta(_RUTA_LLM, accion)
        except Exception:
            pass
        try:
            return _intentar_narrativa_via_ruta(_RUTA_LLM_RESPALDO, accion)
        except Exception:
            pass
    if esta_disponible(_RUTA_LLM_LOCAL):
        try:
            return _intentar_narrativa_via_ruta(_RUTA_LLM_LOCAL, accion)
        except Exception:
            pass
    return _narrativa_plantilla(accion)
```

El gate de nivel superior en `generar_contenido_llm` (hoy `if esta_disponible(_RUTA_LLM): ... else: plantilla`) debe generalizarse a `if esta_disponible(_RUTA_LLM) or esta_disponible(_RUTA_LLM_LOCAL): ... else: plantilla` — de lo contrario, con las API keys ausentes y solo Ollama configurado, el código saltaría directo a plantilla sin intentar `local` siquiera.

`_intentar_narrativa_via_ruta` debe generalizarse para pasar `api_key=` o `api_base=` a `litellm.completion(...)` según cuál campo tenga la `RutaLLM` (ver 1.2) y usar `ruta.timeout_segundos` (ver 1.3) en vez de la constante fija.

### 1.5 Alcance: solo F3, no F1/F9

El benchmark de phi3 se hizo contra el prompt de F3 ("Firma electrónica"). Este plan solo agrega `local` a la cadena de `generador_plan.py` (F3). F1 (`asistente_captura.py`) y F9 (`verificador.py`) siguen usando únicamente `economico` (DeepSeek), sin alternativa local — extenderlo ahí queda fuera de alcance explícito de E1-bis, anotado como posible pendiente futuro si se quisiera simetría completa. No se inventa alcance no pedido.

## 2. Tabla de tareas — dependencias y bloqueos

| # | Tarea | Depende de | Bloquea | Especialista | Estado |
|---|---|---|---|---|---|
| E1bis-1 | Wiring de código: ruta `local` en `litellm_config.yaml`; generalizar `RutaLLM`/`esta_disponible()`/nuevo `api_base_de()`/`timeout_segundos` en `app/ia/config.py`; cadena de fallback Sonnet→Fable→local→plantilla en `generador_plan.py` (gate de nivel superior incluido); tests unitarios con mocks en `test_ia_config.py` y `test_generador_plan.py` (sin Ollama real todavía) | Ninguna (extiende E1/E2, ya aprobadas) | E1bis-2 | ia-automatizacion | Pendiente de asignar |
| E1bis-2 | Instalación real de Ollama + `ollama pull phi3` en un entorno de desarrollo verificable; test de integración real con guard `skipif` (`backend/tests/test_generador_plan_ollama_real.py`), sin mocks, generando una narrativa real vía la ruta `local` | E1bis-1 | E1bis-3, E1bis-4 | ia-automatizacion | Pendiente |
| E1bis-3 | Documentación: corregir `docs/stack-tecnologico.md` (líneas 31 y 80-109) y `entregables/fase-2/dimensionamiento-costos.md` (línea 9) para no describir el wiring como hecho mientras no lo esté; actualizar `.env.example`; decidir si amerita fila en `docs/plan-implementacion.md` (ver 3.3) | E1bis-2 (para la versión final con latencia real medida) — la corrección interina `[PENDIENTE]` puede adelantarse en paralelo con E1bis-1 | E1bis-4 | ia-automatizacion | Pendiente |
| E1bis-4 | Auditoría conjunta de E1bis-1 + E1bis-2 + E1bis-3 como un solo entregable (mismo patrón que E2-bis: código + YAML + docs + tests, un solo ciclo) | E1bis-3 | Cierre de E1-bis | auditor | Pendiente |
| E1bis-5 (opcional, no bloqueante) | Revalidar `entregables/fase-2/dimensionamiento-costos.md` sección 6 ("rango conservador, no una medición") con la latencia real medida en E1bis-2 | E1bis-2 | Ninguna — mejora, no bloquea el cierre de E1-bis | infraestructura-costos | Pendiente, opcional |

**Paralelismo real disponible:** dentro de este alcance acotado, la mayoría de las tareas son secuenciales (E1bis-2 necesita el código de E1bis-1; la versión final de E1bis-3 necesita la latencia real de E1bis-2; la auditoría necesita las tres). El único paralelismo legítimo es **E1bis-5 junto con E1bis-4**: ambas dependen solo de E1bis-2, no comparten archivos, y E1bis-5 no bloquea el cierre de E1-bis — pueden despacharse en el mismo momento a `infraestructura-costos` y `auditor` respectivamente.

## 3. Detalle de cada tarea

### 3.1 E1bis-1 — Wiring de código

**Archivos:** `backend/app/ia/litellm_config.yaml`, `backend/app/ia/config.py`, `backend/app/ia/generador_plan.py`, `backend/tests/test_ia_config.py`, `backend/tests/test_generador_plan.py`.

**Contrato duro a preservar sin excepción** (mismo que E1-E4/E2-bis):
- `_narrativa_llm` nunca lanza una excepción hacia quien llama — cualquier fallo de las 3 rutas LLM cae en `_narrativa_plantilla`.
- `ia/` nunca importa de `engine/` en sentido inverso.
- Sin narrativa de proceso (fechas, nombres de agente, historial de auditoría) en comentarios/docstrings — eso vive en `entregables/plan.md`/`sesiones/`.
- Nomenclatura en español, consistente con el resto del módulo.
- No tocar `verificador.py`, `plan_job.py`, `engine/`, frontend, ni el watchdog de jobs (fuera de alcance, ver 1.5).
- Sin dependencias nuevas en `requirements.txt`: LiteLLM ya soporta el provider `ollama`/`ollama_chat` de forma nativa (sin paquete adicional) — el especialista debe **verificar contra la documentación vigente de LiteLLM (WebSearch)** cuál prefijo de modelo usar exactamente (`ollama/phi3` vs. `ollama_chat/phi3`) antes de escribir el YAML, no asumir de memoria. Esto es exactamente el mismo estándar de verificación que ya se aplicó a la nota de licencia de LiteLLM en `docs/stack-tecnologico.md` y al incidente de seguridad de marzo 2026 citado en la nota de procedencia de E2 (`entregables/plan.md`).

**Especificación YAML propuesta** (ilustrativa, a confirmar el prefijo exacto del modelo vía WebSearch antes de fijarla):

```yaml
  - model_name: local
    litellm_params:
      model: ollama/phi3          # confirmar prefijo exacto (ollama/ vs ollama_chat/) contra docs vigentes de LiteLLM
      api_base: os.environ/OLLAMA_API_BASE
      timeout_segundos: 180       # ver decisión 1.3 — margen sobre los ~123s medidos en el benchmark
```

**Tests unitarios exigidos (mocks, sin Ollama real todavía):**
- `test_ia_config.py`: la ruta `local` carga con `env_var_api_base == "OLLAMA_API_BASE"` y `env_var_api_key is None`; `esta_disponible("local")` es `True`/`False` según `ollama_api_base` esté poblado/vacío/ausente en `Settings` (mismo patrón que los tests ya existentes para `economico`/`calidad`); una entrada de YAML sin `api_key` ni `api_base` (o con ambos) falla fuerte al cargar, no en silencio.
- `test_generador_plan.py`: (a) Sonnet y Fable fallan, `local` disponible y responde → se usa esa narrativa; (b) `ANTHROPIC_API_KEY` ausente, `OLLAMA_API_BASE` presente → se intenta `local` directo, sin intentar Sonnet/Fable (espía que confirma que esas dos rutas nunca se llaman); (c) las 3 rutas fallan o ninguna está disponible → cae a plantilla, sin excepción; (d) la llamada a `local` usa el `timeout_segundos` declarado en el YAML (180), distinto del default de las otras rutas (30) — regresión específica contra el riesgo señalado en 1.3.

### 3.2 E1bis-2 — Instalación real + prueba de integración real (sin mocks)

**Justificación de por qué no basta con mocks:** ya hubo un incidente en este proyecto (`sesiones/2026-08-05-hotfix-rls-seguimiento.md`) de un bug real que un ciclo de solo-mocks no detectó porque el mock verificaba el orden de las llamadas, no el comportamiento real de la infraestructura subyacente. El riesgo concreto aquí es el mismo tipo de bug: un timeout mal configurado (sección 1.3) pasaría cualquier test con mocks (que no esperan 123 segundos reales) y solo se manifestaría contra un Ollama real.

**Pasos:**
1. Instalar Ollama en un entorno de desarrollo verificable (instalador oficial de Windows, o `winget install Ollama.Ollama`, dado que la máquina de desarrollo activa hoy es Windows). **Riesgo operativo declarado:** si el sandbox del agente que ejecute esta tarea no tiene permisos de instalación de software o acceso de red saliente, este paso específico (no la construcción de código) debe escalarse a ejecución manual del usuario/coordinador, y el agente retoma solo para correr los tests una vez confirmado que `ollama` responde.
2. `ollama pull phi3` — mismo modelo evaluado en el benchmark original.
3. Confirmar el servidor escuchando (`ollama list`, o `GET http://localhost:11434/api/tags`) antes de correr cualquier test contra él.
4. Configurar `OLLAMA_API_BASE=http://localhost:11434` en el `.env` real (no commiteado) del entorno de prueba.
5. Correr **dos escenarios reales distintos**, no uno solo:
   - (a) con `ANTHROPIC_API_KEY`/`DEEPSEEK_API_KEY` presentes: forzar un fallo simulado únicamente de Sonnet/Fable (mock acotado a esas dos llamadas, en ese test específico) y confirmar que `local` sí se invoca de verdad y produce una narrativa real.
   - (b) con `ANTHROPIC_API_KEY`/`DEEPSEEK_API_KEY` ausentes del entorno: confirmar que el camino "todo-o-nada por configuración" (1.4) llega a `local` directo, sin intento previo, y produce una narrativa real.
6. Nuevo archivo `backend/tests/test_generador_plan_ollama_real.py`: función `_ollama_real_disponible()` — chequeo de socket (`host`/`puerto` extraídos de `OLLAMA_API_BASE`) con timeout corto, mismo patrón exacto que `_postgres_real_disponible()` en `backend/tests/test_api_seguimiento.py` (líneas 99-115) — y, si es alcanzable, confirmar además que el modelo `phi3` está descargado (`GET /api/tags`) antes de intentar, para no confundir "Ollama no está" con "el modelo no está". Decorar el test real con `@pytest.mark.skipif(not _ollama_real_disponible(), reason="Requiere Ollama real alcanzable con OLLAMA_API_BASE configurado y el modelo phi3 descargado")` — se salta limpio en CI (que no provisiona Ollama, igual que no provisiona Postgres real hoy) sin fallar el pipeline.
7. El test real debe generar la narrativa de una brecha de prueba conocida (recomendado: "Firma electrónica", el mismo prompt del benchmark original en `docs/stack-tecnologico.md`, para poder comparar) y verificar: texto no vacío; el texto **no** es literalmente igual a la plantilla determinista de `_narrativa_plantilla` para esa acción (para confirmar que sí vino del LLM y no cayó en degradado por un fallo silencioso); tiempo total dentro de un margen razonable (ej. menor a 200s, dejando margen sobre los 180s del timeout de la ruta).
8. Guardar el output literal de la corrida real (terminal) como evidencia adjunta al entregable — mismo estándar que las "Verificación mecánica independiente" ya usadas en el proyecto (`entregables/plan.md`, secciones de E2/E4/E2-bis).

### 3.3 E1bis-3 — Documentación

- **`docs/stack-tecnologico.md`:** mientras E1bis-1/E1bis-2 no estén aprobadas, reemplazar la frase aspiracional de la línea 82 ("queda disponible como alternativa vía cambio de configuración de LiteLLM... si el criterio cambia en el futuro") por una versión que distinga explícitamente evaluado/decidido de construido, con puntero a este documento — ej.: agregar tras esa frase: "**[PENDIENTE — 05-ago-2026]**: esta alternativa está evaluada y decidida pero *aún no wireada* en el código (`litellm_config.yaml` solo define hoy las 3 rutas API; `ollama_api_base` en `app/core/config.py` no está conectado a ningún módulo de `app/ia/`); el plan de implementación para cerrar esta brecha vive en `docs/plan-implementacion-e1-bis-capa-ia-local.md`." Igual tratamiento en la línea 31 (fila "Capa IA" de la tabla del stack) y en la línea 84 ("El diseño de LiteLLM... hace que este default sea reversible por configuración... no exige reescribir `ia/` ni `engine/`" — hoy tampoco verificable sin el wiring). Una vez E1bis-4 (auditoría) apruebe, esta nota se reemplaza por una que confirme "implementado, ver commit X" — no se elimina sin dejar rastro, se actualiza.
- **`entregables/fase-2/dimensionamiento-costos.md` línea 9:** misma frase aspiracional casi idéntica ("queda disponible como alternativa vía cambio de configuración de LiteLLM... útil si el criterio cambia en el futuro") — mismo tratamiento `[PENDIENTE]` con el mismo puntero.
- **`.env.example`:** agregar un comentario bajo `OLLAMA_API_BASE=` explicando el nuevo comportamiento real una vez implementado (ejemplo `http://localhost:11434`) y aclarando que dejarlo vacío preserva el comportamiento actual (solo rutas API, sin cambio para quien no lo use).
- **`docs/plan-implementacion.md`:** decidir explícitamente si amerita una fila nueva en la tabla de Fase E. **Precedente relevante:** E2-bis (extensión de alcance equivalente, mismo patrón "-bis") **no** tocó `docs/plan-implementacion.md` — quedó registrada solo en `entregables/plan.md`. Recomendación del coordinador: mantener esa misma consistencia (no agregar fila al documento canónico por un add-on de una sola sesión) salvo que el usuario indique lo contrario al ejecutar esta tarea; la trazabilidad ya queda cubierta por este documento nuevo y por la sección "E1-bis" de `entregables/plan.md`. Quien ejecute E1bis-3 debe registrar explícitamente cuál de las dos opciones tomó y por qué, sin asumir en silencio.

### 3.4 E1bis-4 — Auditoría

El auditor debe verificar como mínimo:
1. Los 3 puntos de disponibilidad/timeout (1.2/1.3) implementados exactamente como se decidió, sin bifurcación hardcodeada por nombre de ruta.
2. La cadena de fallback (1.4) trazada manualmente en los 4 caminos posibles (Sonnet ok; Sonnet falla+Fable ok; ambas fallan+local ok; las 3 fallan → plantilla) y en el camino "todo-o-nada" (solo `OLLAMA_API_BASE` poblado).
3. Contrato "nunca excepción hacia quien llama / nunca decide la acción" intacto en los 4 caminos.
4. Que la evidencia de E1bis-2 sea una corrida real, no solo declarativa — pedir el output literal si no viene adjunto, igual criterio que la verificación mecánica independiente ya usada en el proyecto.
5. Consistencia exacta de nombre de ruta/modelo/variable de entorno entre `litellm_config.yaml`, `config.py`, `generador_plan.py`, `docs/TRD.md` (si se actualiza) y la documentación corregida.
6. Sin scope creep a `verificador.py`/`plan_job.py`/`engine/`/frontend/F1/F9 (ver 1.5).
7. Sin narrativa de proceso en código.
8. Fidelidad de la corrección de `docs/stack-tecnologico.md`/`dimensionamiento-costos.md`/`.env.example` al alcance de 3.3.

Máximo 2 iteraciones. Si persiste desacuerdo entre especialista y auditor, el coordinador empaqueta ambas posturas y escala a Mario Alberto Quintana con un resumen de una cuartilla (qué se disputa, postura del especialista, postura del auditor, recomendación del coordinador) — sin implementar la resolución por cuenta propia.

## 4. Asignación de especialistas y orden

Toda la construcción/instalación (E1bis-1, E1bis-2) y la documentación (E1bis-3) a `ia-automatizacion`, por continuidad directa con quien construyó E1-E4/E2-bis y por no existir un especialista de IA dedicado distinto en el kit. `infraestructura-costos` entra únicamente en la tarea opcional E1bis-5. `auditor` cierra el loop (E1bis-4). Orden secuencial obligatorio E1bis-1 → E1bis-2 → E1bis-3 → E1bis-4, con E1bis-5 despachable en paralelo a E1bis-4 (ver tabla de la sección 2). Un especialista a la vez por entregable, conforme a la regla dura del coordinador.

## 5. Riesgos y supuestos abiertos

- Formato exacto del provider string de LiteLLM para Ollama (`ollama/phi3` vs. `ollama_chat/phi3`) no verificado en este plan — instruir al especialista a confirmarlo contra la documentación vigente de LiteLLM (WebSearch) antes de escribir el YAML, no asumir de memoria.
- Ollama no está instalado en ningún entorno de desarrollo activo hoy (Windows) — E1bis-2 depende de poder instalar software en el entorno de ejecución del agente o de una intervención manual del usuario; si el sandbox del agente no tiene permisos de instalación/red saliente, escalar la ejecución de ese paso específico (no la construcción de código) al usuario directamente.
- Este plan no extiende el fallback local a F1 (`asistente_captura.py`)/F9 (`verificador.py`) — ver 1.5.
- No se modifica el timeout de las rutas ya existentes (`economico`/`calidad`/`calidad_respaldo`) — el campo `timeout_segundos` es opcional y retrocompatible.
- CI (GitHub Actions) no provisiona Ollama, igual que no provisiona Postgres real hoy (`.github/workflows/ci.yml`) — el test de integración real de E1bis-2 se saltará limpio ahí por diseño; la verificación real depende de correrlo manualmente en un entorno con Ollama instalado, mismo estándar que ya rige para el test de Postgres real.

## 6. Documentos relacionados

`docs/stack-tecnologico.md`, `docs/TRD.md`, `docs/plan-implementacion.md`, `entregables/plan.md`, `entregables/fase-2/dimensionamiento-costos.md`, `backend/app/ia/config.py`, `backend/app/ia/litellm_config.yaml`, `backend/app/ia/generador_plan.py`, `backend/tests/test_ia_config.py`, `backend/tests/test_generador_plan.py`, `backend/tests/test_api_seguimiento.py` (patrón `skipif` de referencia, líneas 99-121), `sesiones/2026-07-31-e2bis-fallback-fable-f3.md` (precedente de nomenclatura "-bis"), `sesiones/2026-08-05-hotfix-rls-seguimiento.md` (precedente de por qué no basta con mocks).
