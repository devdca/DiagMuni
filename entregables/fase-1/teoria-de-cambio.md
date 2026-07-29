# Teoría de cambio y validación de admisibilidad — DiagMuni

**Fecha:** 24 de julio de 2026 · **Insumos base:** `docs/anexo_legislacion_mx.md` y `docs/anexo_legislacion_uy.md` (corte de investigación 14-jul-2026), `entregables/fase-1/matriz-normativa.md`, `docs/PRD.md`, `docs/stack-tecnologico.md`.
**Advertencia de fuente:** este documento usa los anexos legislativos verificados como fuente normativa. Algunas referencias del planteamiento original del proyecto estaban desactualizadas (citaban LGMR, CONAMER e INAI, extintos desde 2024-2025 — ver `docs/anexo_legislacion_mx.md` sección 0); lo que se actualiza aquí es únicamente el fundamento jurídico, el alcance de producto no cambia.

---

## 1. Resumen ejecutivo

DiagMuni es una intervención pública, no solo un artefacto de software: busca reducir la opacidad y la fricción que enfrenta un ciudadano frente a un trámite municipal, y cerrar la brecha de capacidades técnicas que impide a un gobierno local pequeño planificar su propia modernización. La teoría de cambio de esta sección liga cada eslabón — problema, intervención, resultados, impacto — a un indicador verificable y a una fuente de datos concreta, para que el proyecto no dependa de una promesa aspiracional sino de mediciones que ya están, en su mayoría, ancladas a obligaciones normativas vigentes en México y Uruguay (Sección 2).

El proyecto se valida como admisible dentro del ciclo de gestión de retos del Laboratorio de Innovación Pública del INAP y dentro del Eje 1 (Atención Ciudadana) de GovTech Connect (Sección 3), con una advertencia de riesgo de admisibilidad que **no se resuelve en este documento** porque excede el mandato de este agente (Sección 3.4). Se fijan las salvaguardas de rectoría pública que impiden que el diagnóstico se convierta en herramienta de venta (Sección 4), se traduce el instrumento al lenguaje institucional correcto de cada país (Sección 5) y se declara el compromiso de transferencia de capacidades exigido por la convocatoria, con su criterio de evidencia (Sección 6).

---

## 2. Teoría de cambio explícita y medible

### 2.1 Cadena causal

```
PROBLEMA PÚBLICO              INTERVENCIÓN                    RESULTADOS                      IMPACTO
─────────────────             ──────────────                  ───────────                     ───────
Opacidad y fricción      →    Diagnóstico estandarizado   →   Trámites digitalizados     →    Confianza ciudadana
en trámites municipales        (índice de madurez 0-4,          (índice sube de línea            (medición fuera del
                                criterios binarios,               base a remedición)               alcance del piloto;
Brecha de capacidades     →    reproducibles)               →   Tiempos de resolución       →    hipótesis, no
del gobierno local              Plan a medida                    reducidos                        compromiso medido)
                                (brecha → acción, costeada,
                                verificada antes de                                          →    Eficiencia del
                                mostrarse)                   →   Plan adoptado                    gasto público
                                                                  (% de acciones iniciadas)        (proxy: menor carga
                                                                                                    burocrática por
                                                                                                    trámite)
```

Cada flecha implica un supuesto causal que el proyecto no controla directamente y que debe declararse (ver 2.3), porque la teoría de cambio de DiagMuni termina en el **plan**, no en su ejecución: el software diagnostica y recomienda, pero la implementación del plan es una decisión soberana del gobierno local (ver Sección 4).

### 2.2 Matriz de indicadores por eslabón

| Eslabón | Descripción | Indicador | Fuente de verificación | Momento de medición |
|---|---|---|---|---|
| **Problema — opacidad y fricción** | El ciudadano no puede saber de antemano qué documentos, costo, plazo o canal (presencial/digital) tiene un trámite | % de trámites del gobierno local con requisitos, costo total, plazo máximo y dependencia responsable publicados formalmente (LNETB art. 54, México; Ley 19.355 art. 76, Uruguay) | Cuestionario de diagnóstico (F1, `docs/PRD.md`), cotejado contra la publicación real del gobierno local si existe | Línea base, en la primera aplicación del instrumento |
| **Problema — brecha de capacidades** | El gobierno local carece de estructura, personal o convenio institucional para digitalizar sin asesoría externa | México: existencia de Autoridad Municipal de Simplificación y Digitalización y Enlace designado (LNETB arts. 11 y 14). Uruguay: existencia de convenio vigente con Agesic (Decreto 184/015, Convenio Marco Agesic–Congreso de Intendentes) | Variables de capacidad institucional del cuestionario (`docs/PRD.md` §"Alcance del MVP", punto 1) | Línea base |
| **Intervención — diagnóstico estandarizado** | Un funcionario de mostrador, sin conocimientos técnicos, obtiene un índice objetivo y reproducible | Número de trámites diagnosticados; tiempo de aplicación del instrumento; mismo dato de entrada produce siempre el mismo índice (F2, motor determinista versionado) | Métricas de éxito del piloto ya definidas en `docs/PRD.md` §"Métricas de éxito del piloto" | Durante la aplicación del piloto |
| **Intervención — plan a medida** | El gobierno recibe, no solo un diagnóstico, sino una ruta de acción costeada y verificada | % de brechas detectadas que reciben una acción del catálogo brecha→acción con costo, tiempo, prerrequisito y justificación (F3); % de esas acciones auditadas por el verificador (F9) antes de mostrarse al funcionario, sin acciones fuera de catálogo | Log de auditoría del diagnóstico (`docs/stack-tecnologico.md`, fila "Observabilidad"); `entregables/fase-2/modelo-diagnostico.md` | Al cierre de cada diagnóstico |
| **Resultado — trámites digitalizados** | El índice de madurez del trámite sube tras la implementación de acciones del plan | Diferencia entre índice de madurez inicial y en remedición (0-4, `docs/PRD.md` glosario) por trámite y agregado | Remedición con el mismo instrumento a 90 días (`docs/PRD.md` §"Métricas de éxito del piloto") | 90 días post-diagnóstico inicial |
| **Resultado — tiempos reducidos** | El trámite tarda menos en resolverse | Reducción del plazo de resolución declarado/observado por trámite (dato que la propia norma exige publicar: LNETB art. 54, fracc. IX; Ley 19.355 art. 76) | Comparación de plazo publicado/observado antes-después | 90 días post-diagnóstico inicial, sujeto a que el gobierno haya iniciado la acción |
| **Resultado — plan adoptado** | El gobierno local ejecuta, no solo archiva, el plan recibido | % de acciones del plan iniciadas a 90 días (métrica ya definida en `docs/PRD.md`); panel de seguimiento con semáforo por acción (F6) | Panel de seguimiento (F6, `docs/PRD.md`) | 90 días post-diagnóstico inicial |
| **Impacto — confianza ciudadana** | El ciudadano percibe menos fricción y más previsibilidad en su gobierno local | Proxy, no medición directa del piloto: variación en % de trámites con presencia y datos completos en el canal oficial (Portal Ciudadano Único en México, canal de trámites en línea en Uruguay); si el gobierno local decide levantarla, encuesta de satisfacción ciudadana | Fuera del control y del cronograma del piloto — se declara como hipótesis causal, no como compromiso de medición de esta postulación | Largo plazo, posterior al piloto |
| **Impacto — eficiencia del gasto** | Menos carga burocrática por trámite atendido | Proxy: variación en "funcionarios involucrados por trámite" (variable ya identificada en la matriz normativa, `entregables/fase-1/matriz-normativa.md`, como indicador indirecto de carga burocrática en ambos países) | Cuestionario de diagnóstico, remedición a 90 días si el plan avanzó | Largo plazo, parcialmente observable a 90 días |

### 2.3 Supuestos causales que el proyecto no controla (declarados, no resueltos aquí)

1. **Diagnóstico → resultado exige implementación real del plan por el gobierno local.** DiagMuni no ejecuta el plan; solo lo genera y lo audita (F9). Si el gobierno local no asigna presupuesto o personal a las acciones, el índice de madurez no cambia aunque el diagnóstico haya sido impecable. El panel de seguimiento (F6) mide adopción, no la garantiza.
2. **Resultado → impacto exige tiempo y variables fuera del proyecto.** La confianza ciudadana y la eficiencia del gasto dependen de factores macro (percepción general de la gestión, otros servicios públicos, contexto político) que ningún diagnóstico de trámites puede aislar por completo. Este documento no compromete una medición de impacto dentro del ciclo de vida de la postulación; solo declara la vía causal esperada y el proxy más cercano disponible.
3. **La reproducibilidad del índice (motor determinista) es condición necesaria pero no suficiente de confianza institucional.** Un índice técnicamente correcto no genera por sí mismo legitimidad si el gobierno local no comunica los resultados o no actúa sobre ellos — la trazabilidad normativa (F8) y el panel de seguimiento (F6) mitigan, pero no eliminan, este riesgo.

---

## 3. Validación de admisibilidad

### 3.1 Encaje en el ciclo de gestión de retos del Laboratorio INAP

| Etapa del ciclo | Estado de DiagMuni a la fecha de este documento | Entregable asociado |
|---|---|---|
| Recepción | Completada — el reto (opacidad/fricción y brecha de capacidades en trámites municipales) fue recibido y validado internamente por el Laboratorio antes del arranque del proyecto (20-jul-2026) | `README.md`, `docs/PRD.md` |
| Admisibilidad | **En curso — este documento es el instrumento de esa validación** | `entregables/fase-1/teoria-de-cambio.md` (este archivo) |
| Diagnóstico | En curso, en paralelo (Fase 1 del plan de trabajo) | `docs/anexo_legislacion_mx.md`, `docs/anexo_legislacion_uy.md`, `entregables/fase-1/matriz-normativa.md` |
| Definición | Cubierta por este documento (teoría de cambio) y por la matriz normativa | Este archivo + matriz normativa |
| Diseño | Programada, Fase 2 (28-jul → 11-ago-2026) | `entregables/fase-2/modelo-diagnostico.md` (pendiente), arquitectura (`docs/stack-tecnologico.md`) |
| Prototipo | Programada, Fase 2 — demo desplegable antes de la postulación, no solo documentos (mitiga la causal de descarte "prototipos sin validación") | Scaffolding FastAPI+Postgres (`backend/`), demo de staging |
| Piloto | Fuera del alcance de esta postulación en sentido estricto — es lo que se solicita financiar; ocurre **si** la propuesta es seleccionada | Objeto de la postulación misma |
| Implementación | Explícitamente fuera de alcance del proyecto — corresponde al gobierno local una vez transferidas las capacidades (Sección 6); DiagMuni no opera la implementación de largo plazo | — |

**Lectura de admisibilidad:** el proyecto cabe en el ciclo porque hoy se encuentra correctamente ubicado en las etapas de admisibilidad/diagnóstico/definición, sin adelantarse a etapas posteriores (no se está prometiendo una implementación que el proyecto no puede controlar) ni quedarse corto (ya hay un prototipo programado, no solo intención). No se detecta deriva de alcance frente a la Guía original en cuanto a la definición del reto — el problema público y la población objetivo (gobiernos locales pequeños y medianos) son los mismos que en el planteamiento inicial.

### 3.2 Encaje en el Eje 1 (Atención Ciudadana) de GovTech Connect

DiagMuni se postula bajo el Eje 1, Atención Ciudadana. El encaje es directo: las variables de diagnóstico (documentos en papel vs. digital, motor de pagos, firma electrónica, interoperabilidad, identidad/acceso ciudadano) son, todas, dimensiones de la experiencia del ciudadano frente al trámite, no de back-office puro. El catálogo de componentes OSS recomendados (`docs/stack-tecnologico.md`) está organizado explícitamente por subtema del Eje 1 (gestión de reclamos, automatización/trazabilidad, captura, tableros, interoperabilidad).

**Nota de encaje:** la decisión de arquitectura sobre si el default de producción de la capa de IA es un modelo local o una API externa (`docs/stack-tecnologico.md`) no altera el encaje en el Eje 1 ni la admisibilidad del proyecto — es una decisión técnica interna, no de alcance del reto.

### 3.3 Verificación contra las causales de descarte (lectura desde política pública)

Las 7 causales de descarte oficiales de la convocatoria (texto literal registrado en `docs/stack-tecnologico.md`, principio 6) se cruzan con el diseño del proyecto de la siguiente manera, desde la óptica de esta validación (el detalle técnico de cada causal es responsabilidad de los agentes técnicos, no de este documento):

- **(a) Componentes privativos:** mitigada por el principio de licenciamiento 100% OSS (`docs/stack-tecnologico.md`, principio 2); no es materia de este documento, pero se vigila que ninguna pieza del instrumento de diagnóstico induzca al gobierno local hacia un componente propietario específico (ver Sección 4.3).
- **(b) Prototipos sin validación ni antecedentes:** mitigada por el prototipo desplegable de Fase 2 y por el antecedente real de operación de un sistema de gestión de trámites/reclamos que se documentará en la validación final de Fase 3 (Sección 7) — verificación de que ese antecedente se declara sin convertirlo en promoción de un producto comercial corresponde a esa misma validación.
- **(c) Dependencia total del implementador original:** es la causal directamente bajo mandato de este agente — ver Sección 4.2.
- **(d) Documentación técnica insuficiente o licencia ambigua:** no es materia de este documento (ver `docs/stack-tecnologico.md`, nota sobre Formio).
- **(e) Proyectos que no responden a un desafío concreto de los ejes priorizados:** cubierta por la Sección 3.2 de este documento.
- **(f) Adjudicación directa o acuerdo exclusivo con una ciudad:** cubierta por el diseño de la carta de interés (`entregables/one-pager-intendencias.md`), que declara explícitamente ausencia de exclusividad; no es materia técnica de este documento pero se confirma su coherencia con la teoría de cambio (el diagnóstico debe ser replicable en más de una ciudad para que el argumento de política pública — reducir opacidad y brecha de capacidades como problema estructural, no como favor a una sola ciudad — se sostenga).
- **(g) Plazo de ejecución:** no es materia de este documento.

### 3.4 Riesgo de admisibilidad abierto — NO resuelto por este documento

**Existe un riesgo de fondo, señalado por RIL, que este documento declara sin resolver:** la convocatoria GovTech Connect podría estar diseñada para **adoptar soluciones OSS ya existentes con comunidad activa**, no para **financiar el desarrollo de una solución nueva** como DiagMuni. Si ese fuera el criterio real de evaluación, DiagMuni — un desarrollo de cero, sin comunidad de usuarios previa, aunque construido enteramente sobre componentes OSS existentes y con licencia Apache 2.0 desde el día uno — enfrentaría un riesgo de admisibilidad que ninguna de las salvaguardas de este documento resuelve, porque no es un problema de diseño del proyecto sino de interpretación de las bases de la convocatoria.

Esta interpretación no se cierra en este documento — se deja registrada para aclarar con RIL antes de la postulación:

- Si la convocatoria exige que la solución postulada ya tenga una comunidad de uso/desarrollo activa fuera del equipo postulante, DiagMuni no cumpliría ese criterio en su estado actual, independientemente de la calidad técnica o normativa del proyecto.
- Si, en cambio, la convocatoria permite financiar el desarrollo de una solución nueva siempre que sea OSS desde su origen (lectura que sostiene el resto de este documento y el resto del proyecto), DiagMuni cumple.
- Mientras no se aclare, este riesgo debe mencionarse explícitamente en la comunicación con RIL, no ocultarse ni asumirse resuelto a favor del proyecto.

---

## 4. Salvaguardas de rectoría pública

### 4.1 Propiedad del diagnóstico y de los datos

El diagnóstico y los datos que un gobierno local produce al responder el instrumento **pertenecen a ese gobierno**, no al Laboratorio ni a ningún implementador. Esto ya está reflejado en el diseño técnico (`docs/PRD.md`, F7: multi-tenant con Row-Level Security por `tenant_id`) y en el compromiso público del proyecto (`README.md`, sección "Transferencia de capacidades"). Esta sección lo fija como principio de política pública, no solo como decisión de arquitectura: ningún rediseño técnico futuro puede debilitar el aislamiento de datos por tenant ni introducir un mecanismo que permita al Laboratorio o a un tercero acceder, agregar o comercializar los diagnósticos de un gobierno local sin su consentimiento explícito.

### 4.2 No dependencia del implementador original (causal de descarte c)

DiagMuni está diseñado para que un gobierno local pueda operarlo sin el Laboratorio ni ningún desarrollador original, una vez transferido:

- Licencia Apache 2.0 en el repositorio propio, código auditable, sin componentes privativos (`docs/stack-tecnologico.md`, principio 2).
- Entrega oficial de producción autoalojable con Docker Compose (nginx + backend + db), sin cuenta de terceros obligatoria para operar (`docs/stack-tecnologico.md`).
- Motor de reglas normativas versionado y config-driven, y catálogo brecha→acción mantenible por alguien sin conocimiento de programación, acotado por diseño (`docs/PRD.md`, "Requisitos no funcionales").
- Documentación técnica completa desde el primer commit (`README.md`).

Esta salvaguarda es la que convierte la "dependencia total del implementador" en causal de descarte real y vigilada, no en frase retórica: cualquier decisión técnica futura (por ejemplo, entre capa de IA local o vía API, `docs/stack-tecnologico.md`) debe evaluarse también contra este criterio, porque ambas opciones ya están diseñadas con degradación a plantillas deterministas como mecanismo de independencia — lo que cambia entre ellas es solo cuál es la primera línea de defensa y cuál la de respaldo, no si existe independencia del proveedor.

### 4.3 Separación entre cocreación y contratación comercial

El Laboratorio de Innovación Pública del INAP cocrea el diagnóstico y el plan de modernización en un espacio neutral, sin interés comercial en la implementación posterior. Esta separación es un firewall estructural del proyecto y se traduce en una regla de producto explícita:

**El plan generado por DiagMuni recomienda categorías de tecnología y estándares abiertos — nunca marcas ni proveedores comerciales específicos.** Esto ya está reflejado en el diseño del catálogo de componentes recomendados (`docs/stack-tecnologico.md`, sección "Catálogo OSS — solo recomendación, no se opera"): el plan puede decir "sistema de gestión de reclamos y solicitudes bajo licencia abierta, con comunidad activa" y citar un componente OSS como referencia de categoría verificada, pero la contratación efectiva de cualquier implementación posterior —sea de ese componente OSS, de una adaptación a medida, o de cualquier servicio asociado— es una decisión soberana del gobierno local, sujeta a sus propios procesos de contratación pública, y ocurre **fuera** del proceso de cocreación del Laboratorio y sin participación de este ni de ningún actor con interés comercial en el resultado. Ningún entregable de este proyecto debe nombrar, promover o direccionar hacia una empresa privada específica como proveedor de implementación; esta regla aplica también a este mismo documento, que deliberadamente no menciona ninguna razón social.

Esta salvaguarda es la que impide que el diagnóstico "estandarizado" se convierta en un embudo de ventas: la neutralidad técnica del Laboratorio depende de que quien responde el diagnóstico no pueda inferir, del propio instrumento o del plan, una preferencia hacia un proveedor determinado.

---

## 5. Economía política local — hablar el lenguaje institucional correcto

El instrumento de diagnóstico y el plan que genera deben dirigirse al interlocutor real con autoridad y recursos en cada país, no a una entidad genérica de "municipio" que no existe de la misma forma en ambos marcos jurídicos.

### 5.1 México — el ayuntamiento y su Autoridad Municipal de Simplificación y Digitalización

El interlocutor institucional en México es el **ayuntamiento**, a través de la **Autoridad Local de Simplificación y Digitalización** que la LNETB exige constituir también a nivel municipal (art. 11), con sus cinco áreas sustantivas (Simplificación; Digitalización; Atención Ciudadana; Buenas prácticas regulatorias; Desarrollo de Soluciones Tecnológicas), y el **Enlace de Simplificación y Digitalización** designado (arts. 14–15) como responsable operativo del inventario de trámites (art. 15, fracc. IV) y de la métrica de uso (art. 15, fracc. X) (`docs/anexo_legislacion_mx.md`, sección 1). El cuestionario debe preguntar explícitamente por la existencia de esta Autoridad y de este Enlace como variable de capacidad institucional (ya incorporada en `entregables/fase-1/matriz-normativa.md`), y el plan de modernización debe dirigir sus recomendaciones de gobernanza hacia esa Autoridad, no hacia una "oficina de sistemas" genérica que puede no existir con ese nombre ni ese mandato legal.

### 5.2 Uruguay — la intendencia, no el municipio

En Uruguay el interlocutor institucional real es la **intendencia** (gobierno departamental), no el municipio. La Ley N.º 19.272 (`docs/anexo_legislacion_uy.md`, sección 7) es explícita en esto: la **materia departamental** (art. 6) incluye la política de recursos financieros y humanos y los programas presupuestales municipales — es decir, **la intendencia controla los recursos** con los que un municipio podría digitalizarse — mientras que la **materia municipal** (art. 7) se limita a asuntos de cercanía (vialidad local, alumbrado, espacios públicos, necrópolis, residuos) y a la facultad de celebrar convenios y participar en proyectos de cooperación internacional (art. 7, nums. 7 y 10, que es además la base jurídica directa para que un municipio de la coalición CIIAR participe del piloto). La gran mayoría de los "trámites municipales" en sentido coloquial (tributos, permisos de construcción, habilitaciones comerciales, licencias de conducir) son en realidad **departamentales**.

Consecuencia de diseño ya incorporada en la matriz normativa: el instrumento no debe asumir que un municipio uruguayo tiene, por sí mismo, la capacidad presupuestal o competencial para ejecutar el plan que el diagnóstico genera — la carta de interés y la contraparte técnica de la convocatoria deben gestionarse con la intendencia (como ya lo hace `entregables/one-pager-intendencias.md`, dirigido a intendencias, no a municipios), y el propio cuestionario debe incluir el "mapa competencial del trámite" (¿lo presta el municipio, la intendencia, o es delegado?) como variable estructural previa a cualquier otra, tal como ya está registrado en `entregables/fase-1/matriz-normativa.md`.

### 5.3 Implicación para el diseño del instrumento

Ambas asimetrías institucionales están ya anticipadas en la matriz normativa reconciliada (`entregables/fase-1/matriz-normativa.md`, tabla "Variables nuevas"): México captura "Autoridad Municipal de Simplificación y Digitalización y Enlace designado" como variable con anclaje legal directo; Uruguay captura, en su lugar, "existencia de convenio vigente con Agesic" como variable sustituta, porque no existe un equivalente uruguayo obligatorio a nivel departamental. Esta asimetría es deliberada y correcta — no debe "corregirse" buscando artificialmente un equivalente 1:1 entre ambos países donde la propia arquitectura institucional no lo tiene.

---

## 6. Transferencia de capacidades — compromiso y criterio (detalle en Fase 3)

La convocatoria exige explícitamente la transferencia de capacidades al gobierno local (`README.md`, `docs/PRD.md`, causal de descarte (c)). Este documento fija el compromiso conceptual y el criterio de aceptación; el diseño detallado del instrumento de formación, sus materiales y su plan de medición corresponden a la Fase 3.

**Compromiso:** el piloto no se da por cerrado únicamente con la entrega del diagnóstico y del plan de modernización; incluye una sesión de capacitación dirigida a la **contraparte técnica designada por la carta de interés** (exigida por las bases de la convocatoria), cuyo objetivo es que esa contraparte pueda, sin soporte del Laboratorio ni de ningún implementador original:

1. Operar la plataforma (cargar un nuevo trámite, ejecutar un nuevo diagnóstico, leer el panel de seguimiento).
2. Interpretar el índice de madurez y el plan generado sin depender de una explicación externa cada vez.
3. Mantener el catálogo brecha→acción editable del país correspondiente, dado que está diseñado como texto estructurado, no hardcodeado (`docs/PRD.md`, "Requisitos no funcionales").

**Criterio de evidencia documental (a detallar en Fase 3, no a inventar aquí):** el piloto no se considera completo sin registro verificable de que esa transferencia ocurrió — como mínimo, evidencia de asistencia de la contraparte técnica a la sesión de capacitación y algún mecanismo de autoevaluación de autonomía operativa antes/después. La forma exacta de ese instrumento (encuesta, checklist, acta de entrega-recepción del código y los datos) se detalla en Fase 3; este documento solo fija que **debe existir** y que su ausencia es motivo suficiente para no dar por cumplida la salvaguarda de transferencia de capacidades en la validación final.

---

## 7. Qué queda pendiente para la validación final de Fase 3

Este documento cierra la validación de admisibilidad de Fase 1. La validación final de Fase 3 deberá verificar, ya con el instrumento y el plan de M&E de Fase 3 sobre la mesa:

1. Que el instrumento de diagnóstico final no induce, ni siquiera implícitamente, a un proveedor comercial específico (Sección 4.3).
2. Que el componente de transferencia de capacidades diseñado en Fase 3 cumple el criterio de evidencia documental fijado en la Sección 6.
3. Que el riesgo de admisibilidad abierto en la Sección 3.4 fue efectivamente planteado a RIL antes del cierre de la postulación, con independencia de cuál haya sido la respuesta.
4. Que no se introdujo, entre esta fecha y el cierre de la postulación, ninguna deriva de alcance frente a lo fijado en la Sección 3 de este documento.
