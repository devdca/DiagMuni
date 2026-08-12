# Plan de implementación — E1-bis: wiring real de la ruta local (phi3/Ollama) en la Capa IA

Versión 1 · 5 de agosto de 2026. Cierra una brecha detectada entre la documentación y el código: la alternativa de modelo local está documentada como disponible, pero no está construida. Extiende E1 (`docs/plan-implementacion.md`, Fase E), no es una fase nueva; la nomenclatura "-bis" señala una extensión acotada de una fase ya cerrada.

**Estado: E1bis-1 a E1bis-4 cerrados** (ver estado por tarea en la tabla de la sección 2 y la actualización de la sección 7) — el documento se conserva completo como registro de las decisiones de diseño y su justificación, no solo como planeación pendiente.

## 0. La brecha exacta (verificada contra código real, no especulación)

`docs/stack-tecnologico.md` líneas 31 y 80-109 (sección "Nota sobre la Capa IA — modelo local evaluado, no elegido como default") documentan un benchmark real de 5 modelos LLM locales corrido en un iMac Intel Core i5-4570 (proxy pesimista de un VPS económico) y afirman que el ganador, phi3/Phi-3-mini (MIT), "queda disponible como alternativa vía cambio de configuración de LiteLLM, sin tocar `engine/` ni el resto del backend, si el criterio cambia en el futuro". Verificado hoy contra el código real del repositorio:

- `backend/app/ia/litellm_config.yaml` solo define 3 rutas: `economico` (deepseek/deepseek-chat), `calidad` y `calidad_respaldo` (ambas modelos Claude vía API de Anthropic, ver el propio YAML). Ninguna ruta local/Ollama.
- `backend/app/core/config.py` línea 21 declara `ollama_api_base: str | None = None`, pero ningún módulo de `backend/app/ia/` (`config.py`, `generador_plan.py`, `verificador.py`, `asistente_captura.py`) lo lee — campo muerto.
- `.env.example` documenta `OLLAMA_API_BASE=` como si fuera funcional; no lo es.
- `backend/tests/test_ia_config.py` solo cubre las 3 rutas API; cero cobertura de una ruta local.
- Ollama no está instalado en ningún entorno de desarrollo activo hoy (Windows); el benchmark original se corrió en otro equipo (iMac), y nunca se ha vuelto a correr ni validar contra el código de esta rama.

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

### 1.4 Política de selección — fallback automático y modo todo-o-nada con una sola cadena

Hay dos alternativas de política: (i) la ruta local como tercer nivel de fallback automático después de `calidad`/`calidad_respaldo`, o (ii) una alternativa manual todo-o-nada que reemplaza qué ruta usa el generador.

**Decisión: una sola cadena de fallback sirve ambos casos, gobernada enteramente por qué variables de entorno están pobladas — sin agregar un flag booleano nuevo ni una rama de código distinta.**

Cadena dentro de `_narrativa_llm` (`generador_plan.py`): **`calidad` → `calidad_respaldo` → `local` (phi3) → plantilla determinista.**

- Si `ANTHROPIC_API_KEY` está poblada: comportamiento actual sin cambio — `calidad` y `calidad_respaldo` se intentan primero. `local` solo entra como tercera red de contención si ambas fallan (timeout, red, respuesta vacía). Esto cubre el escenario "sin conexión a internet" u "outage de la API" citado en `docs/stack-tecnologico.md` línea 82, sin que el operador toque nada.
- Si `ANTHROPIC_API_KEY` **no** está poblada (se retira deliberadamente — presupuesto de API o política de datos) pero `OLLAMA_API_BASE` sí: `calidad`/`calidad_respaldo` se saltan sin intento (mismo guard `esta_disponible` ya usado hoy, sin llamada que sabemos fallará) y `local` se intenta directo. Esto **es** el "todo-o-nada por configuración" que pide `docs/stack-tecnologico.md` línea 82 ("disponible... vía cambio de configuración de LiteLLM, sin tocar `engine/` ni el resto del backend"): apagar dos variables de entorno y encender una tercera basta — cero cambio de código.
- Si ninguna de las tres rutas está disponible: plantilla determinista, comportamiento ya existente, sin cambio.

Pseudocódigo ilustrativo de la forma esperada (no código final — la implementación decide la forma exacta):

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

El benchmark de phi3 se hizo contra el prompt de F3 ("Firma electrónica"). Este plan solo agrega `local` a la cadena de `generador_plan.py` (F3). F1 (`asistente_captura.py`) y F9 (`verificador.py`) siguen usando únicamente `economico` (DeepSeek), sin alternativa local — extenderlo ahí queda fuera de alcance explícito de E1-bis, anotado como posible pendiente futuro si se quisiera simetría completa.

## 2. Tabla de tareas — dependencias y bloqueos

| # | Tarea | Depende de | Bloquea | Estado |
|---|---|---|---|---|
| E1bis-1 | Wiring de código: ruta `local` en `litellm_config.yaml`; generalizar `RutaLLM`/`esta_disponible()`/nuevo `api_base_de()`/`timeout_segundos` en `app/ia/config.py`; cadena de fallback `calidad`→`calidad_respaldo`→`local`→plantilla en `generador_plan.py` (gate de nivel superior incluido); tests unitarios con mocks en `test_ia_config.py` y `test_generador_plan.py` (sin Ollama real todavía) | Ninguna (extiende E1/E2, ya cerradas) | E1bis-2 | Cerrado |
| E1bis-2 | Instalación real de Ollama + `ollama pull phi3` en un entorno de desarrollo verificable; test de integración real con guard `skipif` (`backend/tests/test_generador_plan_ollama_real.py`), sin mocks, generando una narrativa real vía la ruta `local` | E1bis-1 | E1bis-3, E1bis-4 | Cerrado — corrida real capturada en `docs/TRD.md` (76.38s y 57.8s contra Ollama real con `phi3` descargado) |
| E1bis-3 | Documentación: corregir `docs/stack-tecnologico.md` (líneas 31 y 80-109) y `entregables/fase-2/dimensionamiento-costos.md` (línea 9) para no describir el wiring como hecho mientras no lo esté; actualizar `.env.example`; decidir si amerita fila en `docs/plan-implementacion.md` (ver 3.3) | E1bis-2 (para la versión final con latencia real medida) — la corrección interina `[PENDIENTE]` puede adelantarse en paralelo con E1bis-1 | E1bis-4 | Cerrado |
| E1bis-4 | Revisión integral de E1bis-1 + E1bis-2 + E1bis-3 como un solo entregable (código + YAML + docs + tests, un solo ciclo de revisión) | E1bis-3 | Cierre de E1-bis | Cerrado |
| E1bis-5 (opcional, no bloqueante) | Revalidar `entregables/fase-2/dimensionamiento-costos.md` sección 6 ("rango conservador, no una medición") con la latencia real medida en E1bis-2 | E1bis-2 | Ninguna — mejora, no bloquea el cierre de E1-bis | Pendiente, opcional — la corrida real de E1bis-2 fue en un entorno de desarrollo, no en un VPS; la sección 6 sigue siendo una traducción conservadora, no una medición en el hardware de destino |

**Paralelismo real disponible:** dentro de este alcance acotado, la mayoría de las tareas son secuenciales (E1bis-2 necesita el código de E1bis-1; la versión final de E1bis-3 necesita la latencia real de E1bis-2; la revisión necesita las tres). El único paralelismo legítimo es **E1bis-5 junto con E1bis-4**: ambas dependen solo de E1bis-2, no comparten archivos, y E1bis-5 no bloquea el cierre de E1-bis — pueden ejecutarse en paralelo.

## 3. Detalle de cada tarea

### 3.1 E1bis-1 — Wiring de código

**Archivos:** `backend/app/ia/litellm_config.yaml`, `backend/app/ia/config.py`, `backend/app/ia/generador_plan.py`, `backend/tests/test_ia_config.py`, `backend/tests/test_generador_plan.py`.

**Contrato duro a preservar sin excepción** (mismo que rige toda la Fase E):
- `_narrativa_llm` nunca lanza una excepción hacia quien llama — cualquier fallo de las 3 rutas LLM cae en `_narrativa_plantilla`.
- `ia/` nunca importa de `engine/` en sentido inverso.
- Sin narrativa de proceso (fechas, historial de revisiones) en comentarios/docstrings — el código documenta comportamiento, no cronología.
- Nomenclatura en español, consistente con el resto del módulo.
- No tocar `verificador.py`, `plan_job.py`, `engine/`, frontend, ni el watchdog de jobs (fuera de alcance, ver 1.5).
- Sin dependencias nuevas en `requirements.txt`: LiteLLM ya soporta el provider `ollama`/`ollama_chat` de forma nativa (sin paquete adicional) — antes de escribir el YAML debe **verificarse contra la documentación vigente de LiteLLM** cuál prefijo de modelo usar exactamente (`ollama/phi3` vs. `ollama_chat/phi3`), no asumirlo de memoria; mismo estándar de verificación contra fuente primaria ya aplicado a la nota de licencia de LiteLLM en `docs/stack-tecnologico.md`.

**Especificación YAML propuesta** (ilustrativa, a confirmar el prefijo exacto del modelo contra la documentación vigente de LiteLLM antes de fijarla):

```yaml
  - model_name: local
    litellm_params:
      model: ollama/phi3          # confirmar prefijo exacto (ollama/ vs ollama_chat/) contra docs vigentes de LiteLLM
      api_base: os.environ/OLLAMA_API_BASE
      timeout_segundos: 180       # ver decisión 1.3 — margen sobre los ~123s medidos en el benchmark
```

**Tests unitarios exigidos (mocks, sin Ollama real todavía):**
- `test_ia_config.py`: la ruta `local` carga con `env_var_api_base == "OLLAMA_API_BASE"` y `env_var_api_key is None`; `esta_disponible("local")` es `True`/`False` según `ollama_api_base` esté poblado/vacío/ausente en `Settings` (mismo patrón que los tests ya existentes para `economico`/`calidad`); una entrada de YAML sin `api_key` ni `api_base` (o con ambos) falla fuerte al cargar, no en silencio.
- `test_generador_plan.py`: (a) `calidad` y `calidad_respaldo` fallan, `local` disponible y responde → se usa esa narrativa; (b) `ANTHROPIC_API_KEY` ausente, `OLLAMA_API_BASE` presente → se intenta `local` directo, sin intentar `calidad`/`calidad_respaldo` (espía que confirma que esas dos rutas nunca se llaman); (c) las 3 rutas fallan o ninguna está disponible → cae a plantilla, sin excepción; (d) la llamada a `local` usa el `timeout_segundos` declarado en el YAML (180), distinto del default de las otras rutas (30) — regresión específica contra el riesgo señalado en 1.3.

### 3.2 E1bis-2 — Instalación real + prueba de integración real (sin mocks)

**Justificación de por qué no basta con mocks:** un timeout mal configurado (sección 1.3) pasaría cualquier test con mocks (que no esperan 123 segundos reales) y solo se manifestaría contra un Ollama real — un mock verifica el orden de las llamadas, no el comportamiento real de la infraestructura subyacente. Esta clase de bug solo se detecta con una corrida de integración real.

**Pasos:**
1. Instalar Ollama en un entorno de desarrollo verificable (instalador oficial de Windows, o `winget install Ollama.Ollama`, dado que el entorno de desarrollo activo hoy es Windows).
2. `ollama pull phi3` — mismo modelo evaluado en el benchmark original.
3. Confirmar el servidor escuchando (`ollama list`, o `GET http://localhost:11434/api/tags`) antes de correr cualquier test contra él.
4. Configurar `OLLAMA_API_BASE=http://localhost:11434` en el `.env` real (no commiteado) del entorno de prueba.
5. Correr **dos escenarios reales distintos**, no uno solo:
   - (a) con `ANTHROPIC_API_KEY`/`DEEPSEEK_API_KEY` presentes: forzar un fallo simulado únicamente de `calidad`/`calidad_respaldo` (mock acotado a esas dos llamadas, en ese test específico) y confirmar que `local` sí se invoca de verdad y produce una narrativa real.
   - (b) con `ANTHROPIC_API_KEY`/`DEEPSEEK_API_KEY` ausentes del entorno: confirmar que el camino "todo-o-nada por configuración" (1.4) llega a `local` directo, sin intento previo, y produce una narrativa real.
6. Nuevo archivo `backend/tests/test_generador_plan_ollama_real.py`: función `_ollama_real_disponible()` — chequeo de socket (`host`/`puerto` extraídos de `OLLAMA_API_BASE`) con timeout corto, mismo patrón exacto que `_postgres_real_disponible()` en `backend/tests/test_api_seguimiento.py` (líneas 99-115) — y, si es alcanzable, confirmar además que el modelo `phi3` está descargado (`GET /api/tags`) antes de intentar, para no confundir "Ollama no está" con "el modelo no está". Decorar el test real con `@pytest.mark.skipif(not _ollama_real_disponible(), reason="Requiere Ollama real alcanzable con OLLAMA_API_BASE configurado y el modelo phi3 descargado")` — se salta limpio en CI (que no provisiona Ollama, igual que no provisiona Postgres real hoy) sin fallar el pipeline.
7. El test real debe generar la narrativa de una brecha de prueba conocida (recomendado: "Firma electrónica", el mismo prompt del benchmark original en `docs/stack-tecnologico.md`, para poder comparar) y verificar: texto no vacío; el texto **no** es literalmente igual a la plantilla determinista de `_narrativa_plantilla` para esa acción (para confirmar que sí vino del LLM y no cayó en degradado por un fallo silencioso); tiempo total dentro de un margen razonable (ej. menor a 200s, dejando margen sobre los 180s del timeout de la ruta).
8. Guardar el output literal de la corrida real (terminal) como evidencia adjunta del cierre de esta tarea.

### 3.3 E1bis-3 — Documentación

- **`docs/stack-tecnologico.md`:** mientras E1bis-1/E1bis-2 no estén cerradas, reemplazar la frase aspiracional de la línea 82 ("queda disponible como alternativa vía cambio de configuración de LiteLLM... si el criterio cambia en el futuro") por una versión que distinga explícitamente evaluado/decidido de construido, con puntero a este documento — ej.: agregar tras esa frase: "**[PENDIENTE — 05-ago-2026]**: esta alternativa está evaluada y decidida pero *aún no wireada* en el código (`litellm_config.yaml` solo define hoy las 3 rutas API; `ollama_api_base` en `app/core/config.py` no está conectado a ningún módulo de `app/ia/`); el plan de implementación para cerrar esta brecha vive en `docs/plan-implementacion-e1-bis-capa-ia-local.md`." Igual tratamiento en la línea 31 (fila "Capa IA" de la tabla del stack) y en la línea 84 ("El diseño de LiteLLM... hace que este default sea reversible por configuración... no exige reescribir `ia/` ni `engine/`" — hoy tampoco verificable sin el wiring). Una vez cerrada la revisión (E1bis-4), esta nota se reemplaza por una que confirme "implementado, ver commit X" — no se elimina sin dejar rastro, se actualiza.
- **`entregables/fase-2/dimensionamiento-costos.md` línea 9:** misma frase aspiracional casi idéntica ("queda disponible como alternativa vía cambio de configuración de LiteLLM... útil si el criterio cambia en el futuro") — mismo tratamiento `[PENDIENTE]` con el mismo puntero.
- **`.env.example`:** agregar un comentario bajo `OLLAMA_API_BASE=` explicando el nuevo comportamiento real una vez implementado (ejemplo `http://localhost:11434`) y aclarando que dejarlo vacío preserva el comportamiento actual (solo rutas API, sin cambio para quien no lo use).
- **`docs/plan-implementacion.md`:** decidir explícitamente si amerita una fila nueva en la tabla de Fase E. Recomendación: no agregar fila al documento canónico por una extensión acotada de una sola iteración — la trazabilidad ya queda cubierta por este documento. Quien ejecute E1bis-3 debe registrar explícitamente cuál de las dos opciones tomó y por qué, sin asumir en silencio.

### 3.4 E1bis-4 — Revisión integral

La revisión debe verificar como mínimo:
1. Los 3 puntos de disponibilidad/timeout (1.2/1.3) implementados exactamente como se decidió, sin bifurcación hardcodeada por nombre de ruta.
2. La cadena de fallback (1.4) trazada manualmente en los 4 caminos posibles (`calidad` ok; `calidad` falla + `calidad_respaldo` ok; ambas fallan + `local` ok; las 3 fallan → plantilla) y en el camino "todo-o-nada" (solo `OLLAMA_API_BASE` poblado).
3. Contrato "nunca excepción hacia quien llama / nunca decide la acción" intacto en los 4 caminos.
4. Que la evidencia de E1bis-2 sea una corrida real, no solo declarativa — exigir el output literal si no viene adjunto.
5. Consistencia exacta de nombre de ruta/modelo/variable de entorno entre `litellm_config.yaml`, `config.py`, `generador_plan.py`, `docs/TRD.md` (si se actualiza) y la documentación corregida.
6. Sin scope creep a `verificador.py`/`plan_job.py`/`engine/`/frontend/F1/F9 (ver 1.5).
7. Sin narrativa de proceso en código (ver contrato de 3.1).
8. Fidelidad de la corrección de `docs/stack-tecnologico.md`/`dimensionamiento-costos.md`/`.env.example` al alcance de 3.3.

## 4. Orden de ejecución

Orden secuencial obligatorio E1bis-1 → E1bis-2 → E1bis-3 → E1bis-4, con E1bis-5 ejecutable en paralelo a E1bis-4 (ver tabla de la sección 2). Cada entregable se cierra completo (código + tests + docs) antes de abrir el siguiente.

## 5. Riesgos y supuestos abiertos

- Formato exacto del provider string de LiteLLM para Ollama (`ollama/phi3` vs. `ollama_chat/phi3`) no verificado en este plan — debe confirmarse contra la documentación vigente de LiteLLM antes de escribir el YAML, no asumirse de memoria.
- Ollama no está instalado en ningún entorno de desarrollo activo hoy (Windows) — E1bis-2 depende de poder instalar software en el entorno de desarrollo; si el entorno de ejecución no lo permite (permisos de instalación, red saliente), la instalación se realiza manualmente y los tests de integración se corren después contra ese Ollama ya instalado.
- Este plan no extiende el fallback local a F1 (`asistente_captura.py`)/F9 (`verificador.py`) — ver 1.5.
- No se modifica el timeout de las rutas ya existentes (`economico`/`calidad`/`calidad_respaldo`) — el campo `timeout_segundos` es opcional y retrocompatible.
- CI (GitHub Actions) no provisiona Ollama, igual que no provisiona Postgres real hoy (`.github/workflows/ci.yml`) — el test de integración real de E1bis-2 se saltará limpio ahí por diseño; la verificación real depende de correrlo manualmente en un entorno con Ollama instalado, mismo estándar que ya rige para el test de Postgres real.

## 6. Documentos relacionados

`docs/stack-tecnologico.md`, `docs/TRD.md`, `docs/plan-implementacion.md`, `entregables/fase-2/dimensionamiento-costos.md`, `backend/app/ia/config.py`, `backend/app/ia/litellm_config.yaml`, `backend/app/ia/generador_plan.py`, `backend/tests/test_ia_config.py`, `backend/tests/test_generador_plan.py`, `backend/tests/test_api_seguimiento.py` (patrón `skipif` de referencia, líneas 99-121).

## 7. Actualización posterior — Ollama como servicio opcional de Docker Compose

Este plan (sección 3.2, paso 1) documentó instalación manual de Ollama fuera de Docker como el único camino, porque en ese momento (5 de agosto de 2026) ningún entorno de desarrollo lo tenía instalado y el objetivo inmediato era cerrar la brecha código-vs-documentación de E1bis-1/E1bis-2, no resolver el despliegue. Esa decisión quedó incompleta frente al principio de "Transferencia de capacidades" del README raíz: si quien adopta DiagMuni con la ruta `local` tiene que instalar y operar Ollama por su cuenta, fuera del `docker compose up -d` que ya cubre el resto del stack, el producto llega incompleto para quien específicamente quiere evitar depender de un proveedor de IA privativo.

Se agregó un perfil opcional (`ia-local`) a `docker-compose.yml`: `docker compose --profile ia-local up -d` levanta un servicio `ollama` (imagen oficial, volumen persistente para el modelo descargado); `OLLAMA_API_BASE=http://ollama:11434` en `.env` lo conecta sin tocar código (ver `docs/TRD.md`, `docs/runbook-despliegue.md` sección "IA local con Ollama"). No reemplaza la instalación manual descrita en 3.2 — sigue siendo válida para quien prefiera correr Ollama fuera de Docker (otro proceso, otro host) — la containeriza como alternativa por defecto para quien sigue el runbook estándar del proyecto.

## 8. Actualización posterior — timeout de la ruta `local` insuficiente en hardware móvil real (verificación G4)

Durante la verificación de G4 (`docs/plan-implementacion.md`) en un equipo portátil real (Intel i7-8650U, 4 núcleos/8 hilos, laptop de bajo consumo, RAM 15.8GB — piso deliberadamente más bajo que un VPS de referencia, ver `docs/runbook-despliegue.md`), el perfil `ia-local` se activó, `phi3` se descargó y respondió (confirmado en el log de Ollama: generación real de tokens, no un fallo de conectividad), pero el plan resultante quedó en modo degradado en dos corridas.

**Diagnóstico:** `backend/app/ia/generador_plan.py` línea 99 (`except Exception: pass`) traga cualquier fallo de la ruta `local` a propósito (contrato de degradación silenciosa, sección 1.4) — por eso no aparecía ningún traceback en los logs, ni siquiera con `LITELLM_LOG=DEBUG`. El sospechoso señalado por el propio diseño de la sección 1.3 (`timeout_segundos: 180`, "margen sobre los 123s medidos" **en el benchmark de un iMac i5-4570 de escritorio, sin restricción térmica**) es consistente con lo observado: un CPU móvil de bajo consumo, con un prompt de ~1400 tokens de contexto, es razonable que exceda ese margen.

**Decisión:** subir `timeout_segundos` de la ruta `local` de 180 a **600** en `backend/app/ia/litellm_config.yaml`, sin cambiar ningún otro comportamiento (sigue siendo config-driven, sección 1.3; las demás rutas conservan su default de 30s). `[NO VERIFICADO]` el tiempo real exacto que tomó `phi3` en este hardware — no se capturó con precisión antes de subir el timeout; pendiente confirmar con una corrida exitosa y anotar la cifra real aquí, siguiendo el mismo estándar de no inventar un número sin medirlo.

**Por qué no es una regresión de diseño:** el mecanismo de timeout configurable por ruta (sección 1.3) fue diseñado exactamente para este escenario — ajustar el margen sin tocar código cuando el hardware real difiere del benchmark original. Confirma además, de forma no planeada, el valor del punto de control de G4: un equipo portátil como piso de verificación expone límites reales (timeout insuficiente) que un servidor de escritorio no había expuesto.

## 9. Actualización posterior — el verificador (F9) divaga en vez de responder SI/NO, aun con el timeout corregido

Tras subir `timeout_segundos` a 600 (sección 8), la misma verificación de G4 repitió la prueba y **el plan siguió en modo degradado**. Los logs reales de Ollama mostraron que las 4 llamadas completaron sin exceder el timeout (53.7s, 66s, 295.6s, 206.4s) — el generador de plan (F3) redactó bien las dos brechas. El problema real estaba en el verificador (F9, `backend/app/ia/verificador.py`): dos de las cuatro llamadas eran auditorías de F9, y `phi3` respondió con **965 y 1509 tokens** de divagación a un prompt que pide explícitamente una sola palabra ("SI" o "NO"). El parser (`veredicto in ("SI", "SÍ")`, igualdad exacta) rechazó correctamente esa respuesta — el plan nunca llegó a `verificado=true`, y se mostró en modo degradado pese a que F3 sí generó con IA real.

Este es el mismo problema ya observado antes de containerizar Ollama y dejado pendiente de resolver en ese momento: "`phi3` sí responde, pero no respeta la instrucción de responder ÚNICAMENTE con SI o NO". El commit que después marcó a G1 como cerrado (`8106d9e`, 2026-08-10) solo agregó el E2E `modo-llm.spec.ts` y lo corrió una vez a mano con éxito — pero la llamada real usa `temperature = 0.800` (sampler params de `llama-server`, visto en el log), es decir, la salida **no es determinista entre corridas**. Un "pasó una vez" no es evidencia de que el problema esté resuelto.

**Revisión de diseño antes de implementar:** por el mismo motivo que la sección 1 de `docs/plan-implementacion-alta-gobierno.md` documenta alternativas comparadas explícitamente antes de decidir, este fix se sometió a una revisión de diseño dedicada antes de tocar código (no se resume aquí completa; ver el fix aplicado y sus tests como fuente de verdad). Hallazgos clave de esa revisión:

- `temperature=0` no reduce la capacidad discriminativa del verificador — solo determina cómo se muestrea de la misma distribución. El riesgo real es el inverso: si el veredicto modal de `phi3` para una narrativa infiel también fuera "SI" (sesgo de complacencia), `temperature=0.8` lo enmascaraba parcialmente con ruido; `temperature=0` lo hace *medible* — de ahí que el fix exija un test negativo real (ver abajo), no solo uno positivo.
- `max_tokens` bajo no arregla un veredicto perdido por sí solo (una respuesta truncada a media frase sigue sin ser "SI"/"SÍ" exacto) — resuelve el síntoma de latencia/costo, no el de exactitud. Son dos problemas distintos.
- Relajar el parser a *prefix-match* ("empieza con SI") se **descartó explícitamente**: "SIN EMBARGO, LA NARRATIVA INVENTA..." y "SI BIEN LA NARRATIVA CONTRADICE..." son aperturas concesivas comunes en español que un prefix-match aprobaría por error, convirtiendo el fail-closed en un falso-aprobado sistemático.

**Decisión implementada** (`backend/app/ia/verificador.py`, `_veredicto_llm`):
1. `temperature=0` y `max_tokens=10` en `completion_kwargs`, aplicados a **ambas** rutas de `_RUTAS_VERIFICACION` (`economico` y `local`) en el mismo call-site — son propiedad de la tarea (veredicto binario), no de la ruta; nunca un `if nombre_ruta == "local"` (mismo principio que la sección 1.3). No se tocó `generador_plan.py` (F3 sí necesita variabilidad de prosa) ni `litellm_config.yaml` (la ruta `economico` la comparte F1, que sí necesita respuestas largas).
2. El parser normaliza puntuación/comillas/énfasis envolventes antes de exigir igualdad exacta del resto (`veredicto.strip('.,;:!¡"\'*() \t\n')` antes de comparar) — acepta `"SI."`, `'"SÍ"'`, `"**SI**"`, pero sigue rechazando cualquier cosa con una segunda palabra, incluida una respuesta truncada por `max_tokens` a media frase (ambiguo = rechazo, por contrato).
3. Tests nuevos: `backend/tests/test_verificador.py` extiende las aserciones de espía existentes para confirmar `temperature`/`max_tokens` en ambas rutas, y agrega casos del parser (aprueba puntuación envolvente; rechaza aperturas concesivas y respuestas truncadas — regresión explícita contra volver a un prefix-match). `backend/tests/test_verificador_ollama_real.py` (nuevo, mismo patrón `skipif` que `test_generador_plan_ollama_real.py`) agrega lo que ningún mock puede probar: un caso positivo corrido 3 veces (estabilidad bajo `temperature=0`) y un **caso negativo** — narrativa que inventa una norma y un plazo ausentes de los datos — que hasta este archivo no existía en todo el repo contra un LLM real.

`[NO VERIFICADO]` el resultado real del caso negativo contra `phi3` en el momento de escribir esta sección — es la validación pendiente antes de dar este fix por cerrado (correr `test_verificador_ollama_real.py` contra el mismo entorno de G4). Si `phi3` aprobara la narrativa que inventa la norma, el hallazgo sería mayor que el bug de latencia original: significaría que la ruta `local` de F9 no discrimina y debería retirarse de `_RUTAS_VERIFICACION`, documentando que el modo `llm` 100%-local requiere un modelo auditor distinto — no seguir relajando el parser para forzar una aprobación.

## 10. Cierre de la sección 9 — resultado real del caso negativo y rediseño de F9 en dos capas

**Resultado real, verificado en un equipo de desarrollo con el mismo Ollama/`phi3` usado durante la verificación de G4** (con `temperature=0`, `max_tokens=10`, `stop=["\n"]` ya aplicados): `phi3` respondió `'SI'` de forma limpia y reproducible a la narrativa con el Artículo 999 y el plazo de 10 días inventados. No fue un problema de formato — el caso positivo (narrativa fiel real) también aprobó correctamente, así que no es que rechace o apruebe todo indiscriminadamente: `phi3` simplemente no está discriminando fidelidad normativa con ninguna confiabilidad demostrada. Se confirma el escenario que esta misma sección anticipó: "el veredicto modal de `phi3` para una narrativa infiel también fuera 'SI' (sesgo de complacencia)".

**Objeción real que motivó una segunda escalación de diseño:** retirar `local` de la verificación LLM (dejando solo `economico`/DeepSeek) preocupó porque "requerir un modelo de pago... nos deja en la brecha de 'ya no es open source'". La respuesta, verificada contra el código y los documentos reales del proyecto:

- La licencia del código (Apache 2.0, `README.md` líneas 27-29) **no está amenazada** por ninguna decisión sobre qué modelo audita F9 — DeepSeek se consumiría como servicio externo opcional, no como dependencia de código.
- La meta real en juego es otra: el propio `verificador.py` (antes de esta sección) documentaba explícitamente que agregar `local` a la cadena de veredicto "cierra" el hueco de que el modo `llm` quedara inalcanzable sin una API de pago. Retirar `local` sin más **reabriría exactamente esa meta**, aunque no violara la licencia.
- Pero mantener `local` para preservar la etiqueta "100% local" al costo de vaciar la garantía (un `verificado=true` que aprueba normativa inventada) es la peor versión posible de esa promesa: cumplida en el nombre, incumplida en la sustancia.

**Diseño final implementado — F9 en dos capas, en este orden estricto (`backend/app/ia/verificador.py`, `verificar_contenido`):**

1. **Compuerta determinista, siempre, sin LLM ni costo** (`backend/app/ia/verificador_citas.py`, módulo nuevo): extrae de la narrativa cualquier número de artículo/decreto, acrónimo de ley (LNETB, LFEA, LGPDPPSO...) y cantidad de tiempo (días/meses/años/horas), y exige que cada uno aparezca también en los campos estructurados de referencia (`paso_administrativo`, `paso_tecnico`, `paso_organizacional`, `por_que_importa`, `fuente_normativa`). Coincidencia por límites de palabra (no substring ingenuo, para no confundir "25" con parte de "1250"), robusta a reformular "art. 25-III" como "artículo 25-III" (compara solo el identificador numérico, no el prefijo). Detecta determinísticamente, en milisegundos, exactamente el caso que motivó todo esto. **Basta ella sola para `verificado=true` sin ninguna API de pago** — el modo `llm` 100% local vuelve a estar completo, con una garantía real en vez de un sello de goma.
   - Límite honesto, documentado en el propio módulo: no detecta tergiversación del contenido de una cita real, ni contradicciones que no introducen ningún número o nombre nuevo. Es una mejora estricta sobre no tener ningún chequeo (que es lo que había antes de facto, dado que `local` no discriminaba nada), no una auditoría semántica completa.
2. **Veredicto LLM vía `economico`** (DeepSeek), capa opcional adicional que se suma solo si hay `DEEPSEEK_API_KEY` -- nunca sustituye a la compuerta, nunca es requisito para aprobar sin ella. `local`/Ollama se retiró por completo de esta capa (`_RUTA_VERIFICACION_LLM = "economico"`, ya no una tupla de rutas) -- sigue usándose normalmente para F3 (redacción), donde el fallo es seguro por diseño (degrada a plantilla) y no exige que el modelo "juzgue" nada.

**Validación real, en un equipo de desarrollo con Ollama+`phi3` real** (mismos datos del caso que motivó la sección 9): caso positivo aprobado en 3/3 corridas, ~0.0-3.7s cada una (compuerta determinista, sin ninguna llamada LLM); caso negativo (Artículo 999 + plazo inventados) rechazado en 0.0s, también sin ninguna llamada LLM. Confirma que el rediseño cierra el problema sin reintroducir ninguna dependencia de red para el camino 100% local.

**Tests:** `backend/tests/test_verificador_citas.py` (nuevo, 10 casos puros, sin red) cubre la compuerta: narrativa fiel, cita real reformulada, artículo/decreto/plazo/acrónimo inventados, ausencia de falsos positivos por número suelto o por coincidencia parcial de dígitos. `backend/tests/test_verificador.py` se reescribió para las dos capas en su orden estricto (la compuerta corre primero y bloquea sin llamar nunca al LLM si rechaza). `backend/tests/test_plan_job.py` actualizado: el escenario "verificador sin `economico` disponible" ya no espera degradación automática — ahora depende de si la compuerta determinista aprueba el contenido real. `backend/tests/test_verificador_ollama_real.py` (el que se había agregado en la sección 9 para probar `phi3` como auditor) se **eliminó**: con `local` fuera de la cadena de veredicto LLM, ese archivo ya no ejercitaba ningún camino real del código -- dejarlo habría sido tan engañoso como el docstring desactualizado que esta misma sección corrigió antes.

**Alcance explícitamente diferido, no resuelto:** un modelo local más grande (ej. mistral 7B, Apache 2.0) evaluado específicamente para discriminación de fidelidad en F9 -- nunca se probó para esa tarea (solo para velocidad de redacción en F3), y hay precedente de que 7B tampoco garantiza fidelidad (olmo2, también 7B, fabricó una cita institucional en la tarea más fácil de redactar, `docs/stack-tecnologico.md`). Si se retoma, exige construir primero un set de ≥5 casos negativos variados -- un solo caso no prueba nada, mismo estándar que la "nota de honestidad" del propio `docs/stack-tecnologico.md`.

**Confirmación final end-to-end, en el equipo portátil real de G4** (no solo en el equipo de desarrollo de la validación anterior): tras actualizar el código (`git pull` + reconstrucción de la imagen del backend) y repetir el mismo diagnóstico de prueba, el plan alcanzó modo `llm` sin la advertencia de plantilla degradada -- sin ninguna `DEEPSEEK_API_KEY` configurada, confirmando en el despliegue real objetivo de G4 que la compuerta determinista por sí sola basta para `verificado=true`. Con esto, G4 queda verificado de punta a punta incluyendo el perfil `ia-local` completo (generación con `phi3` + verificación determinista), no solo el camino sin IA.
