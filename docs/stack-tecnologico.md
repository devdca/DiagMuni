# Stack tecnológico — DiagMuni

Versión 2 · julio de 2026
Decisiones fijadas para el desarrollo de DiagMuni, plataforma OSS de diagnóstico y modelado de modernización municipal (Laboratorio de Innovación Pública del INAP), en el marco de la postulación a GovTech Connect (BID Lab / RIL).

## Principios rectores (no negociables)

1. Motor determinista primero, IA después: el índice de madurez y las reglas normativas son código puro, testeable y reproducible. Los LLM solo redactan el plan, clasifican texto libre y asisten la captura.
2. Código y componentes 100% open source, licencia Apache 2.0 en el repo propio. Dependencias solo MIT/BSD/Apache; GPL únicamente como servicio separado sin linking de código (mere aggregation); **AGPL nunca como dependencia integrada** — solo admisible como recomendación de catálogo que el gobierno local despliega y opera por su cuenta, sin modificarlo ni empaquetarlo dentro del repo o del servicio de DiagMuni (el Art. 13 de AGPL dispara obligación de publicar código ante cualquier modificación ofrecida por red, a diferencia de GPL); ninguna licencia "fair-code"/source-available con restricciones comerciales.
3. Replicabilidad: debe correr en un VPS económico o un servidor único modesto de una intendencia pequeña. Criterio rector de todo el stack, no preferencia tecnológica.
4. Multi-tenant desde el día uno.
5. Presupuesto del piloto ≤ USD 10,000 total.
6. Causales de descarte de la convocatoria a vigilar (7 oficiales): (a) soluciones con código parcialmente cerrado o componentes privativos; (b) prototipos sin validación mínima ni antecedentes de implementación; (c) herramientas que generen dependencia total del implementador original; (d) propuestas sin documentación técnica o con licencia ambigua; (e) proyectos que no respondan a un desafío concreto de los ejes priorizados; (f) propuestas que dependan de una adjudicación directa o acuerdo exclusivo con una ciudad; (g) soluciones que no puedan ejecutarse dentro del plazo definido.

## Stack definitivo

| Capa | Decisión | Notas |
|---|---|---|
| Backend | Python 3.12 + FastAPI | API REST/JSON pura |
| Base de datos | PostgreSQL 16 | Shared-schema + columna `tenant_id`, reforzado con **Row-Level Security** (la columna sola no aísla ante un query sin filtro) |
| ORM / migraciones | SQLAlchemy 2.0 + Alembic | — |
| Frontend | React + Vite + TypeScript | SPA, decisión explícita por ecosistema/hireability sobre alternativa server-rendered |
| Data fetching | TanStack Query (React Query) | — |
| Formularios | react-hook-form + zod | Valida en espejo con schemas Pydantic del backend; soporta el cuestionario con lógica de ramificación |
| Componentes UI | shadcn/ui (Radix + Tailwind) | MIT, código copiado al repo, no dependencia de paquete |
| Entrega oficial de producción | Docker Compose, 3 servicios: **nginx** (sirve build de React + proxy `/api`) + **backend** + **db** | 100% autoalojable por la intendencia con solo el repo, sin depender de cuentas de terceros |
| Desarrollo / previews | Cloudflare Pages | Solo para previews automáticos de cada PR durante el desarrollo — nunca como destino de producción del piloto (evita dependencia del implementador y preserva la replicabilidad autoalojada) |
| Async / jobs | FastAPI `BackgroundTasks` + tabla `job` persistida (pending/running/done/failed) | Recupera la generación del plan (llamada LLM de 30-60s) si el proceso reinicia; deja barato el salto a Celery si el volumen lo exige |
| Autenticación | JWT propio con librería vetada (PyJWT/authlib) | `tenant_id` en el claim, validado server-side |
| Motor de reglas / índice de madurez | Versionado y config-driven, nunca hardcodeado | Persiste qué versión de reglas produjo cada diagnóstico — protege reproducibilidad ante cambios legales (ej. México 2025: LGMR abrogada, CONAMER extinta) |
| Capa IA | LiteLLM sirviendo **DeepSeek vía API** (F1 captura, F9 verificador — tareas generales de bajo costo) y **Claude vía API** (F3 generación compleja del plan); degradación a plantillas deterministas si la API no responde | Un modelo local cuantizado (candidato evaluado: phi3/Phi-3-mini, licencia MIT) queda documentado como alternativa técnicamente viable, disponible vía cambio de configuración de LiteLLM sin tocar `engine/` ni el resto del backend, si en el futuro cambia el criterio (presupuesto de API, política de datos, o necesidad de operar sin conexión a internet) — ver "Nota sobre la Capa IA" más abajo |
| CI | GitHub Actions + chequeo automático de licencias de dependencias (pip-licenses / licensecheck) | Ataca directo la causal de descarte "licencia ambigua" |
| Observabilidad | Logs a stdout + endpoint `/health` + log de auditoría del diagnóstico | Sin stack pesado (sin Grafana/Prometheus) para el MVP |

## Catálogo OSS — solo recomendación, no se opera

Estos componentes se documentan como recomendaciones dentro del plan de modernización que el software genera para la ciudad. No se despliegan ni se operan como parte de la infraestructura de DiagMuni ni del piloto.

| Subtema Eje 1 (Atención Ciudadana) | Componente recomendado | Licencia |
|---|---|---|
| Gestión de reclamos y solicitudes | osTicket | GPL-2.0-or-later |
| Automatización de respuestas / trazabilidad de trámites | Node-RED | Apache 2.0 |
| Captura | LimeSurvey | GPL-2.0-or-later |
| Tableros | Metabase / Superset | AGPL-3.0 / Apache 2.0 |
| Interoperabilidad (Uruguay) | Cliente PDI de AGESIC | **Sin licencia declarada** — confirmar con AGESIC antes de integrar (ver nota) |

**Nota sobre Metabase (AGPL-3.0):** admisible como recomendación de catálogo por el Principio 2 de este mismo documento — que admite AGPL "solo como recomendación de catálogo que el gobierno local despliega y opera por su cuenta", nunca como dependencia integrada. La ciudad despliega y opera Metabase de forma independiente, sin que DiagMuni lo modifique ni lo empaquete. Guardarraíl duro: Metabase **nunca** debe pasar de "recomendado en el plan" a "integrado/embebido" dentro del repo o el servicio de DiagMuni — eso chocaría directo con el Principio 2. Si en el futuro se quiere un tablero embebido dentro de la propia plataforma, usar Superset (Apache 2.0), no Metabase.

**Nota sobre el Cliente PDI de AGESIC (licencia sin declarar):** verificado directamente contra el repositorio oficial (`github.com/AGESIC-UY/cliente-java-plataforma-interoperabilidad`, rama `master`) — no contra la inferencia por patrón de organización. Lo que **sí se observó**: el repositorio **no contiene ningún archivo `LICENSE`** (raíz del repo: `.gitignore`, `README.md`, `doc/`, `pom.xml`, `src/`); el campo `license` de la API de GitHub para este repositorio devuelve `null` y el endpoint `GET /repos/AGESIC-UY/cliente-java-plataforma-interoperabilidad/license` responde `404 Not Found`; ni `README.md` ni `pom.xml` declaran una licencia en ningún punto de su texto. Otros repositorios de la organización `AGESIC-UY` (ej. `pdi-core`, `pdi-ruteo`) sí son mayoritariamente AGPL-3.0, pero ese patrón no se replica automáticamente en este repositorio en particular — es una inferencia por organización, no una verificación del repo específico. Se deja `[NO VERIFICADO]` en la tabla. Advertencia adicional: la ausencia total de archivo `LICENSE` no equivale a "libre de usar" — bajo el régimen por defecto de derecho de autor, sin una licencia FOSS explícita el titular (AGESIC) no ha otorgado permiso expreso de uso, copia, modificación o redistribución más allá de la disponibilidad pública del código para consulta. Se recomienda a la intendencia que quiera integrar este cliente en su propio sistema de trámites **confirmar la licencia directamente con AGESIC** antes de integrarlo — DiagMuni, en cualquier caso, solo lo recomienda en el plan, nunca lo empaqueta ni lo modifica.

**Nota sobre Formio (descartado del catálogo):** el ecosistema Form.io es open-core y no admite una sola etiqueta de licencia. `formio.js` (renderer JSON, cliente) es MIT; el servidor `formio` autoalojable cambió de BSD a **OSL-3.0** (OSI-approved pero no está en la lista explícita MIT/Apache/GPL/EUPL de la convocatoria); y PDF Server, Enterprise Server y Premium Library son **propietarios**, con `LICENSE_KEY` de pago. Citar "Formio" sin especificar la pieza es exactamente el tipo de "licencia ambigua" que la convocatoria descalifica — se retira del catálogo y se deja solo LimeSurvey (GPL-2.0-or-later), sin ambigüedad posible.

**Pendiente de catálogo:** `entregables/fase-2/modelo-diagnostico.md` declara que la digitalización del expediente requiere "adoptar un gestor de expediente electrónico (categoría, no marca — candidato específico pendiente en catálogo OSS)". Este catálogo todavía no tiene una fila para la categoría `gestor_expediente_electronico` — queda como pendiente de una futura iteración.

## Componentes descartados

| Componente | Motivo |
|---|---|
| n8n | Licencia Sustainable Use License (no OSI, prohíbe hospedar y cobrar a terceros) — riesgo directo de descalificación por "licencia ambigua" |
| Camunda | Camunda 7 CE (única versión Apache 2.0) entró en EOL el 14-oct-2025; Camunda 8 exige licencia de producción paga para self-managed |
| Inferencia local de LLM **en el servidor de oficina del Laboratorio** (FusionCube 1000H-X3) | Sin GPU, memoria por socket castrada para inferencia — pista muerta específica de ese hardware; sigue sin ser el objetivo de replicabilidad del producto (ver Principio 3), independientemente de qué se resuelva sobre inferencia local en general (medida contra un VPS económico genérico, no contra este servidor) |
| Modelo local único (phi3/Phi-3-mini, MIT) como default de producción de Capa IA | Evaluado a fondo (dos rondas de benchmark) y sin ningún problema de licencia, pero **no adoptado como default**: una prueba comparativa real mostró la API ~20-30x más rápida (~5.8s vs. 101-194s por párrafo) y de costo marginal insignificante para el volumen de un piloto (~USD 0.00016 por llamada de F3) — ver `entregables/fase-2/dimensionamiento-costos.md`. Sigue disponible vía cambio de configuración de LiteLLM (sin tocar `engine/`) si en el futuro cambia el criterio (presupuesto de API, política de datos, o necesidad de operar sin conexión a internet) |
| **Qwen2.5-3B-Instruct** como modelo local candidato de producción | Rindió igual de bien que Llama 3.2 3B en benchmark (215 tokens en 69.6s, ~3.1 tok/s, redacción correcta y sin alucinaciones) pero se descarta por **licencia**: Qwen2.5-3B-Instruct está bajo la *Qwen Research License* ("Tongyi Qianwen"), explícitamente restringida a "non-commercial purposes only" — uso comercial/productivo exige una licencia aparte de Alibaba que DiagMuni no tiene. Choca directo con el Principio 2 y con la causal de descarte (a) "componentes privativos". La licencia manda sobre el rendimiento. Nota: otras variantes de Qwen2.5 (0.5B/1.5B/7B/14B/32B-Instruct) sí son Apache 2.0, no fueron benchmarkeadas |
| **Llama 3.2 3B Instruct** como modelo local candidato de producción | Rindió prácticamente igual que Qwen2.5:3b (218 tokens en 67.2s, ~3.2 tok/s) pero se descarta por **licencia**: la *Llama 3.2 Community License* permite uso comercial/productivo pero **no es OSI-approved** (exige atribución "Built with Llama", Acceptable Use Policy propia, y prohíbe usar el modelo o sus salidas para entrenar modelos competidores). No cumple los cuatro estándares del Principio 2 (Apache/MIT/BSD/GPL). Se prefiere phi3 (MIT), que sí los cumple sin excepción |
| **mistral (7B, Apache 2.0)** como modelo local candidato de producción | Licencia limpia y calidad de redacción sólida y bien estructurada (368 tokens), pero **casi el doble de lento que phi3** (194.0s de generación vs. 122.8s) — peor ajuste para la franja de latencia (30-70s) para la que ya está diseñada la arquitectura async. Se prefiere phi3 por velocidad, con licencia igualmente limpia |
| **olmo2 (7B, Apache 2.0)** como modelo local candidato de producción | Licencia limpia y velocidad intermedia (261 tokens en 101.1s), pero la única muestra observada contiene un **error factual de citación institucional**: la respuesta confunde el SAT (Servicio de Administración Tributaria, el organismo real que emite la e.firma) con la "Secretaría de Telecomunicaciones y Transportes" — una entidad que no corresponde. En un producto cuyo diferenciador es la trazabilidad normativa (F8, `docs/PRD.md`), mezclar el nombre de la autoridad emisora es un riesgo de calidad más serio que la velocidad, aunque sea una sola muestra. Se descarta en favor de phi3 hasta repetir el benchmark con más muestras si se quisiera reconsiderar |

## Infraestructura interna del Laboratorio (servidor de oficina)

El servidor nuevo (BoQ: Huawei FusionCube 1000H-X3, 2 nodos hiperconvergentes, 4× Xeon Gold 5318Y de 24 núcleos, 256GB RAM total, storage por niveles NVMe/SSD/HDD, sin GPU) es infraestructura interna del Laboratorio, no el objetivo de replicabilidad del producto. Usos válidos:

- Instancia canónica multi-tenant con alta disponibilidad real (2 nodos)
- Runner self-hosted de CI
- Ambiente de staging/demo para la postulación

Condición: la demo interna nunca debe depender del software de virtualización/storage propietario de Huawei (FusionStorage) — el entregable que se documenta y transfiere sigue siendo el Docker Compose portable.

## Nota sobre la Capa IA — modelo local evaluado, no elegido como default

**Decisión:** DeepSeek + Claude vía API como default de producción, con degradación a plantillas deterministas si la API no responde. Un modelo local cuantizado (phi3/Phi-3-mini, MIT) fue evaluado a fondo y queda disponible como alternativa vía cambio de configuración de LiteLLM, sin tocar `engine/` ni el resto del backend, si el criterio cambia en el futuro (presupuesto de API, política de datos, u operación sin conexión a internet).

**Por qué:** un benchmark real (mismo párrafo de prueba F3, "Firma electrónica", generado por ambos caminos) midió la API de DeepSeek en 5.8 segundos (~79 tok/s, ~USD 0.00016 por llamada), contra 101-194 segundos de los mejores candidatos locales con licencia limpia — una diferencia de un orden de magnitud en latencia, con costo marginal insignificante para el volumen de un piloto. El diseño de LiteLLM como capa de abstracción hace que este default sea reversible por configuración, no una decisión estructural: cambiarlo más adelante no exige reescribir `ia/` ni `engine/`.

**Benchmark de candidatos locales** (iMac Intel Core i5-4570, 4 núcleos, sin GPU, 32GB RAM — un proxy pesimista de un VPS moderno de gama económica, no un mejor caso: CPUs de 2025-2026 tienen mejor IPC/AVX que este hardware de 2013-2014):

| Modelo | Licencia | Tokens generados | Tiempo de generación | Velocidad | Calidad |
|---|---|---|---|---|---|
| qwen2.5:3b (Q4, ~1.9GB) | Qwen Research License (no comercial) | 215 | 69.6s | ~3.1 tok/s | Correcta, cita LNETB art. 25-III, e.firma SAT, PAdES/XAdES |
| llama3.2:3b (Q4, ~2.0GB) | Llama 3.2 Community License (no OSI-approved) | 218 | 67.2s | ~3.2 tok/s | Correcta, comparable a qwen2.5:3b |
| phi3 / Phi-3-mini (~3.8B, ~2.2GB) | **MIT** | 308 | 122.8s | ~2.5 tok/s | Correcta, un desliz gramatical menor — no factual |
| mistral (7B, ~4.4GB) | **Apache 2.0** | 368 | 194.0s | ~1.9 tok/s | Correcta y bien estructurada, pero notablemente más lenta |
| olmo2 (7B, ~4.5GB) | **Apache 2.0** | 261 | 101.1s | ~2.6 tok/s | Error factual de citación institucional (ver tabla de componentes descartados) |

**Por qué ~123s (candidato local más rápido con licencia limpia) es aceptable en términos de arquitectura:** el job de generación del plan (F3) ya está diseñado como asíncrono (tabla `job` persistida, reintento — ver "Job asíncrono" en `docs/TRD.md`), en la misma franja de decenas de segundos para la que la arquitectura fue pensada, aunque en el extremo superior del rango típico (30-60s) de la API externa.

### Por qué phi3 y no Qwen2.5-3B-Instruct, Llama 3.2 3B, mistral o olmo2 (dentro de los candidatos locales)

Se probaron cinco modelos locales en total. Los resultados técnicos fueron todos comparables en calidad general, así que **la decisión final la determinan la licencia primero, y luego velocidad/calidad entre los que pasan el filtro de licencia**:

- **Qwen2.5-3B-Instruct**: licenciado bajo la *Qwen Research License Agreement* ("Tongyi Qianwen"). El texto define "Non-Commercial" como "for research or evaluation purposes only" y otorga la licencia únicamente "FOR NON-COMMERCIAL PURPOSES ONLY"; el uso comercial exige solicitar una licencia aparte a Alibaba. Esto **descalifica a Qwen2.5-3B-Instruct** para DiagMuni pese a su rendimiento: un piloto desplegado para intendencias no es "investigación o evaluación". Nótese que otras variantes de Qwen2.5 (0.5B, 1.5B, 7B, 14B, 32B-Instruct) sí están bajo Apache 2.0 — no fueron benchmarkeadas.
- **Llama 3.2 3B Instruct**: licenciado bajo la *Llama 3.2 Community License Agreement*. Permite uso comercial/productivo, pero **no es Apache/MIT/BSD/GPL ni está aprobada por OSI**: exige atribución obligatoria "Built with Llama", tiene una Acceptable Use Policy separada, y prohíbe usar el modelo o sus salidas para entrenar o mejorar modelos competidores. Es "open-weight" con condiciones de uso, no FOSS en sentido estricto.
- **mistral (7B)** y **olmo2 (7B)**: ambos Apache 2.0, licencia limpia sin reservas. Se descartan por razones técnicas, no de licencia: mistral es casi el doble de lento que phi3 (194.0s vs 122.8s de generación); olmo2, aunque más rápido que mistral, produjo en su única muestra observada un **error factual de citación institucional** (confundió el SAT con la "Secretaría de Telecomunicaciones y Transportes") — un riesgo de calidad serio para un producto cuyo diferenciador es la trazabilidad normativa citada (F8).
- **phi3 / Phi-3-mini**: licencia **MIT**, sin ninguna condición adicional a las cuatro licencias FOSS del Principio 2. Es el más rápido de los tres candidatos con licencia limpia (~2.5 tok/s) y no mostró errores factuales en la muestra observada.

phi3 es MIT sin reservas, el repositorio de código permanece 100% Apache 2.0, y `engine/` (el motor determinista) no depende del modelo en absoluto. Nota de honestidad: todas las comparaciones de calidad entre modelos se basan en una sola muestra por modelo (el mismo párrafo de prueba) — antes de considerar phi3 para cualquier despliegue futuro, conviene correr varias muestras con distintas entradas del catálogo brecha→acción para confirmar que la ausencia de errores factuales no es casualidad de una sola corrida.

El dimensionamiento y costeo completo de un VPS para correr el modelo local (piso de hardware, cotizaciones de proveedor, latencia esperada, impacto en el presupuesto del piloto) vive como referencia en `entregables/fase-2/dimensionamiento-costos.md`, disponible si el criterio de la Capa IA cambia en el futuro.

## Riesgos abiertos por falta de alcance fino

Decisiones robustas independientemente del alcance exacto del piloto: todo el stack anterior salvo dos piezas que se dejan deliberadamente flexibles porque son las que más van a moverse:

1. **Motor de reglas normativas** — versionado/config-driven, listo para absorber cambios legales sin reescritura.
2. **Capa async** — la tabla `job` deja el salto a Celery barato si el volumen de tenants lo exige más adelante.
