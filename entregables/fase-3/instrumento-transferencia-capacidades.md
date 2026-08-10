# Instrumento de transferencia de capacidades — diseño de la sesión, evaluación y evidencia

Versión 1 · 10 de agosto de 2026
Entregable de diseño puro (sin código). Cierra el pendiente que `entregables/fase-1/teoria-de-cambio.md` (Sección 6) dejó explícitamente para esta fase: *"el diseño detallado del instrumento de formación, sus materiales y su plan de medición corresponden a la Fase 3"*. Ese documento fija el compromiso conceptual y el criterio de aceptación; este documento los convierte en un instrumento aplicable — agenda de la sesión, formulario de autoevaluación, checklist de demostración práctica y acta de entrega-recepción — sin reabrir ninguna decisión ya tomada ahí.

## 0. Hechos verificados antes de diseñar

- `entregables/fase-1/teoria-de-cambio.md` Sección 6 fija, sin ambigüedad, **3 objetivos de la capacitación** (la contraparte técnica debe poder, sin soporte del Laboratorio ni de ningún implementador original): (1) operar la plataforma (cargar un trámite, ejecutar un diagnóstico, leer el panel de seguimiento); (2) interpretar el índice de madurez y el plan sin depender de una explicación externa cada vez; (3) mantener el catálogo brecha→acción editable del país correspondiente.
- La misma sección fija el **criterio de evidencia documental mínimo**: registro verificable de que la transferencia ocurrió — como mínimo, evidencia de asistencia a la sesión y un mecanismo de autoevaluación de autonomía operativa antes/después — y deja la forma exacta (encuesta, checklist, acta de entrega-recepción) para este documento.
- `docs/PRD.md` ("Fuera de alcance"): *"Onboarding self-service sin asistencia — el piloto asume una contraparte técnica designada por la intendencia (requisito de la convocatoria), no un funcionario anónimo llegando sin contexto."* — la sesión de capacitación no es una mejora opcional, es la forma en que el piloto cumple ese requisito de la convocatoria.
- `entregables/one-pager-intendencias.md` ("Qué le pedimos a la intendencia"): la carta de interés **designa una contraparte técnica o institucional responsable del seguimiento** — es la persona (o el rol) destinataria de esta capacitación; el instrumento no necesita inventar a quién se dirige, ya está definido aguas arriba.
- `docs/runbook-alta-gobierno.md`: hoy quien opera el alta de un gobierno, resetea contraseñas, etc. es "quien opera el despliegue (la contraparte técnica designada)" — confirma que la contraparte técnica ya es, por diseño, la usuaria operativa de estos comandos, no solo del frontend.
- `docs/PRD.md` ("Requisitos no funcionales"): el catálogo brecha→acción "vive como texto estructurado editable (no hardcodeado en código) para que alguien sin conocimiento de programación pueda mantenerlo — es un catálogo finito por diseño (~10-15 entradas por país)". Verificado directamente contra `backend/app/engine/reglas/firma_electronica.yaml`: es YAML plano con campos en español (`paso_administrativo`, `paso_tecnico`, `paso_organizacional`, `prerrequisitos`, `por_que_importa`, `fuente_normativa`) — editable con cualquier editor de texto, sin sintaxis de programación real, solo indentación YAML.
- El propio equipo de este proyecto validó hoy, en vivo y de punta a punta contra un despliegue real (sin FusionCube, en un equipo cualquiera con Docker), el recorrido completo login → alta de trámite → diagnóstico → plan generado — el mismo recorrido que el objetivo 1 de la capacitación exige que la contraparte técnica pueda repetir sola. Ese recorrido, ya ejecutado y confirmado hoy, es la base directa de la Sección 3 (agenda) y la Sección 5 (checklist de demostración) de este documento — no se diseña a ciegas.

## 1. A quién se dirige y cuándo ocurre

**Destinatario: la contraparte técnica designada en la carta de interés** (`entregables/one-pager-intendencias.md`), no un funcionario genérico. Si la carta designa más de una persona (ej. un responsable institucional y un enlace técnico operativo), la sesión cubre a ambos, pero el checklist de demostración práctica (Sección 5) solo lo firma quien de verdad va a operar la plataforma día a día — firmar sin poder demostrar la tarea no es evidencia, es formalidad vacía.

**Momento: al cierre del piloto, con datos reales ya cargados.** No es una sesión de "producto terminado en abstracto" — se hace sobre el gobierno real ya dado de alta (`docs/runbook-alta-gobierno.md`), con al menos un diagnóstico real ya completado, para que la contraparte practique sobre su propio caso, no sobre un ejemplo genérico. Justificación: el objetivo 2 (interpretar el índice y el plan) es imposible de evaluar de verdad sobre datos sintéticos que la contraparte no reconoce como propios.

## 2. Los 3 objetivos (heredados, no reinventados)

Este documento no fija objetivos nuevos — reproduce los 3 ya decididos en `entregables/fase-1/teoria-de-cambio.md` Sección 6, porque toda la agenda y el instrumento de evaluación de abajo se organizan exactamente alrededor de ellos, en el mismo orden:

| # | Objetivo | Verbo observable (para el checklist) |
|---|---|---|
| O1 | Operar la plataforma | Ejecutar sin ayuda: alta de trámite, diagnóstico, lectura del panel de seguimiento |
| O2 | Interpretar el índice y el plan | Explicar en sus propias palabras qué significa el índice de su gobierno y por qué el plan recomienda lo que recomienda |
| O3 | Mantener el catálogo brecha→acción | Editar una entrada real del catálogo de su país sin ayuda ni error de sintaxis |

## 3. Agenda de la sesión (formato y duración)

**Formato: presencial o videollamada con pantalla compartida, nunca un video grabado sin interacción** — los 3 objetivos son de *hacer*, no de *ver hacer*; una grabación no permite verificar el checklist de la Sección 5 en el momento. Duración total: **2 horas**, en 3 bloques:

| Bloque | Duración | Contenido | Objetivo que cubre |
|---|---|---|---|
| 1 | 45 min | Recorrido guiado por la plataforma sobre el gobierno real de la contraparte: login → alta de un trámite nuevo → cuestionario → plan generado → panel de seguimiento. El facilitador narra, la contraparte repite cada paso en su propia sesión. | O1 |
| 2 | 30 min | Lectura conjunta del índice de madurez y de 2-3 brechas del plan ya generado — el facilitador pregunta "¿por qué crees que el plan recomienda esto?" antes de explicar, para que la contraparte practique la interpretación, no solo la escuche. | O2 |
| 3 | 30 min | Apertura de un archivo real de `backend/app/engine/reglas/*.yaml` de su país en un editor de texto simple; la contraparte edita un campo (ej. `por_que_importa` de una brecha ya conocida) y confirma que el cambio se refleja en un nuevo diagnóstico. | O3 |
| — | 15 min | Autoevaluación post-sesión (Sección 4) + firma del checklist (Sección 5). | Evidencia |

**Requisito previo a la sesión:** el mismo acceso ya documentado en `docs/runbook-alta-gobierno.md` — terminal con `docker compose` sobre el servidor del piloto — debe estar disponible para la contraparte *durante* la sesión, no solo para el operador original. Si la contraparte no tiene ese acceso todavía, otorgárselo es un prerrequisito de esta sesión, no un tema aparte — sin acceso real, O1 y O3 no se pueden demostrar, solo describir.

## 4. Autoevaluación de confianza (pre/post)

Formulario corto, mismo cuestionario antes y después de la sesión, escala 1-5 ("1 = nada seguro/a de poder hacerlo solo/a" — "5 = totalmente seguro/a"). Mide percepción, no desempeño real — por eso se complementa con el checklist de demostración (Sección 5), nunca sustituye a él.

```
AUTOEVALUACIÓN DE AUTONOMÍA OPERATIVA — DiagMuni
Gobierno: ______________________   Momento: [ ] Antes de la sesión   [ ] Después de la sesión
Nombre de quien responde: ______________________   Fecha: ____________

Para cada afirmación, marca del 1 (nada seguro/a) al 5 (totalmente seguro/a):

1. Puedo dar de alta un trámite nuevo y completar su diagnóstico sin ayuda.        1  2  3  4  5
2. Puedo leer el panel de seguimiento y saber en qué estado está cada acción.     1  2  3  4  5
3. Puedo explicarle a otro funcionario qué significa el índice de madurez
   de mi gobierno y por qué el plan recomienda lo que recomienda.                1  2  3  4  5
4. Sabría dónde encontrar y cómo editar el catálogo de acciones de mi país
   si necesitara corregir o actualizar una recomendación.                        1  2  3  4  5
5. Si el Laboratorio o el equipo que construyó DiagMuni deja de estar
   disponible, puedo seguir operando la plataforma sin su ayuda.                 1  2  3  4  5

Comentario abierto (opcional): _______________________________________________
```

**Criterio de lectura, no de aprobación/reprobación:** una autoevaluación "post" que no sube frente a la "pre" en las preguntas 1-4 es una señal de que la sesión no cumplió su objetivo — motivo para repetir el bloque correspondiente antes de cerrar el piloto, no para ocultarlo en el reporte final. La pregunta 5 mide la percepción de independencia real (causal de descarte (c), `entregables/fase-1/teoria-de-cambio.md` Sección 4.2) — es la más importante de las 5.

## 5. Checklist de demostración práctica (evidencia fuerte, no autorreporte)

A diferencia de la Sección 4 (percepción), esto es observación directa: el facilitador marca cada fila **solo** si la contraparte técnica ejecutó la tarea sola, sin que el facilitador tocara el teclado ni le dictara el siguiente clic.

```
CHECKLIST DE DEMOSTRACIÓN PRÁCTICA — DiagMuni
Gobierno: ______________________   Fecha: ____________
Contraparte técnica evaluada: ______________________
Facilitador: ______________________

Objetivo 1 — Operar la plataforma
[ ] Inició sesión con sus propias credenciales.
[ ] Dio de alta un trámite nuevo (nombre real, no de prueba).
[ ] Completó y envió el cuestionario de diagnóstico de ese trámite.
[ ] Localizó el plan generado y el panel de seguimiento sin indicaciones.

Objetivo 2 — Interpretar el índice y el plan
[ ] Explicó en sus propias palabras qué significa el índice de madurez actual
    de su gobierno (no solo leyó el número en voz alta).
[ ] Señaló, para al menos una brecha del plan, por qué esa acción corresponde
    a esa brecha (sin que el facilitador lo explicara primero).

Objetivo 3 — Mantener el catálogo brecha→acción
[ ] Ubicó, sin ayuda, el archivo YAML correspondiente a una brecha de su país.
[ ] Editó un campo de texto de ese archivo y guardó el cambio sin error de
    sintaxis (indentación/comillas correctas).
[ ] Confirmó que el cambio se refleja en un diagnóstico nuevo generado tras
    la edición.

Resultado: [ ] Los 3 objetivos demostrados   [ ] Objetivo(s) pendiente(s): ___________
Firma de la contraparte técnica: ______________   Firma del facilitador: ______________
```

**Un objetivo marcado como pendiente no cierra el piloto en silencio.** Sección 7 fija qué pasa en ese caso.

## 6. Acta de entrega-recepción (código y datos)

Documento corto, firmado por ambas partes al cierre del piloto, que deja constancia de lo que `entregables/fase-1/teoria-de-cambio.md` Sección 4.1 ya fija como principio (los datos pertenecen al gobierno, nunca al Laboratorio) — el acta es la evidencia de que ese principio se ejecutó, no solo se declaró.

```
ACTA DE ENTREGA-RECEPCIÓN — Piloto DiagMuni
Gobierno: ______________________   Fecha de cierre del piloto: ____________

Se hace constar que:

1. El código de DiagMuni es software de código abierto (Apache 2.0, repositorio
   público) — no requiere ninguna entrega de licencia ni cesión de derechos;
   el gobierno puede operarlo, modificarlo y redistribuirlo desde hoy.
2. Los datos generados durante el piloto (diagnósticos, planes, seguimiento)
   quedan en la base de datos del despliegue del gobierno, aislados por
   tenant_id — el Laboratorio y el equipo implementador no conservan copia
   propia ni acceso posterior a esos datos salvo autorización explícita
   y puntual del gobierno.
3. Las credenciales de acceso al servidor y a la base de datos (o su
   reemplazo, si se rotan al cierre del piloto) quedan exclusivamente en
   poder de la contraparte técnica designada.
4. Se completó la sesión de capacitación de la Sección 3 de este documento,
   con checklist de demostración práctica adjunto (Sección 5).

Firma de la contraparte técnica: ______________   Firma del Laboratorio: ______________
```

**Nota de alcance:** si al cierre del piloto el servidor sigue siendo operado temporalmente por el Laboratorio (ej. mientras el gobierno tramita su propia infraestructura), el punto 3 se declara explícitamente como pendiente con fecha de traspaso comprometida — nunca se marca como cumplido si no lo está.

## 7. Criterio de aceptación de la salvaguarda

La transferencia de capacidades se considera cumplida para un gobierno piloto cuando existen, archivados junto al resto de la documentación del piloto, los 3 artefactos de este instrumento:

1. Autoevaluación pre y post (Sección 4), ambas completadas por la misma persona.
2. Checklist de demostración práctica (Sección 5) con los 3 objetivos marcados como demostrados.
3. Acta de entrega-recepción (Sección 6) firmada.

**Si el checklist queda con un objetivo pendiente:** no se cierra el piloto — se agenda una segunda sesión corta (solo sobre el objetivo pendiente) antes de firmar el acta de entrega-recepción. Esto es exactamente lo que `entregables/fase-1/teoria-de-cambio.md` Sección 6 ya anticipó: *"su ausencia es motivo suficiente para no dar por cumplida la salvaguarda... en la validación final"* — este documento solo hace operativo ese criterio ya fijado, no lo relaja.

## 8. Qué NO resuelve este documento

- **No diseña un manual de usuario completo de la plataforma.** La agenda de la Sección 3 se apoya en el recorrido ya validado en vivo hoy (login → trámite → diagnóstico → plan → seguimiento) y en la documentación técnica ya existente (`docs/runbook-alta-gobierno.md`, `docs/runbook-despliegue.md`) — si en el futuro se decide producir un manual ilustrado o un video de referencia, es una mejora aparte, no un prerrequisito de este instrumento.
- **No resuelve el riesgo de admisibilidad de `entregables/fase-1/teoria-de-cambio.md` Sección 3.4** (si la convocatoria exige comunidad de uso preexistente) — ese pendiente sigue abierto con RIL, sin relación con la transferencia de capacidades.
- **No construye ningún código nuevo.** Los 3 artefactos (Secciones 4, 5, 6) son plantillas de papel/documento a imprimir o completar en una sesión — no hay ninguna pantalla, endpoint ni formulario digital nuevo que agregar a `frontend/` o `backend/` para este instrumento. Si en el futuro se quisiera digitalizar la autoevaluación (ej. un Google Form), es una decisión operativa del equipo que ejecute el piloto, no un requisito de este diseño.
- **No fija quién es la contraparte técnica** — eso ya lo resuelve la carta de interés (`entregables/one-pager-intendencias.md`), este documento solo la recibe como dato de entrada.

## 9. Resumen de archivos entregados

- `entregables/fase-3/instrumento-transferencia-capacidades.md` (nuevo) — este documento.
- `entregables/README.md` (editado) — se agrega la fila de Fase 3.

Ningún archivo de `frontend/` ni `backend/` fue modificado — este entregable es, en su totalidad, diseño de proceso e instrumentos de evaluación, no código.

## Documentos relacionados

`entregables/fase-1/teoria-de-cambio.md` (Sección 6, compromiso y criterio original), `entregables/one-pager-intendencias.md` (carta de interés y contraparte técnica), `docs/PRD.md` (requisitos no funcionales y fuera de alcance), `docs/runbook-alta-gobierno.md`, `docs/runbook-despliegue.md`, `backend/app/engine/reglas/*.yaml` (catálogo que la contraparte debe poder mantener).
