# Variables de contexto y capacidad institucional — cierre del hueco de fidelidad de `docs/PRD.md` línea 31

Entregable de diseño puro (sin código), mismo estándar que `entregables/fase-2/asistente-captura-f1.md` e `entregables/fase-2/identificacion-gobierno-login.md`: cada afirmación cita ruta + línea/sección verificada directamente antes de escribir este documento; lo no verificado queda marcado `[NO VERIFICADO]`.

## 0. Hechos verificados antes de decidir

- `docs/PRD.md` línea 31 (el hueco exacto que este documento cierra): "Cuestionario de diagnóstico por trámite (documentos papel/digital, pagos en línea, firma-e, interoperabilidad, datos personales, mecanismo de identidad/acceso ciudadano — Llave MX / ID Uruguay / propio / ninguno) + variables de contexto (población, personal, presupuesto TIC) + variables de capacidad institucional (área TIC, conectividad, normativa local)." La estructura de la propia oración ya separa tres bloques distintos con "+": el cuestionario por trámite, las variables de contexto, y las variables de capacidad institucional — no los mezcla como un único cuestionario.
- `docs/PRD.md` línea 31 aclara "personal **total**", relevante para el punto 2.4 de este documento (distinguirla de "funcionarios involucrados por trámite"). `docs/PRD.md` línea 18, "Usuario objetivo": "El funcionario público que responde el diagnóstico — no el ciudadano final, no el tecnólogo" — mismo criterio de diseño ("funcionario municipal promedio, no el tecnólogo") aplicado abajo.
- `entregables/fase-1/matriz-normativa.md` línea 29 (tabla "Variables nuevas", fila 1): "Existencia de Autoridad Municipal de Simplificación y Digitalización (5 áreas) y Enlace designado" — México: LNETB art. 11 (Autoridad Local de Simplificación y Digitalización, transversal, con al menos 5 áreas: Simplificación, Digitalización, Atención Ciudadana, Buenas prácticas regulatorias, Desarrollo de Soluciones Tecnológicas) + art. 14 (el Enlace, nivel mínimo director general), `[VERIFICADO]`. Uruguay: sin equivalente obligatorio; variable sustituta "existencia de convenio vigente con Agesic" (Ley 17.930 art. 72, creación de Agesic, + Decreto 184/015 art. 1, asesoría a "Entidades Públicas, estatales y no estatales"; Convenio Marco Agesic–Congreso de Intendentes), `[VERIFICADO]`.
- `entregables/fase-1/matriz-normativa.md` línea 31 (tabla "Variables nuevas", fila 3): "Funcionarios involucrados por trámite (proxy de carga burocrática)" — variable **distinta** de "personal total del gobierno"; ancla LNETB art. 24 (principio de simplificación, sin métrica explícita de número de funcionarios). Esta es la variable ya prevista como insumo de entrada por trámite, no una de las 6 que este documento diseña.
- `entregables/fase-1/teoria-de-cambio.md` línea 140: "El cuestionario debe preguntar explícitamente por la existencia de esta Autoridad y de este Enlace como variable de capacidad institucional (ya incorporada en `entregables/fase-1/matriz-normativa.md`), y el plan de modernización debe dirigir sus recomendaciones de gobernanza hacia esa Autoridad, no hacia una 'oficina de sistemas' genérica que puede no existir con ese nombre ni ese mandato legal."
- `entregables/fase-1/teoria-de-cambio.md` línea 43 (matriz de indicadores, eslabón "Problema — brecha de capacidades"): el indicador ya fijado es exactamente "México: existencia de Autoridad Municipal de Simplificación y Digitalización y Enlace designado... Uruguay: existencia de convenio vigente con Agesic", medido en "Línea base" (una sola vez, no remedido por trámite).
- `entregables/fase-1/teoria-de-cambio.md` línea 50 (eslabón "Impacto — eficiencia del gasto"): el proxy ya fijado es "variación en 'funcionarios involucrados por trámite'" — no usa "personal total del gobierno" como proxy, reforzando que son variables distintas con roles distintos.
- `docs/PRD.md` línea 22: "Interlocutor institucional según país: en Uruguay, la intendencia (Ley 19.272); en México, el ayuntamiento a través de su Autoridad Municipal de Simplificación y Digitalización (LNETB art. 11)." — el PRD ya nombra la Autoridad como interlocutor institucional, fuera incluso de la matriz normativa.
- `docs/app-flow.md` líneas 8-16 (mapa de rutas): 5 rutas (`/login`, `/`, `/tramites/:tramiteId/diagnostico`, `/tramites/:tramiteId/plan`, `/seguimiento`); ninguna cubre un perfil de gobierno — vacío de especificación real, no solo de código.
- `docs/ux-brief.md` líneas 62-77 (pantallas 1-5): ninguna de las 5 pantallas documentadas menciona población, personal, presupuesto TIC, área TIC, conectividad, normativa local o Autoridad/Enlace/convenio Agesic.
- `docs/backend-schema.md` líneas 22-30 (tabla `tenant`): columnas actuales `id`, `nombre`, `pais`, `clave` (agregada por la migración `0002`, ver `backend/app/models/tenant.py` líneas 17-23), `created_at` — sin ninguna columna de contexto o capacidad institucional.
- `backend/app/engine/reglas_loader.py` línea 63: `cargar_catalogo()` itera `for archivo in sorted(REGLAS_DIR.glob("*.yaml"))` — cualquier archivo `.yaml` nuevo en `backend/app/engine/reglas/` se incorpora automáticamente al catálogo, sin tocar este módulo (relevante para la sección 3.1).
- `backend/app/engine/reglas_loader.py` líneas 17-25 (`AccionPais`, `@dataclass(frozen=True)`): los 7 campos (`paso_administrativo`, `paso_tecnico`, `paso_organizacional`, `prerrequisitos`, `por_que_importa`, `fuente_normativa`, `categoria_catalogo`) son obligatorios, sin default — cualquier regla nueva debe rellenar los 7, incluida `categoria_catalogo` como `str` (relevante para la sección 3.1, por qué se opta por una categoría "vacía" en vez de `null`).
- `backend/app/engine/madurez.py` líneas 96-97 (docstring de `calcular_indice_madurez`): "`proteccion_datos_incompleta` NO participa aquí: es transversal (`datos_personales.yaml`), no gatilla un nivel específico del índice" — mismo patrón que se reutiliza en la sección 3.1 para la variable de gobernanza.
- `backend/app/engine/reglas/datos_personales.yaml` líneas 1-2: comentario "transversal, no gatilla un nivel específico del índice... es requisito de cumplimiento en cualquier nivel >= 1" — precedente directo del mismo patrón de regla transversal que se propone en la sección 3.1.
- `entregables/fase-2/catalogo-oss-wiring.md` sección 1 (línea 26): "su valor es un objeto, o `null` en el único caso defensivo de que `categoria_catalogo` no exista en el catálogo combinado... el mecanismo de resolución debe degradar a `null`, nunca lanzar una excepción". Sección 2.1: "`componente_recomendado_para`... busca `categoria_catalogo` en `cargar_catalogo_oss()`; si no existe, devuelve `None`." — mecanismo ya diseñado y aprobado que se reutiliza sin cambio en la sección 3.1 de este documento.
- `backend/app/api/deps.py` líneas 17-42: `TokenData` (`usuario_id`, `tenant_id`, `rol`), `get_current_token` (decodifica JWT vía `HTTPBearer`) y `get_db` (abre sesión con RLS ya fijado vía `tenant_scoped_session(token.tenant_id)`) — mecanismo de autenticación que reutiliza sin cambios el endpoint propuesto en la sección 5.
- `backend/app/api/tramites.py` líneas 14, 65-74 (`crear_tramite`): patrón ya usado de un endpoint autenticado que nunca acepta `tenant_id` en el body — lo toma siempre de `token.tenant_id` (`Tramite(tenant_id=token.tenant_id, ...)`) — mismo patrón que se reutiliza en el contrato de la sección 5.
- `backend/alembic/versions/0002_tenant_clave.py` (íntegro): única migración posterior a la inicial, patrón de cabecera (`revision`, `down_revision`, docstring con referencia al entregable de diseño) que la migración `0003` propuesta en la sección 4.2 reutiliza.
- `backend/alembic/versions/0001_initial_schema.py` líneas 156-168: el patrón real de RLS del proyecto usa `ENABLE ROW LEVEL SECURITY` seguido de `FORCE ROW LEVEL SECURITY` antes de crear la policy, con este comentario explícito en el archivo: "FORCE (no solo ENABLE) es necesario: por default Postgres exime al dueño de la tabla de RLS, y en este docker-compose el usuario de la app es el mismo que corrió la migración (el dueño). Sin FORCE, la policy sería 'la única barrera' solo de nombre — la app la saltaría en silencio." La versión abreviada de `docs/backend-schema.md` líneas 120-129 no menciona `FORCE`; la migración `0003` de la sección 4.2 de este documento sigue el patrón real de `0001`, no la versión abreviada.

## 1. Nivel de captura: gobierno completo, no por trámite

**Decisión: las 7 variables de este documento (las 6 de `docs/PRD.md` línea 31 más la ya investigada de Autoridad/Enlace/convenio Agesic) se capturan una sola vez por gobierno (tenant), nunca por trámite.**

Análisis propio, sin dar por sentada ninguna lectura previa:

1. **Lectura literal de cada variable.** "Población", "personal total" y "presupuesto TIC" (contexto) describen al gobierno como organización, no a un trámite específico — un municipio tiene una sola población, un solo presupuesto TIC anual y un solo total de personal, con independencia de cuántos trámites catalogue. Preguntar "población" 12 veces (una por trámite catalogado) produciría la misma respuesta 12 veces, violando el principio de "funcionario municipal promedio" (`docs/PRD.md` línea 18): captura redundante sin ningún beneficio de precisión.
2. **"Área TIC", "conectividad" y "normativa local emitida" (capacidad institucional) son también hechos del gobierno, no del trámite.** La existencia de un área/responsable de sistemas, el estado de la conectividad de las oficinas, y si el gobierno ya emitió su propia normativa de simplificación/digitalización son condiciones que preceden y encuadran a cualquier trámite particular — no son atributos que cambien trámite por trámite (a diferencia de, por ejemplo, `firma_electronica_habilitada`, que sí puede ser verdadera para un trámite y falsa para otro dentro del mismo gobierno).
3. **La variable ya investigada (Autoridad/Enlace/convenio Agesic) confirma el mismo patrón por diseño normativo, no por analogía forzada.** LNETB art. 11 (`entregables/fase-1/matriz-normativa.md` línea 29) crea la Autoridad como "transversal" — una sola autoridad para todo el municipio, no una por trámite — y `entregables/fase-1/teoria-de-cambio.md` línea 43 ya la mide "en Línea base" (una vez), no en cada trámite.
4. **El propio texto de `docs/PRD.md` línea 31 separa los tres bloques con "+".** "Cuestionario de diagnóstico por trámite (...) + variables de contexto (...) + variables de capacidad institucional (...)" no dice "cuestionario de diagnóstico por trámite, que incluye además..." — la estructura gramatical ya distingue el cuestionario por trámite (un bloque) de los otros dos bloques, que no llevan la calificación "por trámite".
5. **Ningún estado de la máquina de estados de trámite depende de estas variables.** `docs/backend-schema.md` línea 49 (`tramite.estado`, enum `sin_iniciar/en_progreso/diagnosticado/generando_plan/plan_listo`) y `docs/app-flow.md` líneas 41-49 (máquina de estados) no mencionan ninguna de estas 7 variables como condición de transición — si fueran por trámite, se esperaría que aparecieran en esa máquina de estados junto a las 6 variables sí capturadas hoy en `diagnostico_tramite.respuestas`.

## 2. Lista final de variables y tipo de dato

Contrato preciso, empezando por la variable con sustento normativo completo ya investigado.

### 2.1 `autoridad_gobernanza_digital` (boolean)

- **Pregunta al funcionario (texto por país, mismo campo subyacente — mismo patrón que `proteccion_datos_incompleta`, cuyo `criterio_deteccion` es único para ambas ramas y cuyo `por_que_importa` es textualmente idéntico en ambas ramas, aunque el paso administrativo concreto sí difiere por país, `backend/app/engine/reglas/datos_personales.yaml` línea 5 (`criterio_deteccion`, único para ambas ramas) y líneas 12/20 (`por_que_importa`, texto idéntico en ambas ramas)):**
  - México: "¿Existe la Autoridad Municipal de Simplificación y Digitalización (LNETB art. 11, con sus 5 áreas sustantivas) y su Enlace designado (art. 14)?"
  - Uruguay: "¿Existe un convenio vigente con Agesic para asesoría en transformación digital?"
- **Tipo:** `boolean`, nullable hasta que se responda.
- **Sustento normativo:** ya completo, ver sección 0 (`entregables/fase-1/matriz-normativa.md` línea 29).

### 2.2 `poblacion_total` (integer)

- **Pregunta:** "¿Cuál es la población total del gobierno local (último dato oficial disponible)?"
- **Tipo:** `integer`, `>= 0`, nullable.
- Fuente normativa directa: ninguna — es un dato de contexto de escala, no una obligación legal (ver sección 3.2).

### 2.3 `presupuesto_tic_anual` (decimal)

- **Pregunta:** "¿Cuál es el presupuesto anual destinado a tecnologías de la información del gobierno local?"
- **Tipo:** `numeric(14,2)`, `>= 0`, nullable. Moneda implícita por `tenant.pais` (MXN si `mx`, UYU si `uy`) — mismo criterio ya usado en `entregables/fase-2/catalogo-oss-wiring.md` sección 1.3 para no exponer una columna de moneda redundante cuando ya existe `tenant.pais` como fuente de verdad.

### 2.4 `personal_total_gobierno` (integer)

- **Pregunta:** "¿Cuál es el total de personal del gobierno local (todas las áreas, no solo el trámite)?"
- **Tipo:** `integer`, `>= 0`, nullable.
- **Nombre de campo deliberadamente distinto de "personal" a secas**, para no confundirse con "funcionarios involucrados por trámite" (`entregables/fase-1/matriz-normativa.md` línea 31), variable ya prevista como insumo por trámite y fuera del alcance de este documento. Son dos números distintos: uno es la nómina completa del gobierno (esta variable), el otro es cuántos de esos funcionarios atienden un trámite específico (variable ya existente en el diseño del cuestionario por trámite).

### 2.5 `area_tic_existe` (boolean)

- **Pregunta:** "¿El gobierno local cuenta con un área o responsable formalmente designado de tecnologías de la información?"
- **Tipo:** `boolean`, nullable.
- **Distinción deliberada frente a `autoridad_gobernanza_digital`:** en México, la Autoridad Local de Simplificación y Digitalización (LNETB art. 11) incluye un área de "Desarrollo de Soluciones Tecnológicas" entre sus 5 áreas sustantivas — pero esa área es un mandato de gobernanza formal (puede existir en el papel por obligación legal sin que haya, en la práctica, personal técnico ni infraestructura operando). `area_tic_existe` captura la capacidad técnica operativa real (¿hay alguien que administre sistemas/redes hoy?), distinta de la existencia formal de la Autoridad. Mantenerlas separadas evita el doble conteo que la propia matriz normativa ya evita en otro punto (`entregables/fase-1/matriz-normativa.md` línea 18, nota: "la autenticación vía Llave MX... se trata como variable de Identidad, no de Interoperabilidad, para evitar doble conteo en el índice").

### 2.6 `conectividad` (enum)

- **Pregunta:** "¿Cómo describiría la conectividad a internet de las oficinas donde se atienden trámites?"
- **Tipo:** enum de 3 valores: `estable`, `intermitente`, `sin_conexion`. Nullable.
- **Por qué enum de 3 valores y no boolean:** `backend/app/engine/reglas/firma_electronica.yaml` línea 10 ya usa el prerrequisito textual "Conectividad estable" como texto fijo (no capturado, no evaluado) en la rama `mx`. La realidad de conectividad de un municipio pequeño rara vez es binaria (funciona/no funciona) — es más frecuente que sea intermitente. Forzar un booleano reproduciría el mismo problema que ya motivó la sección 1 de `entregables/fase-2/asistente-captura-f1.md` (variables booleanas que fuerzan una realidad binaria sobre situaciones que no lo son) — aquí se resuelve en el diseño con un enum de 3 estados en vez de retrocorregirlo después con un campo de texto libre.

### 2.7 `normativa_local_emitida` (boolean)

- **Pregunta:** "¿El gobierno local ha emitido normativa propia de simplificación o digitalización (reglamento, decreto o resolución municipal/departamental)?"
- **Tipo:** `boolean`, nullable.

## 3. Uso del resultado — cuál genera una acción real del plan y cuál es contextual

### 3.1 `autoridad_gobernanza_digital` — SÍ genera una acción real: 7ª entrada candidata de `engine/reglas/`

`entregables/fase-1/teoria-de-cambio.md` línea 140 ya instruye, como decisión de producto previamente aprobada (no una decisión nueva de este documento): "el plan de modernización debe dirigir sus recomendaciones de gobernanza hacia esa Autoridad, no hacia una 'oficina de sistemas' genérica que puede no existir con ese nombre ni ese mandato legal." Esto es un mandato de wiring explícito, no una lectura libre. Se decide, por tanto, que esta variable sí produce una brecha→acción real, siguiendo exactamente el mismo formato de los 6 archivos ya existentes en `backend/app/engine/reglas/` (`docs/TRD.md`, formato ya fijado, confirmado en el encabezado de cada YAML leído en la sección 0).

**Contenido propuesto (ilustrativo, texto dentro de este documento — no se crea el archivo real):**

```yaml
# entregables/fase-2/variables-contexto-institucional.md, sección 3.1
version: "1.0"
variable: autoridad_gobernanza_digital
criterio_deteccion: "autoridad_gobernanza_digital == false"
acciones:
  mx:
    paso_administrativo: "Constituir o fortalecer la Autoridad Local de Simplificación y Digitalización con sus 5 áreas sustantivas (Simplificación; Digitalización; Atención Ciudadana; Buenas prácticas regulatorias; Desarrollo de Soluciones Tecnológicas) y designar al Enlace de Simplificación y Digitalización (nivel mínimo director general)"
    paso_tecnico: "No aplica un componente tecnológico específico — brecha de gobernanza institucional, no de adopción de software"
    paso_organizacional: "Formalizar el mandato de la Autoridad y del Enlace mediante acuerdo/bando municipal, y dirigir hacia esa Autoridad las recomendaciones de gobernanza del resto del plan"
    prerrequisitos: []
    por_que_importa: "Transversal a todos los trámites del gobierno — no bloquea un nivel específico del índice de madurez de ningún trámite (mismo tratamiento que proteccion_datos_incompleta, ver datos_personales.yaml), pero es el interlocutor institucional al que deben dirigirse las recomendaciones de gobernanza del plan"
    fuente_normativa: "LNETB art. 11 (Autoridad Local de Simplificación y Digitalización, 5 áreas) + art. 14 (Enlace, nivel mínimo director general)"
    categoria_catalogo: "gobernanza_institucional"
  uy:
    paso_administrativo: "Suscribir o renovar el convenio con Agesic para asesoría en transformación digital (Convenio Marco Agesic–Congreso de Intendentes)"
    paso_tecnico: "No aplica un componente tecnológico específico — brecha de gobernanza institucional, no de adopción de software"
    paso_organizacional: "Designar la contraparte técnica responsable del convenio dentro de la intendencia"
    prerrequisitos: []
    por_que_importa: "Transversal a todos los trámites del gobierno — mismo criterio que la rama mx; sin equivalente obligatorio uruguayo directo a la Autoridad mexicana, el convenio con Agesic es la variable sustituta ya identificada en la matriz normativa"
    fuente_normativa: "Ley 17.930 art. 72 (creación de Agesic) + Decreto 184/015 art. 1 (asesoría a Entidades Públicas)"
    categoria_catalogo: "gobernanza_institucional"
```

**Por qué `categoria_catalogo: "gobernanza_institucional"` y no `null` ni una de las 6 categorías ya existentes:**

- `backend/app/engine/reglas_loader.py` líneas 17-25 (`AccionPais`) tipa `categoria_catalogo` como `str` obligatorio, sin `| None` — usar `null` violaría el contrato de tipos de la dataclass tal como existe hoy, y este documento no está autorizado a proponer un cambio de código.
- Usar una de las 6 categorías ya cerradas (`modulo_cifrado_datos`, `gestor_expediente_electronico`, `modulo_firma_electronica`, `identidad_federada`, `conector_interoperabilidad`, `adaptador_pasarela_pago`) sería falso: esta brecha no recomienda ninguno de esos componentes OSS, es una acción organizacional pura.
- `"gobernanza_institucional"` es una cadena válida (`AccionPais.categoria_catalogo: str` no exige que la cadena exista en un catálogo cerrado) que, al no existir como llave en `componentes_oss.yaml`/`costos_oss.yaml`, hace que `componente_recomendado_para` (`entregables/fase-2/catalogo-oss-wiring.md` sección 2.1) "busque `categoria_catalogo` en `cargar_catalogo_oss()`; si no existe, devuelve `None`" — es decir, el mecanismo de degradación ya diseñado y aprobado produce automáticamente `componente_recomendado: null` para esta brecha, **sin ningún cambio de código** en `catalogo_loader.py`, `plantillas.py` ni `generador_plan.py`. Esto es consistente con que la acción es genuinamente organizacional, no tecnológica.

**Qué SÍ requiere un cambio de código (fuera de alcance de este documento, especificado para quien lo implemente):**

1. Crear el archivo real `backend/app/engine/reglas/autoridad_gobernanza_digital.yaml` con el contenido de arriba — `reglas_loader.py` línea 63 ya lo incorpora automáticamente al iterar `REGLAS_DIR.glob("*.yaml")`, sin tocar ese módulo.
2. **Fusionar el namespace de `contexto_institucional` con el de `diagnostico_tramite.respuestas` antes de evaluar el catálogo.** Hoy `criterio_se_cumple`/`generar_contenido_degradado`/`generar_contenido_llm` reciben únicamente el `dict` de `respuestas` de un trámite (`backend/app/engine/reglas_loader.py` línea 54; `backend/app/engine/plantillas.py`, `backend/app/ia/generador_plan.py`, ambos citados en `entregables/fase-2/catalogo-oss-wiring.md` sección 4). Para que `autoridad_gobernanza_digital == false` se evalúe, quien invoque la generación del plan debe construir el `dict` efectivo como `{**contexto_institucional_del_tenant, **respuestas_del_tramite}` antes de pasarlo al motor — el propio nombre de campo (`autoridad_gobernanza_digital`) no colisiona con ninguna de las 6 claves ya usadas hoy (`documentos_digitalizados`, `motor_pagos`, `firma_electronica_habilitada`, `interoperabilidad`, `proteccion_datos_incompleta`, `mecanismo_identidad`), así que la fusión es segura.
3. **No requiere subir `VERSION_MOTOR`** (`backend/app/engine/madurez.py` línea 24): esta variable no participa de `indice_madurez.yaml` (no es booleana de las 5 que gobiernan el índice, `backend/app/engine/madurez.py` líneas 88-97) — es transversal, mismo tratamiento que `proteccion_datos_incompleta` (línea 96-97 del mismo archivo). El campo `version: "1.0"` del YAML propuesto es metadato propio de esa regla, no ligado a `VERSION_MOTOR`.

**Limitación declarada, no resuelta aquí:** editar `contexto_institucional.autoridad_gobernanza_digital` después de que ya existen planes generados no dispara automáticamente la regeneración de esos planes — un plan solo se regenera cuando el funcionario reabre y reenvía el diagnóstico de ese trámite específico (`docs/app-flow.md` línea 61, mecanismo ya existente para cualquier corrección de respuesta). Como el dato de gobernanza vive en una pantalla distinta de la que dispara la regeneración (sección 5), esta asimetría debe declararse explícitamente para quien implemente, en el mismo espíritu que la asimetría `llm`/`degradado` ya declarada en `entregables/fase-2/catalogo-oss-wiring.md` sección 4.

### 3.2 Las 6 variables de `docs/PRD.md` línea 31 — descriptivas, sin acción propia (justificación una por una)

Ninguna de estas 6 variables gatilla una brecha→acción real en esta iteración. Se guardan y se muestran (perfil del gobierno, sección 5), pero no bloquean ni desbloquean ningún nivel del índice ni producen una entrada en `engine/reglas/`.

- **`poblacion_total`.** Ninguna norma citada en `entregables/fase-1/matriz-normativa.md` ni en los anexos de legislación liga un umbral de población a una obligación o acción diferenciada. Su único uso ya documentado es de escala/segmentación de usuario (`docs/PRD.md` línea 19, "municipio pequeño ~5,000 habitantes" como perfil de referencia), no un disparador normativo. Además, `backend/app/engine/reglas_loader.py` línea 40-56 (`_parse_criterio`/`criterio_se_cumple`) solo soporta comparación de igualdad/desigualdad contra un valor literal (`==`/`!=`), no umbrales numéricos (`>=`, `<`) — inventar un umbral de población sin sustento normativo, además de requerir extender el evaluador, sería fabricar un criterio sin fuente, exactamente lo que el estándar de esta casa prohíbe (`entregables/fase-2/catalogo-costos-oss.md` línea 5, "ninguna cifra sin fuente citada... nunca se inventa un número").
- **`presupuesto_tic_anual`.** Ningún documento del proyecto (`docs/PRD.md`, `docs/TRD.md`, `entregables/fase-2/catalogo-costos-oss.md`, `entregables/fase-2/catalogo-oss-wiring.md`) define una regla que compare este presupuesto contra el costo del plan para gatillar una acción distinta. Convertirlo en un criterio de brecha exigiría un umbral de "presupuesto insuficiente" arbitrario, lo cual viola el mandato de `docs/PRD.md` línea 32 ("criterios binarios verificables, no juicio subjetivo"): "suficiente" o "insuficiente" no es un hecho verificable de la misma naturaleza que "¿existe firma electrónica habilitada, sí o no?". Se mantiene descriptivo, mostrado junto al costo del plan (F5) para que el propio funcionario lo interprete, nunca evaluado por el motor.
- **`personal_total_gobierno`.** Es un dato de línea base para una futura razón (ej. % de personal dedicado a TIC) que ningún documento aprobado define todavía — el proxy de eficiencia del gasto que sí está ya fijado (`entregables/fase-1/teoria-de-cambio.md` línea 50) usa "funcionarios involucrados por trámite" (variable distinta, ver sección 2.4), no este total. Se mantiene descriptivo.
- **`area_tic_existe`.** A diferencia de `autoridad_gobernanza_digital`, no existe ningún documento ya aprobado (`entregables/fase-1/matriz-normativa.md`, `entregables/fase-1/teoria-de-cambio.md`) que instruya dirigir una recomendación del plan hacia esta variable específicamente, ni un ancla normativa que la ligue a una obligación puntual — la instrucción explícita de `teoria-de-cambio.md` línea 140 nombra la Autoridad/Enlace, no un "área TIC" genérica. Introducir aquí una 8ª regla sin ese mismo respaldo documental sería exactamente el tipo de deriva de alcance que `entregables/fase-1/teoria-de-cambio.md` sección 3.1 ya advierte evitar ("sin adelantarse a etapas posteriores"). Se mantiene descriptiva, y se deja registrado como candidata a una futura investigación normativa dedicada (análoga a la ya hecha para la Autoridad) si el piloto revela que es necesaria.
- **`conectividad`.** `backend/app/engine/reglas/firma_electronica.yaml` línea 10 (rama `mx`) y línea 18 (rama `uy`) ya listan "Conectividad estable" como texto fijo del campo `prerrequisitos` de una regla **ya aprobada y existente** — convertir `conectividad` en una variable evaluada que bloquee esa acción sería modificar una regla ya existente fuera del alcance autorizado de este documento (que solo puede proponer una regla candidata *nueva*, la de la sección 3.1, no alterar las 6 ya existentes). Se mantiene descriptiva; queda como nota para una tarea futura y separada la posibilidad de que `firma_electronica.yaml` sustituya ese texto fijo por una condición dinámica sobre esta variable.
- **`normativa_local_emitida`.** El indicador de "brecha de capacidades" ya fijado en `entregables/fase-1/teoria-de-cambio.md` línea 43 usa exclusivamente la Autoridad/Enlace (México) o el convenio Agesic (Uruguay) como indicador — no incluye "normativa local emitida" como un indicador adicional o sustituto. Agregarle una acción propia duplicaría el rol que ya cumple `autoridad_gobernanza_digital` sin un ancla normativa propia que lo distinga. Se mantiene descriptiva.

## 4. Impacto de esquema

### 4.1 Tabla nueva `contexto_institucional` (1:1 con `tenant`)

Se opta por una **tabla nueva**, no columnas agregadas a `tenant`, por tres razones:

1. `tenant` es "la tabla raíz que define el aislamiento" (`docs/backend-schema.md` línea 30, "Sin RLS") — agregar 7 columnas editables y de negocio a esa tabla mezclaría el rol de identidad/aislamiento con el de perfil de contexto, que sí necesita RLS propio (a diferencia de `tenant`).
2. El patrón ya usado en el proyecto para datos 1:1 opcionales y editables independientemente del ciclo de vida de otra entidad es una tabla propia con FK único (`plan_modernizacion` 1:1 lógico con la versión activa de un `diagnostico_tramite`, aunque con cardinalidad distinta) — no una alteración de la tabla padre.
3. Mantiene la migración `0003` **más simple y menos riesgosa que la `0002`**: una tabla nueva no tiene filas existentes que hacer *backfill* (a diferencia de `0002`, que sí necesitó tres pasos por las filas ya sembradas del piloto, `backend/alembic/versions/0002_tenant_clave.py` líneas 20-35) — aquí basta un `create_table`, sin ningún riesgo para datos ya persistidos.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | uuid, PK | |
| `tenant_id` | uuid, FK → tenant, **UNIQUE** | Fuerza la relación 1:1; lleva RLS igual que el resto de tablas con `tenant_id` (`docs/backend-schema.md` líneas 120-129) |
| `poblacion_total` | integer, nullable | `>= 0` si no nulo (constraint `CHECK`, ver 4.2) |
| `personal_total_gobierno` | integer, nullable | `>= 0` si no nulo |
| `presupuesto_tic_anual` | numeric(14,2), nullable | `>= 0` si no nulo; moneda implícita por `tenant.pais` |
| `area_tic_existe` | boolean, nullable | |
| `conectividad` | enum(`estable`,`intermitente`,`sin_conexion`), nullable | |
| `normativa_local_emitida` | boolean, nullable | |
| `autoridad_gobernanza_digital` | boolean, nullable | Única de las 7 con `criterio_deteccion` real, sección 3.1 |
| `actualizado_en` | timestamptz, nullable | `NULL` hasta el primer guardado; se reescribe en cada edición posterior (ver "editable" abajo) |
| `created_at` | timestamptz | `server_default=func.now()`, mismo patrón que `tenant.created_at` |

**Todas las columnas de negocio son nullable y editables en cualquier momento**, sin excepción — ninguna pantalla ni transición de `docs/app-flow.md` líneas 41-49 depende de que este perfil esté completo (confirmado en la sección 1, punto 5), así que no hay razón de producto para bloquear el guardado parcial ni impedir su corrección posterior. Esto es coherente con "Guardar y continuar después" ya usado en F1 (`docs/ux-brief.md` línea 69) — aquí no hace falta ni ese botón, porque no hay noción de cuestionario "incompleto" que bloquee nada: cada campo se guarda de forma independiente.

### 4.2 Migración `0003` (ilustrativa — no se crea el archivo real, restricción dura de esta tarea)

Mismo patrón de cabecera que `backend/alembic/versions/0002_tenant_clave.py` líneas 1-17:

```python
"""contexto_institucional: perfil de contexto y capacidad institucional del gobierno,
1:1 con tenant (entregables/fase-2/variables-contexto-institucional.md, sección 4)

Revision ID: 0003
Revises: 0002
Create Date: <fecha de implementación>

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conectividad_enum = postgresql.ENUM(
        "estable", "intermitente", "sin_conexion", name="conectividad_enum"
    )
    conectividad_enum.create(op.get_bind())

    op.create_table(
        "contexto_institucional",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"), nullable=False
        ),
        sa.Column("poblacion_total", sa.Integer(), nullable=True),
        sa.Column("personal_total_gobierno", sa.Integer(), nullable=True),
        sa.Column("presupuesto_tic_anual", sa.Numeric(14, 2), nullable=True),
        sa.Column("area_tic_existe", sa.Boolean(), nullable=True),
        sa.Column("conectividad", conectividad_enum, nullable=True),
        sa.Column("normativa_local_emitida", sa.Boolean(), nullable=True),
        sa.Column("autoridad_gobernanza_digital", sa.Boolean(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_contexto_institucional_tenant", "contexto_institucional", ["tenant_id"]
    )
    op.create_check_constraint(
        "ck_contexto_institucional_poblacion_no_negativa",
        "contexto_institucional",
        "poblacion_total IS NULL OR poblacion_total >= 0",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_personal_no_negativo",
        "contexto_institucional",
        "personal_total_gobierno IS NULL OR personal_total_gobierno >= 0",
    )
    op.create_check_constraint(
        "ck_contexto_institucional_presupuesto_no_negativo",
        "contexto_institucional",
        "presupuesto_tic_anual IS NULL OR presupuesto_tic_anual >= 0",
    )
    # Política RLS — mismo patrón que backend/alembic/versions/0001_initial_schema.py líneas 156-168
    op.execute("ALTER TABLE contexto_institucional ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE contexto_institucional FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON contexto_institucional "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid);"
    )


def downgrade() -> None:
    op.drop_constraint("ck_contexto_institucional_presupuesto_no_negativo", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_personal_no_negativo", "contexto_institucional")
    op.drop_constraint("ck_contexto_institucional_poblacion_no_negativa", "contexto_institucional")
    op.drop_constraint("uq_contexto_institucional_tenant", "contexto_institucional")
    op.drop_table("contexto_institucional")
    postgresql.ENUM(name="conectividad_enum").drop(op.get_bind())
```

Sin ningún `UPDATE`/backfill: es una tabla nueva sin filas — ningún tenant existente del piloto queda en un estado inconsistente, a diferencia de `0002` (que sí necesitó backfill porque alteraba una tabla con filas ya sembradas).

`downgrade()` simétrico, mismo criterio que `0002` (líneas 38-40 de esa migración).

El modelo ORM `backend/app/models/contexto_institucional.py` (nuevo archivo) y su registro en `backend/app/models/__init__.py` quedan especificados por esta tabla, no se implementan en este entregable de diseño.

## 5. Dónde se captura en el producto

### 5.1 Pantalla nueva: "Perfil del gobierno"

**Decisión: ruta nueva `/gobierno/perfil`, no un paso de onboarding bloqueante ni una sección dentro de una pantalla ya existente.**

Justificación:

- No es un paso de onboarding obligatorio porque, como ya se confirmó en la sección 1 punto 5, ninguna transición de la máquina de estados de `docs/app-flow.md` líneas 41-49 depende de este perfil — forzarlo como paso bloqueante inventaría una regla de producto no pedida por ningún documento existente.
- No encaja como sección dentro de una pantalla ya existente: la pantalla 2 ("Panel resumen", `docs/ux-brief.md` línea 65-66) está descrita como "tarjeta superior con el índice de madurez global... debajo, tabla de trámites" — insertar 7 campos de perfil ahí rompería el mandato de esa pantalla ("Sin gráficas de tendencia en el MVP — un solo número por trámite, no series de tiempo", línea 66) al convertirla en un formulario además de un resumen. La pantalla 3 (cuestionario F1) es explícitamente **por trámite** (`docs/ux-brief.md` línea 68-71) — ya se descartó en la sección 1 que estas variables sean por trámite.
- Una pantalla nueva y dedicada respeta el principio de "pantalla mínima" de cada pantalla individual (`docs/ux-brief.md` línea 63, aplicado ahí al login) sin sobrecargar ninguna de las 5 pantallas ya aprobadas con un objetivo distinto al que tienen hoy.

**Acceso:** nav superior (`docs/app-flow.md` línea 16) pasa de dos enlaces ("Inicio", "Seguimiento") a tres ("Inicio", "Perfil del gobierno", "Seguimiento") — sigue sin sidebar, 6 rutas totales no lo justifican (mismo criterio ya usado en `docs/app-flow.md` línea 16 para las 5 rutas actuales). Requiere sesión, igual que las demás rutas autenticadas; no requiere que ningún trámite esté diagnosticado ni ninguna otra precondición.

**Contenido de la pantalla (componentes ya aprobados en `docs/ux-brief.md` línea 58, sin agregar ningún componente nuevo):**
- Los 4 campos booleanos (`area_tic_existe`, `normativa_local_emitida`, `autoridad_gobernanza_digital`, y la pregunta de gobernanza con su texto condicionado por `tenant.pais`) como `RadioGroup` "Sí"/"No" — mismo componente y mismo patrón de pregunta cerrada ya usado en el cuestionario F1.
- `conectividad` como `Select` de 3 opciones — componente ya listado (`Input`/`Select`/`RadioGroup`, línea 58).
- `poblacion_total`, `personal_total_gobierno`, `presupuesto_tic_anual` como `Input` numérico.
- Un `Card` por bloque (contexto / capacidad institucional), mismo patrón que "resumen de índice" ya aprobado (línea 58, `Card`).
- Guardado por campo o por bloque (no hay noción de "enviar cuestionario completo" como en F1) — cada edición dispara el `PUT` de la sección 5.2 de forma independiente; no hay estado "incompleto" que bloquee nada, coherente con la sección 4.1.

`[NO VERIFICADO]` — el texto exacto de ayuda contextual bajo cada campo (mismo principio de "lenguaje llano" de `docs/ux-brief.md` línea 8) y si el guardado es por campo individual o por botón único de "Guardar perfil" al pie de la pantalla, quedan para la fase de implementación de frontend, siguiendo el mismo criterio ya usado en `entregables/fase-2/asistente-captura-f1.md` sección 6 (dejar la redacción final para esa fase, no fijarla de antemano en este documento).

### 5.2 Contrato de endpoints nuevos

**`GET /api/gobierno/contexto`** — nuevo router `backend/app/api/gobierno_contexto.py`, registrado en `backend/app/main.py` con el mismo patrón que los routers existentes (`docs/backend-schema.md` no lo describe, pero `entregables/fase-2/identificacion-gobierno-login.md` sección 3 ya fija el patrón de registro: import + `app.include_router(...)`).

- **Autenticado** (`get_current_token` + `get_db`, `backend/app/api/deps.py` líneas 24-42 — mismo patrón que `backend/app/api/tramites.py` líneas 17-22) — a diferencia de `GET /api/gobiernos/{clave}` (público, `entregables/fase-2/identificacion-gobierno-login.md` sección 3), este endpoint expone datos de negocio del tenant y debe requerir sesión.
- **Sin parámetros** — el `tenant_id` se toma de `token.tenant_id`, nunca de la URL ni del body (mismo patrón que `crear_tramite`, `backend/app/api/tramites.py` línea 71).
- **Response 200**, siempre (nunca 404 — mismo principio de "nunca un error visible al funcionario" ya aplicado en `entregables/fase-2/asistente-captura-f1.md` sección 2.1): si no existe fila para ese tenant todavía, se sintetiza el mismo shape con todos los campos de negocio en `null`.

```json
{
  "tenant_id": "<uuid>",
  "poblacion_total": null,
  "personal_total_gobierno": null,
  "presupuesto_tic_anual": null,
  "area_tic_existe": null,
  "conectividad": null,
  "normativa_local_emitida": null,
  "autoridad_gobernanza_digital": null,
  "actualizado_en": null
}
```

**`PUT /api/gobierno/contexto`** — mismo router, mismo requisito de autenticación.

- **Body:** mismo shape que el `Response` de `GET`, sin `tenant_id` ni `actualizado_en` (el backend los deriva/asigna). Todos los campos opcionales — un `PUT` puede actualizar un solo campo sin obligar a reenviar los demás (semántica de *upsert* parcial, ej. `PATCH`-like aunque el verbo HTTP sea `PUT` por simplicidad de un solo endpoint de escritura, sin distinguir creación de actualización).
- **Validación:** enteros `>= 0` para `poblacion_total`/`personal_total_gobierno`; numérico `>= 0` para `presupuesto_tic_anual`; uno de los 3 valores para `conectividad`; booleano para el resto — mismas reglas que los `CHECK` de la migración (sección 4.2), validados también en el esquema Pydantic del endpoint para devolver un error en lenguaje llano antes de tocar la base de datos (mismo principio de `docs/ux-brief.md` línea 63, "mensaje de error en lenguaje llano").
- **Comportamiento:** `INSERT ... ON CONFLICT (tenant_id) DO UPDATE` (o `SELECT` + `INSERT`/`UPDATE` explícito equivalente en SQLAlchemy) — `created_at` solo se asigna en el primer `INSERT`; `actualizado_en` se reescribe en cada `PUT` exitoso.
- **Response 200:** el objeto ya guardado, mismo shape que `GET`.

Ningún archivo de `backend/` ni `frontend/` fue creado ni modificado por este documento — quedan como especificación para la tarea de código correspondiente, igual que en `entregables/fase-2/identificacion-gobierno-login.md` sección 6.

## 6. Actualizaciones a los documentos de blueprint

Se editan los 4 documentos de blueprint, con la misma disciplina de cita de fuente que el resto de esta casa. El estado descrito abajo corresponde al contenido efectivamente presente en cada archivo al momento de entregar este documento:

- **`docs/PRD.md`**: en el punto 1 del alcance del MVP se agrega, al final de la oración que ya enumera el cuestionario por trámite más las variables de contexto y de capacidad institucional, la aclaración de que estas dos últimas (incluida la de gobernanza) se capturan una sola vez por gobierno (tenant), nunca por trámite, con referencia a este documento para el contrato completo. En el modelo conceptual de datos se agrega la entidad `contexto_institucional` a la lista de entidades principales, con referencia a este documento.
- **`docs/backend-schema.md`**: se agrega la sección de la tabla `contexto_institucional` (mismo formato que las demás tablas del documento, columnas de la sección 4.1 de este documento) inmediatamente después de la tabla `tenant`, y se agrega al diagrama de entidades (`mermaid`) la relación `TENANT ||--o| CONTEXTO_INSTITUCIONAL : perfila`.
- **`docs/app-flow.md`**: se agrega la ruta `/gobierno/perfil` al mapa de rutas ("Requiere sesión"), se actualiza la descripción de la nav superior para incluir el nuevo enlace ("Inicio", "Perfil del gobierno", "Seguimiento"), y se agrega el nodo y las transiciones correspondientes al diagrama de navegación (`mermaid`).
- **`docs/ux-brief.md`**: se agrega la pantalla 6, "Perfil del gobierno", después de la pantalla 5, con el contenido de componentes ya especificado en la sección 5.1 de este documento (los 4 campos booleanos como `RadioGroup`, `conectividad` como `Select`, los 3 campos numéricos como `Input`, un `Card` por bloque).

## 7. Pendientes y `[NO VERIFICADO]`

- `[NO VERIFICADO]` — el texto exacto de ayuda contextual y ayudas de validación (ej. formato del campo de presupuesto) de la pantalla "Perfil del gobierno" — queda para la fase de implementación de frontend.
- `[NO VERIFICADO]` — si conviene un botón único "Guardar perfil" vs. guardado por campo individual (autosave al perder foco) — ambos son compatibles con el contrato de la sección 5.2; se deja como decisión de UX de la fase de implementación, mismo criterio que `entregables/fase-2/asistente-captura-f1.md` sección 6 aplica a una decisión de UX equivalente.
- `[NO VERIFICADO]` — si el piloto revela que `area_tic_existe` sí necesita una acción propia del plan (candidata a una 8ª entrada de `engine/reglas/`), queda pendiente de una investigación normativa dedicada, análoga a la ya hecha para la Autoridad/Enlace en `entregables/fase-1/matriz-normativa.md` — no se fabrica esa investigación en este documento.
- No aplica ningún hallazgo de bilingüismo normativo adicional más allá del ya declarado en la sección 2.1 (texto de pregunta condicionado por `tenant.pais` para `autoridad_gobernanza_digital`, mismo mecanismo ya usado por `mecanismo_identidad` en `entregables/fase-2/asistente-captura-f1.md` sección 2.2) — el resto de las 6 variables de `docs/PRD.md` línea 31 no requieren parametrización por país (población, personal, presupuesto TIC, área TIC, conectividad y normativa local se preguntan igual en ambos países).

## Documentos relacionados

`docs/PRD.md`, `docs/backend-schema.md`, `docs/app-flow.md`, `docs/ux-brief.md`, `docs/TRD.md`, `entregables/fase-1/matriz-normativa.md`, `entregables/fase-1/teoria-de-cambio.md`, `entregables/fase-2/asistente-captura-f1.md`, `entregables/fase-2/identificacion-gobierno-login.md`, `entregables/fase-2/catalogo-componentes-oss.md`, `entregables/fase-2/catalogo-costos-oss.md`, `entregables/fase-2/catalogo-oss-wiring.md`, `backend/app/engine/reglas_loader.py`, `backend/app/engine/madurez.py`, `backend/app/models/tenant.py`, `backend/app/api/deps.py`, `backend/app/api/tramites.py`, `backend/alembic/versions/0002_tenant_clave.py`.
