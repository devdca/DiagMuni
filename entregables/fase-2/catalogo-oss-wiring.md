# Wiring del catálogo OSS (F4/F5) al plan de modernización — diseño

Paso 3 de 4 del pendiente #2 de backend. Insumo directo: `backend/app/engine/catalogo/componentes_oss.yaml` + `entregables/fase-2/catalogo-componentes-oss.md` (paso 1, aprobado) y `backend/app/engine/catalogo/costos_oss.yaml` + `entregables/fase-2/catalogo-costos-oss.md` (paso 2, aprobado). Documento de diseño puro — no contiene código Python; define con precisión de nombres, tipos y comportamiento lo que `ia-automatizacion` debe implementar en el paso 4, sin dejarle ninguna decisión de diseño pendiente.

## 0. Verificación previa: alineamiento 1:1 de las 6 claves

Antes de proponer el mecanismo se releyeron directamente (no de memoria) los 3 orígenes para confirmar que `categoria_catalogo` es la misma llave textual en los tres:

| `categoria_catalogo` | YAML de regla (archivo, línea del campo) | `componentes_oss.yaml` (línea) | `costos_oss.yaml` (línea) |
|---|---|---|---|
| `modulo_cifrado_datos` | `datos_personales.yaml` líneas 14 (mx) / 22 (uy) | línea 9 | línea 16 |
| `gestor_expediente_electronico` | `documentos_papel_digital.yaml` líneas 13 (mx) / 21 (uy) | línea 18 | línea 32 |
| `modulo_firma_electronica` | `firma_electronica.yaml` líneas 13 (mx) / 21 (uy) | línea 27 | línea 48 |
| `identidad_federada` | `identidad_acceso.yaml` líneas 13 (mx) / 23 (uy) | línea 37 | línea 64 |
| `conector_interoperabilidad` | `interoperabilidad.yaml` líneas 13 (mx) / 21 (uy) | línea 46 | línea 80 |
| `adaptador_pasarela_pago` | `motor_pagos.yaml` líneas 13 (mx) / 21 (uy) | línea 56 | línea 96 |

Las 6 llaves son idénticas carácter por carácter en los tres orígenes, en ambas ramas `mx`/`uy` de cada YAML de reglas (`AccionPais.categoria_catalogo` no varía por país dentro de la misma regla — ver `backend/app/engine/reglas_loader.py` líneas 17-25). Confirmado también que ambos YAML de catálogo anidan sus 6 entradas bajo la misma clave contenedora `componentes:` (`componentes_oss.yaml` línea 7, `costos_oss.yaml` línea 14) — mismo nombre de contenedor en los dos archivos, lo que simplifica el merge.

**Hallazgo que condiciona el diseño (no es un defecto de este wiring, es un hecho ya presente en el catálogo aprobado en pasos 1/2):** para `conector_interoperabilidad`, rama `uy`, el propio `paso_tecnico` de `interoperabilidad.yaml` línea 16 dice textualmente *"Cliente PDI de AGESIC (ya en catálogo OSS, docs/stack-tecnologico.md)"* — es decir, el texto de la brecha para Uruguay nombra un producto (la PDI de AGESIC) distinto del componente que resuelve la categoría genérica en `componentes_oss.yaml` (X-Road, sustituido explícitamente por falta de licencia verificable de la PDI, ver `catalogo-componentes-oss.md` sección 5). El wiring de este documento no oculta ni resuelve esta discrepancia: la propaga tal cual mediante el campo `nota_advertencia` (sección 1), que en esta entrada específica ya contiene, verbatim, la advertencia de que X-Road no sustituye la obligación legal de integrarse con la PDI real (Ley 18.719 arts. 157-160). Es responsabilidad de quien lea el plan (y, a mediano plazo, de una redacción LLM en el modo `llm`, hoy fuera de alcance — ver sección 4) dejar claro que `componente_recomendado` es una referencia de catálogo genérico, no el software puntual que el `paso_tecnico` de la brecha ya nombra para ese país.

## 1. Campo nuevo en `brechas[]`: `componente_recomendado`

**Decisión: un solo campo anidado, `componente_recomendado`, agregado como una clave hermana más dentro de cada entrada de `brechas` (junto a `variable`, `categoria_catalogo`, `paso_administrativo`... ya existentes) — nunca varios campos sueltos a nivel de brecha.** Razón: las 9 claves ya existentes describen una sola brecha con una sola fuente de verdad (el YAML de reglas); mezclar ahí, sueltos, 15+ campos provenientes de dos archivos distintos (componente + costo) rompería la legibilidad del objeto y obligaría al frontend a reensamblar manualmente qué claves pertenecen al mismo componente. Un objeto anidado es, además, el mismo patrón que `docs/backend-schema.md` línea 124 ya acepta explícitamente para `contenido` ("estructura enriquecida... semi-estructurada", jsonb sin normalizar) — no es una desviación del criterio de esa tabla, es su continuación natural.

El campo es **siempre presente** en cada brecha (nunca una clave opcional que el frontend deba comprobar con `in`); su valor es un objeto, o `null` en el único caso defensivo de que `categoria_catalogo` no exista en el catálogo combinado (no debería ocurrir dado el alineamiento 1:1 de la sección 0, pero el mecanismo de resolución —sección 2— debe degradar a `null`, nunca lanzar una excepción que tumbe la generación completa del plan).

### 1.1 Forma exacta

```json
{
  "variable": "documentos_digitalizados",
  "categoria_catalogo": "gestor_expediente_electronico",
  "paso_administrativo": "...",
  "paso_tecnico": "...",
  "paso_organizacional": "...",
  "prerrequisitos": ["..."],
  "por_que_importa": "...",
  "fuente_normativa": "...",
  "narrativa": "...",
  "componente_recomendado": {
    "nombre_componente": "Mayan EDMS",
    "licencia": "Apache-2.0",
    "url_repositorio": "https://github.com/mayan-edms/Mayan-EDMS",
    "moneda_local_codigo": "MXN",
    "costo_licenciamiento": {"moneda_local": "0", "usd": "0"},
    "costo_infraestructura": {
      "moneda_local": "114.55/mes (piso mínimo verificado; ver nota_infraestructura para el escalón recomendado, no verificado)",
      "usd": "6.60/mes (piso mínimo verificado; ver nota_infraestructura para el escalón recomendado, no verificado)"
    },
    "costo_implementacion": {"moneda_local": "[NO VERIFICADO]", "usd": "[NO VERIFICADO]"},
    "nota_advertencia": null,
    "fuente_licencia": "https://raw.githubusercontent.com/mayan-edms/Mayan-EDMS/master/LICENSE",
    "fuente_actividad": "https://api.github.com/repos/mayan-edms/Mayan-EDMS",
    "fuente_costo": "https://docs.mayan-edms.com/chapters/requirements.html (requisitos mínimo/recomendado); https://contabo.com/en/vps/ (precio Cloud VPS 4, dato estructurado schema.org Product/AggregateOffer leído del HTML de la página)",
    "fecha_verificacion": "2026-08-03"
  }
}
```

Ejemplo del caso con `nota_advertencia` no nula (misma brecha, rama `uy`, categoría `conector_interoperabilidad`): `nota_advertencia` lleva, verbatim y sin resumir, el texto completo del campo `nota` de `componentes_oss.yaml` línea 54 (la advertencia de que X-Road sustituye al Cliente PDI de AGESIC solo para efectos de catálogo genérico, y no reemplaza la obligación legal de integrarse con la PDI real).

### 1.2 Subconjunto de datos incluido, campo por campo, y por qué

De `componentes_oss.yaml` (por entrada):

| Campo origen | ¿Incluido? | Nombre en `componente_recomendado` | Razón |
|---|---|---|---|
| `nombre_componente` | Sí | `nombre_componente` | Dato mínimo que el encargo pide explícitamente |
| `licencia` | Sí | `licencia` | Dato mínimo que el encargo pide explícitamente |
| `url_repositorio` | Sí | `url_repositorio` | Referencia corta y accionable — el área TIC del municipio puede ir directo al repositorio |
| `version_o_release_verificado` | No | — | Evidencia de verificación (metodología), no una decisión que el funcionario deba leer; queda consultable indirectamente vía `fuente_licencia`/`fuente_actividad` para quien quiera profundizar |
| `evidencia_actividad_comunidad` | No | — | Prosa extensa de metodología (a veces varios cientos de caracteres); mismo criterio que la fila anterior |
| `fuente_licencia` | Sí | `fuente_licencia` | "Una referencia corta a la fuente", tal como pide el encargo |
| `fuente_actividad` | Sí | `fuente_actividad` | Ídem — permite verificar que el componente sigue activo sin tener que copiar la evidencia completa |
| `nota` (solo presente en 3 de 6 entradas: `modulo_firma_electronica`, `conector_interoperabilidad`, `adaptador_pasarela_pago`) | Sí | `nota_advertencia` (renombrado; `null` cuando la entrada no declara `nota`) | No es evidencia de metodología — es una advertencia operativa/legal que cambia cómo debe leerse la recomendación (ver hallazgo de la sección 0 para `conector_interoperabilidad`; casos análogos: DSS debe desplegarse como servicio separado, no linkeado; django-payments es un patrón de referencia del ecosistema Django, no una dependencia de DiagMuni). Omitirla arriesgaría que el funcionario lea el nombre del componente sin el matiz que ya lo acompaña en el catálogo aprobado |

De `costos_oss.yaml` (por entrada):

| Campo origen | ¿Incluido? | Nombre en `componente_recomendado` | Razón |
|---|---|---|---|
| `costo_licenciamiento_mxn`/`_uyu`/`_usd` | Sí, subconjunto | `costo_licenciamiento.moneda_local` (según país) + `costo_licenciamiento.usd` | Ver sección 1.3 sobre por qué solo la moneda local + USD, no las 3 monedas simultáneas |
| `nota_licenciamiento` | No | — | Boilerplate casi idéntico en las 6 categorías ("OSS sin costo de licencia, verificado") — ya se infiere de `licencia` + el propio valor `"0"` |
| `costo_infraestructura_mxn`/`_uyu`/`_usd` | Sí, subconjunto | `costo_infraestructura.moneda_local` + `.usd` | Igual que arriba |
| `nota_infraestructura` | No | — | Prosa extensa de metodología de cotización (a veces un párrafo completo con 2-3 fuentes distintas); el valor de costo ya trae inline el matiz esencial entre paréntesis (ej. "piso mínimo verificado; ver nota..., no verificado") |
| `costo_implementacion_mxn`/`_uyu`/`_usd` | Sí, subconjunto | `costo_implementacion.moneda_local` + `.usd` | Igual que arriba; en las 6 categorías este valor es hoy literalmente `"[NO VERIFICADO]"` (ver sección 3) |
| `nota_implementacion` | No | — | Mismo patrón boilerplate en las 6 ("no se encontró fuente pública de horas típicas..."); cubierto de forma genérica por la regla de renderizado de la sección 3, sin repetir la prosa |
| `fuente_costo` | Sí | `fuente_costo` | Referencia corta a la fuente, tal como pide el encargo |
| `fecha_consulta` | Sí | `fecha_verificacion` (renombrado, mismo criterio de claridad de nombre que `nota` → `nota_advertencia`) | Da al funcionario una fecha de corte del dato — relevante porque los precios de infraestructura son volátiles (ya advertido en `catalogo-costos-oss.md`) |
| Bloque `tipo_cambio` (nivel raíz de `costos_oss.yaml`, no por entrada) | No aplica | — | No es un campo por `categoria_catalogo`, es la fuente del tipo de cambio ya usado para *precalcular* las cifras `_mxn`/`_uyu` que sí se leen. El wiring nunca recalcula una conversión de moneda en tiempo de ejecución — solo lee cadenas ya resueltas del YAML |

### 1.3 Por qué solo moneda local + USD, no las 3 monedas simultáneas

El encargo ilustra la idea con un campo `componente_recomendado` que expone `costo_infraestructura_usd`, `costo_infraestructura_mxn`, `costo_infraestructura_uyu` todos a la vez (mismo patrón plano que ya usa `costos_oss.yaml`). Se decide **no** replicar ese patrón plano tal cual, sino resolver, en el momento de armar el `contenido` (que ya se genera por país — `generar_contenido_degradado(respuestas, pais)`), cuál es la moneda local aplicable, y exponer solo esa más USD como referencia internacional:

- Cada llamada a `generar_contenido_degradado` ya conoce el país (parámetro `pais`); no hay razón para que un municipio mexicano reciba en su plan una cifra en UYU que nunca va a usar, ni viceversa.
- El principio rector del producto (`.claude/agents/transformacion-digital.md` línea 15, "Diseña para el funcionario municipal promedio, no para el tecnólogo" — brief del especialista que redactó la tarea madre de este documento, coherente con `docs/PRD.md` línea 18 "Usuario objetivo... no el tecnólogo") pesa a favor de mostrar menos cifras irrelevantes, no más.
- El costo de esta decisión es mínimo: una función de resolución con un diccionario de 2 entradas (`"mx" → ("MXN", sufijo "mxn")`, `"uy" → ("UYU", sufijo "uyu")"`) — ver sección 2 — no una reescritura del catálogo de costos.
- El campo `moneda_local_codigo` (`"MXN"` o `"UYU"`) viaja junto al objeto precisamente para que el objeto sea autocontenido: quien lea `contenido` (frontend, un reporte exportado, un auditor) no necesita volver a mirar `tenant.pais` para saber qué representa `costo_infraestructura.moneda_local`.

**Contrato de tipos, explícito para evitar un error común de implementación:** todos los valores dentro de `costo_licenciamiento`, `costo_infraestructura` y `costo_implementacion` (tanto `moneda_local` como `usd`) son **strings opacas**, nunca números. `costos_oss.yaml` ya almacena estos valores como texto con unidades, calificadores y rangos (ej. `"0 (no aplica)"`, `"114.55-416.55/mes"`, `"[NO VERIFICADO]"`) — el wiring los copia verbatim, sin parsear a `float` ni intentar normalizar unidades. Ningún componente de este wiring hace aritmética con estos valores.

## 2. Mecanismo de resolución

**Decisión: módulo nuevo, `backend/app/engine/catalogo_loader.py` — no una función agregada a `reglas_loader.py`.**

Justificación: `reglas_loader.py` está deliberadamente acotado a un directorio (`REGLAS_DIR = backend/app/engine/reglas/`) y a un esquema (`Regla`/`AccionPais`, claves `variable`/`criterio_deteccion`/`acciones`). El propio `docs/TRD.md` línea 74 ya traza la línea divisoria de responsabilidad que este documento hereda: *"costo y tiempo no viven aquí [en el catálogo de reglas]: los añade infraestructura-costos en una capa de costeo paramétrico separada (por país/moneda), para no mezclar contenido normativo-técnico (estable) con precios (volátiles)"*. `componentes_oss.yaml`/`costos_oss.yaml` ya viven, por esa misma razón, en un subdirectorio distinto (`backend/app/engine/catalogo/`, no `backend/app/engine/reglas/`) desde el paso 1. Un módulo nuevo, paralelo a `reglas_loader.py` en el mismo paquete `engine/`, replica el patrón ya establecido (una función cacheada con `@lru_cache(maxsize=1)` que lee YAML en tiempo de ejecución y nunca lo transcribe a Python — misma regla dura que `reglas_loader.py` líneas 3-6) sin mezclar los dos esquemas de datos en un mismo archivo.

### 2.1 Contenido exacto del módulo nuevo

- **Rutas de archivo:** `CATALOGO_DIR = Path(__file__).parent / "catalogo"`; `COMPONENTES_YAML = CATALOGO_DIR / "componentes_oss.yaml"`; `COSTOS_YAML = CATALOGO_DIR / "costos_oss.yaml"`.
- **Dataclass nueva, `ComponenteCatalogo` (frozen, mismo estilo que `AccionPais`)**, con un campo por cada dato incluido en la tabla de la sección 1.2, aplanado (sin anidar), con estos nombres exactos: `nombre_componente`, `licencia`, `url_repositorio`, `nota` (`str | None`), `fuente_licencia`, `fuente_actividad`, `costo_licenciamiento_mxn`, `costo_licenciamiento_uyu`, `costo_licenciamiento_usd`, `costo_infraestructura_mxn`, `costo_infraestructura_uyu`, `costo_infraestructura_usd`, `costo_implementacion_mxn`, `costo_implementacion_uyu`, `costo_implementacion_usd`, `fuente_costo`, `fecha_consulta`.
- **Función `cargar_catalogo_oss() -> dict[str, ComponenteCatalogo]`**, cacheada con `@lru_cache(maxsize=1)` (idéntico patrón a `cargar_catalogo()` de `reglas_loader.py` líneas 59-74): lee `COMPONENTES_YAML["componentes"]` y `COSTOS_YAML["componentes"]`, confirma que ambos diccionarios tienen exactamente el mismo conjunto de llaves (guarda de integridad de datos — si algún día un YAML gana o pierde una categoría sin actualizar el otro, esta función debe fallar de forma ruidosa en el primer acceso, no silenciosa en producción), y arma un `ComponenteCatalogo` por llave combinando los campos de ambos orígenes según la tabla de la sección 1.2. El bloque `tipo_cambio` de `costos_oss.yaml` se ignora explícitamente (no es una entrada de `categoria_catalogo`).
- **Constante `_MONEDA_POR_PAIS: dict[str, tuple[str, str]]`**, con exactamente dos entradas: `"mx" → ("MXN", "mxn")`, `"uy" → ("UYU", "uyu")` — el primer elemento de la tupla es el código de moneda a mostrar (`moneda_local_codigo`), el segundo es el sufijo de atributo a leer de `ComponenteCatalogo` (`costo_infraestructura_mxn` vs. `costo_infraestructura_uyu`, etc.).
- **Función pública `componente_recomendado_para(categoria_catalogo: str, pais: str) -> dict | None`**: busca `categoria_catalogo` en `cargar_catalogo_oss()`; si no existe, devuelve `None`. Busca `pais` en `_MONEDA_POR_PAIS`; si no existe (defensivo — hoy el único caso posible es `"mx"`/`"uy"`, dado que `AccionPais` solo se construye para esas dos ramas en los 6 YAML de reglas ya existentes), devuelve `None`. En cualquier otro caso, arma y devuelve el objeto con la forma exacta descrita en la sección 1.1 (incluyendo el renombrado `nota` → `nota_advertencia` y `fecha_consulta` → `fecha_verificacion`, y la selección de `moneda_local` según el sufijo resuelto). Esta es la única función que `plantillas.py` necesita importar.

### 2.2 Por qué toda la lógica de armado vive en `catalogo_loader.py`, no en `plantillas.py`

`componente_recomendado_para` recibe `pais` como parámetro y devuelve el diccionario ya completo, listo para insertarse — no una tupla de datos crudos que `plantillas.py` tendría que interpretar. Esto minimiza el diff en `plantillas.py` (sección 5) a una sola línea nueva dentro del diccionario de cada brecha, y —más importante de cara a la limitación de la sección 4— deja toda la lógica reutilizable en un solo lugar: el día en que se autorice una tarea futura para cerrar la asimetría `llm`/`degradado`, `generador_plan.py` podrá llamar exactamente a la misma función `componente_recomendado_para(accion.categoria_catalogo, pais)` sin duplicar ninguna lógica de resolución de moneda o de merge de catálogos.

## 3. Manejo de campos `[NO VERIFICADO]`

**Regla: el wiring nunca transforma, oculta ni sustituye el literal `"[NO VERIFICADO]"` — lo copia verbatim del YAML de origen a `contenido`, exactamente como llega.** Hoy esto aplica a `costo_implementacion` en las 6 categorías (las 6 tienen ese hueco declarado en `catalogo-costos-oss.md`) y a `costo_infraestructura` únicamente en `modulo_firma_electronica` (la única de las 6 sin cifra de infraestructura verificable — ver `catalogo-costos-oss.md` sección 3).

Tres consecuencias de diseño, explícitas para que no queden a discreción de quien implemente:

1. **Nunca se convierte a `0`.** `"[NO VERIFICADO]"` y `"0"` son valores textuales distintos con significados opuestos: `"0"` es un hecho verificado (ej. licenciamiento OSS sin costo, o "no aplica" porque el componente no requiere un servicio adicional que hostear — `modulo_cifrado_datos` y `adaptador_pasarela_pago`); `"[NO VERIFICADO]"` es la ausencia honesta de una fuente citable. Colapsar el segundo caso al primero fabricaría un dato falso — exactamente lo que `catalogo-costos-oss.md` (línea 5) declara que esta tarea prohíbe.
2. **Nunca se omite la clave.** El objeto `componente_recomendado` siempre trae las tres claves `costo_licenciamiento`, `costo_infraestructura`, `costo_implementacion`, cada una con sus dos sub-claves `moneda_local`/`usd` presentes — nunca ausentes ni `null` a nivel de sub-clave individual (a diferencia de `componente_recomendado` en sí, que sí puede ser `null` a nivel de brecha completa, ver sección 1). Si se omitiera la clave en vez de mostrar el literal, el frontend no tendría forma de distinguir "no hay dato" de "se nos olvidó pedirlo".
3. **`"[NO VERIFICADO]"` es un literal reservado del proyecto, no una cadena libre.** Ya se usa con este formato exacto (mayúsculas, corchetes) en los 3 documentos de evidencia de fase 2 (`catalogo-componentes-oss.md`, `catalogo-costos-oss.md`, y el propio `dimensionamiento-costos.md`, citado como precedente del mismo estándar de marcado en `catalogo-costos-oss.md` línea 5, "ninguna cifra sin fuente citada... se marca `[NO VERIFICADO]`, nunca se inventa un número"). Este documento fija ese mismo literal como parte del contrato de la API (`plan_modernizacion.contenido`): quien construya la vista para el funcionario (frontend, fuera de alcance de esta tarea) debe hacer una comparación de igualdad exacta contra la cadena `"[NO VERIFICADO]"` para activar un tratamiento visual distinto (ej. atenuado, con una etiqueta del tipo "dato no verificado — no se encontró una fuente pública confiable", nunca presentado como si fuera una cifra normal) — nunca debe re-traducirse, re-capitalizarse ni parafrasearse ese literal en ningún punto de la cadena backend→frontend, para que la comparación de igualdad siga funcionando en cualquier capa que la necesite (incluida una futura auditoría F9 sobre este campo, si se decidiera extenderla).

No se requiere ninguna lógica condicional en `catalogo_loader.py` para producir este comportamiento: como los propios YAML de origen ya almacenan el literal `"[NO VERIFICADO]"` como el valor completo de la cadena (no como un flag booleano separado), el simple hecho de copiar el valor verbatim (sección 2) ya cumple las 3 consecuencias de arriba sin código adicional de manejo especial — es una propiedad que emerge del diseño de "solo lectura y merge", no una rama de código nueva que agregar.

## 4. Asimetría `llm`/`degradado` — limitación declarada, no resuelta en esta tarea

**Confirmación explícita de la restricción:** `backend/app/ia/generador_plan.py` está fuera de alcance de esta tarea por instrucción dura del coordinador; no se propone, sugiere, ni redacta ningún cambio a ese archivo en este documento.

**Confirmación del hallazgo que motiva declarar la asimetría (verificado leyendo el archivo, no asumido):** `generar_contenido_llm` (`generador_plan.py` líneas 95-138) recorre el mismo catálogo de reglas (`cargar_catalogo()`, `criterio_se_cumple()`) de forma completamente independiente de `generar_contenido_degradado` (`plantillas.py` líneas 17-49), y arma su propio literal de diccionario por brecha (líneas 117-129) con exactamente los mismos 9 campos que `plantillas.py` líneas 29-40, campo por campo — es una segunda copia de la misma lógica de recorrido y armado, no una llamada a una función compartida. El único campo que difiere entre ambos es `narrativa` (plantilla determinista en un caso, LLM con *fallback* a la misma plantilla en el otro).

**Consecuencia práctica de esta tarea:** como el wiring de `componente_recomendado` (secciones 1-3) se instruye únicamente dentro de `generar_contenido_degradado` (ver alcance exacto, sección 5) y `generador_plan.py` no se toca, el campo `componente_recomendado` **no existirá** en ningún `contenido` producido por `generar_contenido_llm` hasta que una tarea futura dedicada replique el mismo cambio de una línea (`"componente_recomendado": componente_recomendado_para(accion.categoria_catalogo, pais)`) dentro del literal de diccionario de `generador_plan.py` líneas 117-129. En términos operativos y algo contraintuitivos: **un plan generado con la ruta `calidad` disponible (LLM funcionando, `ANTHROPIC_API_KEY` configurada) mostrará una narrativa más rica pero sin ninguna recomendación de componente/costo; un plan generado en modo `degradado` (sin API key, o tras el fallo de ambas rutas LLM) sí mostrará `componente_recomendado` completo en cada brecha.** El modo "mejor" en redacción queda, hasta que se cierre esta asimetría, peor en dato accionable.

**Recomendación: sí, registrar esto como limitación conocida del MVP**, con el mismo formato que la sección "Riesgos abiertos" de `docs/backend-schema.md` (líneas 121-124) y de `docs/PRD.md` — no dejarlo únicamente documentado en este archivo de diseño de fase 2, donde un lector futuro del backlog podría no encontrarlo. Se recomienda agregar, en la próxima edición de esos documentos (fuera del alcance de escritura de esta tarea, que no debe tocar `docs/`), una entrada del tipo: *"`componente_recomendado` (F4/F5) solo está wireado en el modo `degradado`; el modo `llm` no lo incluye todavía — brecha conocida, no un defecto silencioso, cierre pendiente de una tarea dedicada que además evalúe unificar el recorrido de catálogo duplicado entre `plantillas.py` y `generador_plan.py`."* Esta redacción dual (declarar la brecha + señalar la causa raíz real, la duplicación de recorrido) es deliberada: registrar solo el síntoma sin la causa raíz invitaría a una futura corrección superficial (copiar el campo a mano en `generador_plan.py`, dejando la duplicación intacta) en vez de la consolidación de fondo que el propio hallazgo de esta sección ya deja lista para ejecutarse con mínimo riesgo (sección 2.2).

## 5. Alcance exacto del cambio a `backend/app/engine/plantillas.py`

**Tocar únicamente:**

1. Un import nuevo al inicio del archivo: `componente_recomendado_para` desde el módulo nuevo `app.engine.catalogo_loader`.
2. El literal de diccionario dentro del bucle `for regla in catalogo.values():` de `generar_contenido_degradado` (líneas 29-40 actuales): agregar una clave nueva, `"componente_recomendado"`, cuyo valor es el resultado de llamar `componente_recomendado_para(accion.categoria_catalogo, pais)` — una sola línea nueva dentro de un diccionario que ya existe.

**No tocar, explícitamente:**

- La firma pública de `generar_contenido_degradado`: sigue siendo `(respuestas: dict, pais: str) -> dict`, sin parámetros nuevos ni cambio de tipo de retorno (el objeto de retorno sigue siendo `{"resumen_narrativo": str, "brechas": list[dict]}` — solo cambia la forma interna de cada `dict` de `brechas`).
- El criterio de detección de brechas: el bucle `for regla in catalogo.values(): if not criterio_se_cumple(...): continue` no cambia en ninguna línea ni condición. El wiring nunca decide si una brecha aplica.
- `_narrativa_plantilla` (líneas 10-14): no se modifica ni se le agregan parámetros. El wiring no toca la redacción de la narrativa, solo agrega un campo hermano nuevo.
- El manejo de `resumen_narrativo` / caso "no hay brechas" (líneas 43-47): sin cambios — un trámite sin brechas sigue sin `brechas` y sin necesidad de resolver ningún componente.
- Cualquier archivo de `backend/app/engine/reglas/*.yaml`, `reglas_loader.py`, `componentes_oss.yaml`, `costos_oss.yaml`, o cualquier archivo de `backend/app/ia/`/`backend/app/jobs/` — ya cubierto como restricción dura de la tarea madre, reafirmado aquí para que quede en el mismo documento que consume `ia-automatizacion`.

### 5.1 Tests nuevos esperados en `backend/tests/test_engine_plantillas.py`

Los 3 tests ya existentes (`test_sin_nada_detecta_todas_las_brechas_mx`, `test_nivel_maximo_sin_brechas_no_fuerza_recomendacion`, `test_firma_electronica_cita_norma_correcta_por_pais`) deben seguir pasando sin modificación — son la prueba de regresión de que el wiring no altera qué brechas se detectan ni su contenido ya existente. Tests nuevos a agregar, todos usando las mismas fixtures `RESPUESTAS_SIN_NADA`/`RESPUESTAS_NIVEL_MAXIMO` ya definidas en el archivo:

1. **`test_brecha_incluye_componente_recomendado_con_datos_del_catalogo`** — para la brecha `firma_electronica_habilitada` (presente en `RESPUESTAS_SIN_NADA`), verificar que `brecha["componente_recomendado"]["nombre_componente"] == "DSS (Digital Signature Service) — esig/dss"` y `brecha["componente_recomendado"]["licencia"] == "LGPL-2.1"`.
2. **`test_componente_recomendado_selecciona_moneda_segun_pais`** — generar `contenido` para `"mx"` y para `"uy"` sobre la misma brecha (ej. `documentos_digitalizados`, categoría `gestor_expediente_electronico`) y verificar: (a) `moneda_local_codigo` es `"MXN"` en el primer caso y `"UYU"` en el segundo; (b) el valor de `costo_infraestructura.moneda_local` coincide exactamente con `costo_infraestructura_mxn`/`costo_infraestructura_uyu` de `costos_oss.yaml` para esa categoría; (c) `costo_infraestructura.usd` es igual en ambos países (mismo valor `costo_infraestructura_usd`).
3. **`test_costo_no_verificado_se_preserva_literal`** — para cualquier brecha cuya categoría tenga `costo_implementacion_*` en `"[NO VERIFICADO]"` (las 6 categorías cumplen esto hoy), verificar que `componente_recomendado["costo_implementacion"]["moneda_local"] == "[NO VERIFICADO]"` exactamente (no `"0"`, no cadena vacía, no clave ausente).
4. **`test_nota_advertencia_presente_solo_cuando_el_catalogo_la_declara`** — para la brecha `interoperabilidad` en `"uy"` (categoría `conector_interoperabilidad`, que sí tiene `nota` en `componentes_oss.yaml`), verificar que `nota_advertencia` no es `None` y contiene la palabra `"PDI"`; para la brecha `mecanismo_identidad` (categoría `identidad_federada`, sin `nota` en el YAML), verificar que `nota_advertencia is None`.
5. **`test_wiring_no_altera_deteccion_de_brechas`** — test de regresión explícito: comparar el conjunto de `variable`s detectadas y la longitud de `brechas` para `RESPUESTAS_SIN_NADA`/`RESPUESTAS_NIVEL_MAXIMO` contra los mismos valores ya afirmados por los tests existentes, confirmando que agregar `componente_recomendado` no cambia cuántas ni cuáles brechas se generan (protege la regla dura de la sección 6).

Se recomienda además (no exigido explícitamente por el encargo, pero consistente con que `catalogo_loader.py` es un módulo nuevo con lógica propia de merge/caché) un archivo de test independiente, `backend/tests/test_engine_catalogo_loader.py`, que pruebe `cargar_catalogo_oss()` y `componente_recomendado_para()` de forma aislada (las 6 categorías resuelven, un `categoria_catalogo` inexistente devuelve `None`, un `pais` fuera de `{"mx","uy"}` devuelve `None`) — análogo en función a cómo `test_engine_plantillas.py` ya prueba `plantillas.py` por separado de cualquier prueba directa de `reglas_loader.py`.

## 6. Confirmación de los límites de responsabilidad de este wiring

Se confirma explícitamente, como pide la tarea madre:

- **Este wiring no decide el índice de madurez.** `engine/madurez.py` sigue siendo la única pieza que calcula `indice_madurez`; nada en `catalogo_loader.py` ni en el cambio descrito a `plantillas.py` lee ni escribe ese cálculo, y `componente_recomendado_para` no recibe `respuestas` como parámetro (solo `categoria_catalogo` y `pais`) — no tiene forma de influir en el índice aunque quisiera.
- **Este wiring no decide qué brecha aplica ni qué acción le corresponde.** Esa decisión sigue siendo exclusivamente de `criterio_se_cumple` (evaluado contra `respuestas`) y del catálogo ya existente en `backend/app/engine/reglas/*.yaml` (`paso_administrativo`/`paso_tecnico`/`paso_organizacional`/`categoria_catalogo` ya fijados ahí). El wiring actúa estrictamente después de que esa decisión ya se tomó: recibe `accion.categoria_catalogo` como un dato de solo lectura y lo usa exclusivamente como llave de búsqueda en un catálogo distinto (componente + costo) — nunca cambia si la brecha aplica, nunca cambia cuál acción describe, nunca agrega ni quita una brecha de la lista.
- En una frase: este wiring **enriquece** una brecha ya decidida con datos de referencia (componente OSS + costo paramétrico); no **decide** nada que no estuviera ya decidido por `engine/reglas/*.yaml` + `engine/madurez.py`.

## 7. Pendientes y `[NO VERIFICADO]` de este documento

- `[NO VERIFICADO]` — el texto exacto de la etiqueta de UI para el tratamiento visual de `"[NO VERIFICADO]"` (sección 3, punto 3) no se fija aquí; es responsabilidad de quien implemente la vista de frontend (fase posterior, fuera de alcance), en el mismo lenguaje llano que ya exige `docs/ux-brief.md` línea 8.
- No se propone ni se decide en este documento si `docs/backend-schema.md`/`docs/PRD.md` deben editarse para registrar la limitación de la sección 4 — se deja como recomendación explícita para quien tenga permiso de escritura sobre esos documentos (esta tarea es de solo lectura sobre `docs/`).
- No se agrega ningún campo de versión del catálogo OSS (ej. `version_catalogo_oss`) dentro de `componente_recomendado`: `contenido` ya es un snapshot inmutable calculado una sola vez al generar el plan (`docs/backend-schema.md` línea 74, `plan_modernizacion.contenido` jsonb) y persistido tal cual — igual que el resto de la estructura enriquecida (`paso_administrativo`, etc.), que tampoco lleva un sello de versión por campo; la reproducibilidad ya la gobiernan `diagnostico_tramite.version_motor` y `plan_modernizacion.version` a nivel de todo el documento, no campo por campo.

## Documentos relacionados

`docs/TRD.md` (formato del catálogo de reglas, línea 74 sobre separación de costeo), `docs/backend-schema.md` (columna `contenido` de `plan_modernizacion`), `entregables/fase-2/catalogo-componentes-oss.md`, `entregables/fase-2/catalogo-costos-oss.md`, `entregables/fase-2/asistente-captura-f1.md` (mismo estándar de rigor y formato), `backend/app/engine/catalogo/componentes_oss.yaml`, `backend/app/engine/catalogo/costos_oss.yaml`, `backend/app/engine/reglas_loader.py`, `backend/app/engine/plantillas.py`, `backend/app/ia/generador_plan.py`, `backend/tests/test_engine_plantillas.py`.
