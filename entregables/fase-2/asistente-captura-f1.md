# Asistente de captura F1 — definición del campo de texto libre

Versión 1 · 31 de julio de 2026 · Agente: `transformacion-digital`
Entregable de diseño puro (sin código), asignado como bloqueante de E4 antes de que `ia-automatizacion` reciba el brief de construcción (`entregables/plan.md`, fila "E4-diseño"). Resuelve el vacío de especificación real detectado por el coordinador: `docs/PRD.md` línea 26 y `docs/TRD.md` línea 93 dan por sentado que existe un campo de texto libre que los LLM "clasifican", pero ningún documento de blueprint (`docs/backend-schema.md`, `docs/ux-brief.md`, `docs/app-flow.md`) ni el catálogo ya transcrito a YAML (`backend/app/engine/reglas/*.yaml`) definen ese campo. Mismo estándar de esta casa que en `entregables/fase-2/modelo-diagnostico.md`: cada afirmación cita ruta + línea/sección; lo no verificado queda marcado `[NO VERIFICADO]`.

## 0. Insumos verificados antes de decidir

Antes de proponer el campo, se releyeron y confirmaron directamente (no de memoria) los siguientes hechos, porque la decisión de los puntos 1-4 depende de ellos:

- Las 6 variables de trámite y sus tipos, tal como están implementadas hoy en `backend/app/engine/reglas/*.yaml`: `documentos_digitalizados` (bool, `documentos_papel_digital.yaml` línea 3), `motor_pagos` (bool, `motor_pagos.yaml` línea 3), `firma_electronica_habilitada` (bool, `firma_electronica.yaml` línea 3), `interoperabilidad` (bool, `interoperabilidad.yaml` línea 3), `proteccion_datos_incompleta` (bool, `datos_personales.yaml` línea 4), `mecanismo_identidad` (string enum, `identidad_acceso.yaml` línea 3-4, valores confirmados en `docs/PRD.md` línea 31: "Llave MX / ID Uruguay / propio / ninguno").
- `backend/app/engine/reglas_loader.py` líneas 54-56, función `criterio_se_cumple`: evalúa `respuestas.get(clave) == valor_esperado` sobre un `dict` plano. No valida que `respuestas` tenga exactamente esas 6 claves ni rechaza claves adicionales — una clave nueva en el mismo diccionario es invisible para el motor mientras no se llame `clave` igual a una de las 6 ya usadas por algún YAML.
- `backend/app/schemas/diagnostico.py` líneas 7-17: `DiagnosticoGuardar.respuestas` y `DiagnosticoEnviar.respuestas` son `dict` sin sub-esquema Pydantic fijo — no hay una lista cerrada de claves permitidas a nivel de contrato API.
- `backend/app/engine/madurez.py` líneas 28-46: el índice depende de `documentos_digitalizados`, `motor_pagos`, `firma_electronica_habilitada` (por valor booleano) y de `interoperabilidad`/`mecanismo_identidad` (por booleano y por `!= "ninguno"`, respectivamente) — nunca por *cuál* valor no-"ninguno" tiene `mecanismo_identidad`. Confirmado también en `backend/app/engine/reglas/identidad_acceso.yaml`: el `criterio_deteccion` (línea 4) solo dispara la acción cuando el valor es exactamente `"ninguno"`; para cualquier otro valor (`"llave_mx"`, `"id_uruguay"`, `"propio"`, o, hipotéticamente, cualquier otra cadena) no se genera acción y el índice no distingue entre esos casos.
- `docs/PRD.md` línea 74: una de las métricas de éxito del piloto ya definidas es "% de preguntas respondidas con evidencia" — no hay hoy ningún campo que capture "evidencia" textual; es un requisito de producto ya declarado y sin mecanismo de captura.

## 1. Qué campo de texto libre existe en el cuestionario

**Decisión: un campo opcional de "aclaración" (texto libre, `Textarea`) adjunto a cada uno de los 6 `Card` de pregunta ya definidos en `docs/ux-brief.md` línea 68-69 ("Un `Card` por pregunta") — no un campo único de "observaciones" al final del cuestionario.** Con una excepción: en la pregunta de `mecanismo_identidad`, la misma aclaración se vuelve **obligatoria** cuando el funcionario selecciona una quinta opción nueva, "Otro, especifique", agregada al `RadioGroup` que hoy solo contempla las 4 opciones de `docs/PRD.md` línea 31 (Llave MX / ID Uruguay / propio / ninguno).

Justificación contra el propósito del cuestionario (`docs/PRD.md` línea 18, "Usuario objetivo... no el tecnólogo"; `docs/ux-brief.md` línea 8, principio 1, "Sin jerga técnica, en ningún estado de la interfaz"):

- **Por qué "por pregunta" y no un solo campo global de observaciones al final.** Un campo único y genérico rompe la trazabilidad que el propio producto exige: `docs/PRD.md` F8 ("Trazabilidad normativa") liga cada variable a su norma, y la métrica de línea 74 pide "% de preguntas respondidas con evidencia" — evidencia *por pregunta*, no un bloque de texto sin relación clara con cuál de las 6 variables describe. Un funcionario de mostrador que escribe una sola nota al final del formulario, sin que quede ligada a la pregunta que la motivó, obliga a quien lea el diagnóstico después (otro funcionario, el auditor, el propio Laboratorio) a adivinar a qué variable se refiere — exactamente el tipo de ambigüedad que el índice binario-verificable (`docs/PRD.md` línea 32) busca evitar. Adjuntar la aclaración al mismo `Card` de la pregunta (mismo patrón de UI ya aprobado, sin pantalla ni componente nuevo salvo `Textarea`) resuelve esto sin inventar una sección nueva.
- **Por qué es necesario en las 6 variables, no solo en una.** Las 5 variables booleanas (`documentos_digitalizados`, `motor_pagos`, `firma_electronica_habilitada`, `interoperabilidad`, `proteccion_datos_incompleta`) fuerzan una realidad binaria sobre situaciones que en un municipio pequeño rara vez son limpias — ej. "tenemos firma electrónica, pero solo para dos de los cinco documentos del expediente", o "cobramos en línea solo para una modalidad del trámite, las demás siguen en caja". Un funcionario sin formación técnica (`docs/PRD.md` línea 18) no tiene por qué saber si eso cuenta como "sí" o "no" para efectos del índice — y forzarlo a decidir sin poder explicar el matiz degrada la calidad del dato de entrada que el motor determinista después trata como verdad absoluta. El texto libre no cambia el hecho de que la variable se sigue capturando como booleano cerrado (el índice exige eso, ver `backend/app/engine/madurez.py`); solo da un lugar para que la ambigüedad quede documentada en vez de perderse.
- **Por qué `mecanismo_identidad` necesita, además, una opción "Otro, especifique".** A diferencia de las 5 variables booleanas, aquí la limitación no es un matiz sobre un valor binario: es la ausencia real de una opción cerrada válida. `docs/PRD.md` línea 31 fija 4 valores (Llave MX / ID Uruguay / propio / ninguno) — pero un municipio puede operar, por ejemplo, un mecanismo de identidad compartido con otros municipios de su región, o uno heredado de un programa estatal/departamental distinto de los 4 nombrados, que no es realmente "propio" (de ese gobierno) ni "ninguno" (si existe) ni las dos opciones nacionales. Forzar a "propio" o "ninguno" en ese caso produce un dato falso, no solo impreciso. "Otro, especifique" resuelve el problema real de captura que el brief pide resolver explícitamente (mencionado como ejemplo en el encargo del coordinador) sin inventar una variable nueva ajena al catálogo de 6.

## 2. Categorías de clasificación y uso del resultado

El encargo plantea dos alternativas — (a) el texto alimenta directamente una variable existente, o (b) es un campo de solo contexto que nunca toca el índice — y pide no asumir cuál es correcta. **Decisión: ambas, en roles distintos y secuenciales, nunca de forma automática.** El rol por defecto de toda aclaración es (b); el rol (a) solo se activa como una *sugerencia* que requiere confirmación humana explícita antes de guardarse — nunca hay una ruta en la que el LLM escriba directamente sobre una variable del catálogo.

### 2.1 Rol por defecto — (b), contexto/evidencia, nunca toca el índice

Toda aclaración capturada (en cualquiera de las 6 preguntas) se guarda siempre como texto de apoyo, ligada a la variable que la motivó. Esto por sí solo ya cumple la métrica de `docs/PRD.md` línea 74 ("% de preguntas respondidas con evidencia") sin necesitar ninguna llamada a LLM — si la capa de IA no está disponible (sin API key, timeout, sin conectividad), la aclaración igual se guarda tal cual la escribió el funcionario, exactamente con el mismo principio de "nunca un error visible al funcionario" ya usado en E2/E3 (`docs/TRD.md` línea 96).

### 2.2 Rol activado — (a), sugerencia sobre una variable existente, con confirmación humana obligatoria

Cuándo se activa:
- **Siempre** cuando el funcionario elige "Otro, especifique" en `mecanismo_identidad` (ahí la aclaración es obligatoria y el valor final de la variable todavía no existe — no hay "valor cerrado" que reconciliar, solo un texto a clasificar).
- **Opcionalmente** en las 5 variables booleanas, solo cuando el funcionario sí escribió una aclaración: el texto se clasifica para detectar si contradice el valor cerrado que el mismo funcionario ya seleccionó (ej. marcó "No" en `firma_electronica_habilitada` pero escribió "usamos firma digital para todos los documentos desde 2024").

Categorías de clasificación (fijas, ruta `economico` — ver punto 4):

- **Para las 5 variables booleanas**, una de: `consistente` (el texto no contradice el valor marcado — resultado por defecto/fail-safe), `posible_contradiccion_hacia_si`, `posible_contradiccion_hacia_no`, `no_concluyente` (el texto es ambiguo — se trata igual que `consistente`: no se sugiere nada).
- **Para `mecanismo_identidad`** (cuando se eligió "Otro"), una de las 4 categorías ya existentes en el catálogo más una de escape: `llave_mx` (solo ofrecida como candidata si `tenant.pais == "mx"`), `id_uruguay` (solo si `tenant.pais == "uy"`), `propio`, `ninguno`, `no_clasificable`. La restricción por país replica, en la capa de IA, el mismo particionamiento por `mx`/`uy` que ya usa el catálogo determinista (`docs/TRD.md` líneas 56-71, cada YAML tiene una rama `mx` y una `uy`) — es la aplicación de la restricción "Bilingüismo normativo" (`docs/PRD.md` línea 70) a este campo: nunca se le ofrece a un tenant mexicano "id_uruguay" como clasificación posible, ni viceversa.

**Mecanismo de confirmación (explícito, no implícito, tal como pide el encargo):**

1. El funcionario escribe la aclaración. Al continuar (salir del `Card` o intentar enviar el cuestionario), si hay texto y la ruta `economico` está disponible, se invoca la clasificación.
2. Si la clasificación sugiere un valor **distinto** al que el funcionario ya marcó (o, en el caso de "Otro", sugiere cualquiera de las 4 categorías originales), la interfaz muestra la sugerencia en lenguaje llano — ej. "Según su descripción, esto parece corresponder a: *Con firma electrónica habilitada*. ¿Es correcto?" — con dos acciones igual de visibles: **confirmar** (el valor sugerido reemplaza al marcado, o resuelve el "Otro" pendiente) o **mantener/corregir manualmente** (el funcionario decide otra cosa, incluida su respuesta original).
3. **Nada se guarda en la variable del catálogo sin ese paso 2.** El backend nunca persiste un valor de `documentos_digitalizados`, `motor_pagos`, `firma_electronica_habilitada`, `interoperabilidad` o `mecanismo_identidad` que provenga de la clasificación sin que el funcionario haya pulsado "confirmar" — el contrato de guardado (`DiagnosticoGuardar`/`DiagnosticoEnviar`, `backend/app/schemas/diagnostico.py` líneas 7-17) no cambia: sigue siendo el funcionario, a través del mismo formulario, quien produce el `dict` de `respuestas` final.
4. Si la clasificación falla, no está disponible, o devuelve `no_concluyente`/`no_clasificable`: no se muestra ninguna sugerencia (fail-safe hacia "no hacer nada", ver 2.3). En el caso específico de "Otro" en `mecanismo_identidad`, como el motor exige un valor entre los 4 originales para calcular el índice (`backend/app/engine/madurez.py` línea 43, con default `"ninguno"` si la clave falta), el cuestionario **no puede marcarse como completo** mientras el funcionario no elija manualmente una de las 4 opciones cerradas. **Esta es una validación nueva que introduce este documento, no un comportamiento ya existente**: hoy `backend/app/api/diagnosticos.py` (`enviar_diagnostico`, líneas 59-87) no valida presencia de ninguna clave requerida en `respuestas` — acepta cualquier `dict` — y `backend/app/engine/madurez.py` línea 43 aplica el default `"ninguno"` a `mecanismo_identidad` si la clave falta, sin bloquear nada. Por lo tanto, E4/fase F debe implementar esta validación en el formulario de F1 (bloqueo de UI) y se recomienda además una validación mínima equivalente en el endpoint `enviar_diagnostico` (rechazar el envío si quedó un flujo de "Otro" abierto sin resolver), para no depender exclusivamente del frontend. "Guardar y continuar después" (`docs/ux-brief.md` línea 69) sigue disponible en todo momento, nada se pierde.

**Relación con la regla dura del proyecto (no negociable):** `docs/PRD.md` línea 26 ("Nunca calculan el índice") y la regla dura de fase E (`entregables/plan.md` línea 35, "nada dentro de `engine/` importa de `ia/`") se preservan exactamente igual que en E2/E3: el módulo de clasificación (futuro `backend/app/ia/asistente_captura.py`, E4) nunca escribe en `engine/`, nunca calcula `indice_madurez`, y nunca decide una acción del plan — solo propone una etiqueta que un humano confirma o descarta antes de que exista como respuesta. La analogía con el patrón ya usado en E3 (`backend/app/ia/verificador.py` líneas 35-37: cualquier fallo de la llamada de auditoría "se trata como verificación NO aprobada", nunca se asume éxito por defecto) es real pero **no idéntica**, y se declara así explícitamente para no sobre-prometer: en E3, quien concilia la salida del LLM es código determinista (`plan_job.py` compara contra `contenido` ya producido por `engine/`) porque existe una referencia objetiva contra la cual auditar una narrativa. En E4 no existe esa referencia objetiva — la aclaración describe una realidad municipal que nadie más que el propio funcionario puede confirmar —, así que quien concilia aquí es una persona, no otro tramo de código determinista. Es el mismo principio ("el LLM propone, nunca decide solo"), aplicado con el mecanismo de conciliación que el caso permite.

### 2.3 Sesgo de fallo (fail-safe) de este módulo

A diferencia de `verificador.py` (E3), donde cualquier fallo de la llamada se trata como "verificación NO aprobada" (rechazo estricto, `backend/app/ia/verificador.py` líneas 29-40), aquí el sesgo de fallo es "no sugerir nada" — el peor caso posible es que una aclaración quede guardada solo como texto de apoyo (rol 2.1) sin haber sido clasificada, lo cual es exactamente el comportamiento que tendría el sistema si la clasificación no existiera. Nunca hay un caso en el que un fallo de la clasificación bloquee el guardado del cuestionario (salvo el caso ya descrito de "Otro" sin resolver, que se bloquea por falta de un valor requerido, no por el fallo del LLM en sí — el funcionario siempre puede resolverlo eligiendo manualmente).

## 3. Impacto de esquema

**Declaración explícita: este diseño no requiere ninguna migración de Alembic.** La aclaración se guarda como una clave nueva, `aclaraciones` (objeto anidado, una entrada opcional por variable), dentro de la misma columna `respuestas` (jsonb) de `diagnostico_tramite` que ya existe (`docs/backend-schema.md` línea 60). Esto es correcto por tres razones ya verificadas en la sección 0, no supuestas:

1. `respuestas` ya es `jsonb` (`docs/backend-schema.md` línea 60) — agregar una clave dentro de un documento JSON no requiere alterar la tabla.
2. `backend/app/schemas/diagnostico.py` (líneas 7, 11, 17) tipa `respuestas` como `dict` sin sub-esquema Pydantic estricto — no hay una lista cerrada de claves que romper ni extender a nivel de contrato API.
3. `backend/app/engine/reglas_loader.py` línea 54-56 (`criterio_se_cumple`) solo lee las claves que el criterio de cada YAML nombra explícitamente (`documentos_digitalizados`, `motor_pagos`, etc.) — una clave adicional como `aclaraciones` es invisible para el motor, confirmando que el `engine/` no requiere ningún cambio.

Forma concreta de la clave nueva (ejemplo ilustrativo, no normativo):

```json
{
  "documentos_digitalizados": true,
  "motor_pagos": false,
  "firma_electronica_habilitada": false,
  "interoperabilidad": false,
  "proteccion_datos_incompleta": true,
  "mecanismo_identidad": "propio",
  "aclaraciones": {
    "motor_pagos": "Solo aceptamos depósito bancario; no hay conciliación automática",
    "mecanismo_identidad": "Cédula digital propia de la intendencia, no es ID Uruguay"
  }
}
```

`mecanismo_identidad` sigue almacenando exclusivamente uno de los 4 valores canónicos ya definidos (`docs/PRD.md` línea 31) una vez resuelto el flujo de la sección 2.2 — "Otro" es un estado transitorio de la interfaz mientras se captura y clasifica la aclaración, nunca un valor final persistido en esa clave. Por lo tanto, tampoco es necesario tocar `backend/app/engine/reglas/identidad_acceso.yaml` ni su `criterio_deteccion`.

**Lo que sí es un detalle de implementación de E4 (no de este documento, no bloqueante para aprobarlo)**: el endpoint o extensión de endpoint que invoque la clasificación, y si ocurre síncrono desde la petición de guardado o mediante una llamada aparte del frontend al perder foco del `Textarea`. Se deja como nota para quien escriba el código de E4: dado que la clasificación es una tarea liviana (ver punto 4) y no un job de generación de plan, **no** debería requerir una nueva entrada en el enum `job.tipo` (`docs/backend-schema.md` línea 95, "Único tipo en el MVP: `generacion_plan`") — es una llamada síncrona de vida corta, análoga en perfil de latencia a la que ya hace `verificador.py` (`TIMEOUT_SEGUNDOS = 15`, `backend/app/ia/verificador.py` línea 49), no al job asíncrono de `generador_plan.py`.

## 4. Ruta LLM

**Confirmado: la clasificación usa la ruta `economico` (DeepSeek)**, conforme a `docs/TRD.md` línea 93: "F1 (asistente de captura, clasificación de texto libre) usa `economico` (DeepSeek)". Es coherente con el perfil de tarea ya usado para justificar la misma ruta en F9 (`backend/app/ia/verificador.py` líneas 9-13: "tarea liviana", "pide un veredicto... no prosa"): en ambos casos de este documento (clasificar una aclaración en una de 4-5 categorías fijas, o detectar consistencia/contradicción binaria) la salida esperada es una etiqueta corta, no redacción — el mismo tipo de tarea que F9, no el de F3 (`calidad`/Claude, reservado para prosa compleja con trazabilidad normativa, `docs/TRD.md` línea 94). No hay razón para usar `calidad` aquí, y usarlo violaría el principio de costo marginal bajo por diagnóstico (`CLAUDE.md`, "el costo marginal por diagnóstico tiende a cero"; principio general en `docs/PRD.md` línea 26, "Motor determinista primero, IA después") sin ninguna ganancia de calidad, dado que la tarea es de clasificación cerrada, no de composición de texto libre.

## 5. Actualizaciones a otros documentos

Se actualizaron, con la misma disciplina de cita de fuente:

- `docs/ux-brief.md`, línea 58 (lista de componentes): se agregó `Textarea` a los componentes reutilizados de shadcn/ui para el cuestionario F1, con nota de para qué se usa y referencia a este documento.
- `docs/ux-brief.md`, líneas 68-69 (pantalla 3, "Cuestionario de captura"): se agregó la descripción del campo de aclaración opcional por pregunta, la opción "Otro, especifique" en `mecanismo_identidad`, y el patrón de sugerencia-con-confirmación, referenciando este documento para el detalle del mecanismo.
- `docs/backend-schema.md`, línea 60 (tabla `diagnostico_tramite`, columna `respuestas`): se agregó la mención de la clave `aclaraciones` dentro del mismo jsonb, con referencia a este documento y aclaración explícita de que no implica migración.

(Ver diffs aplicados — mismos archivos, mismas líneas citadas arriba.)

## 6. Pendientes y `[NO VERIFICADO]`

- `[NO VERIFICADO]` — el texto exacto de los mensajes de UI para el banner de sugerencia/confirmación (sección 2.2, paso 2) no se fija en este documento; es responsabilidad de quien implemente F1/F3 del frontend (fase F, posterior a E4) redactarlo en el mismo lenguaje llano ya exigido por `docs/ux-brief.md` línea 8, sin inventar aquí una copia final no revisada por ese especialista.
- `[NO VERIFICADO]` — el prompt exacto que usará `asistente_captura.py` para producir la clasificación (equivalente al `_PROMPT_INSTRUCCIONES` de `generador_plan.py`/`verificador.py`) es tarea de E4 (código), no de este documento de diseño; aquí solo se fija el contrato de categorías de salida (sección 2.2) que ese prompt debe producir.
- `[NO VERIFICADO]` — si conviene además ofrecer la clasificación de "posible contradicción" (sección 2.2) de forma perezosa (solo al enviar el cuestionario completo) en vez de por pregunta (al salir de cada `Card`), por razones de latencia percibida en conexiones lentas (`docs/ux-brief.md` línea 10). Ambas son compatibles con el diseño de este documento; la decisión final de UX se deja a la fase F (frontend), no bloquea el código de E4.
- No aplica ningún hallazgo de bilingüismo normativo adicional más allá del ya declarado en la sección 2.2 (restricción de candidatas de `mecanismo_identidad` por `tenant.pais`) — el resto del diseño de este documento no introduce contenido regulatorio nuevo, solo un mecanismo de captura.

## Documentos relacionados

`docs/PRD.md`, `docs/TRD.md`, `docs/ux-brief.md`, `docs/app-flow.md`, `docs/backend-schema.md`, `entregables/fase-2/modelo-diagnostico.md`, `entregables/plan.md` (fila E4-diseño), `backend/app/ia/verificador.py`, `backend/app/ia/generador_plan.py`, `backend/app/ia/config.py`, `backend/app/engine/reglas_loader.py`, `backend/app/engine/madurez.py`, `backend/app/schemas/diagnostico.py`.
