# PRD — Documento de Requerimientos de Producto — DiagMuni

Versión 1 · 21 de julio de 2026
Primero de los 6 documentos de blueprint de producto (`docs/`), previos a escribir código. Consolida decisiones ya tomadas en `README.md` y `docs/stack-tecnologico.md` — no las repite en detalle, las referencia.

## Visión

DiagMuni es una plataforma open source (Apache 2.0) que permite a un gobierno local — municipio en México, intendencia en Uruguay — autodiagnosticar su nivel de madurez digital trámite por trámite y recibir, en automático, un plan de modernización a la medida: tecnología a adoptar, inversión estimada, personal y capacitación requeridos.

Es un proyecto del Laboratorio de Innovación Pública del INAP, postulado a **GovTech Connect** (BID Lab / Red de Innovación Local), con piloto objetivo en una intendencia de la coalición CIIAR (Uruguay). Este PRD cubre el **producto**, no la estrategia de postulación.

## Problema

Los gobiernos locales pequeños y medianos no tienen forma barata de saber, de manera objetiva y comparable, qué tan digitalizados están sus trámites ni qué les falta para modernizarse. El diagnóstico hoy es artesanal (consultoría cara, criterio subjetivo) o inexistente. Resultado: opacidad y fricción para el ciudadano, y falta de un plan priorizado y costeado para el funcionario que sí quiere modernizar.

## Usuario objetivo

**El funcionario público que responde el diagnóstico** — no el ciudadano final, no el tecnólogo. Debe funcionar igual de bien para:
- Un municipio pequeño (~5,000 habitantes, 3 funcionarios de mostrador).
- Una intendencia grande con área TIC propia.

Interlocutor institucional según país: en Uruguay, la intendencia (Ley 19.272); en México, el ayuntamiento a través de su Autoridad Municipal de Simplificación y Digitalización (LNETB art. 11).

## Principio rector del producto

**Motor determinista primero, IA después.** El índice de madurez y las reglas normativas son código puro, testeable y reproducible — el mismo dato siempre da el mismo resultado. Los LLM (DeepSeek/Claude vía LiteLLM) solo redactan el plan en lenguaje natural, clasifican texto libre del funcionario y asisten la captura. Nunca calculan el índice. Detalle técnico completo en `docs/stack-tecnologico.md`.

## Alcance del MVP (piloto)

### Dentro de alcance
1. Cuestionario de diagnóstico por trámite (documentos papel/digital, pagos en línea, firma-e, interoperabilidad, datos personales, mecanismo de identidad/acceso ciudadano — Llave MX / ID Uruguay / propio / ninguno) + variables de contexto (población, personal, presupuesto TIC) + variables de capacidad institucional (área TIC, conectividad, normativa local).
2. Cálculo del índice de madurez 0-4 por trámite y agregado global, con criterios binarios verificables (no juicio subjetivo).
3. Generador de plan de modernización: brechas → acciones (tecnología del catálogo OSS, inversión estimada, personal/capacitación, secuencia).
4. Panel simple de seguimiento del plan (semáforo por acción, responsable, fecha).
5. Multi-tenant desde el día uno: un despliegue sirve a varios municipios/intendencias, aislados por Row-Level Security.
6. Reglas normativas parametrizadas por país (México/Uruguay) desde el mismo modelo de datos — nunca hardcodeadas ni bifurcadas en código separado.
7. Autoalojable por la intendencia vía Docker Compose (nginx + backend + db), sin cuenta de terceros obligatoria para operar en producción.
8. Verificador del plan (F9): antes de mostrar el plan generado por LLM al funcionario, se audita contra las reglas del motor determinista — nunca se muestra una acción que contradiga el índice calculado o que no exista en el catálogo OSS.

### Fuera de alcance (explícitamente, para que el agente que implemente no lo asuma)
- Portal ciudadano o app para el ciudadano final — el usuario es el funcionario, no el vecino; el valor ciudadano se entrega indirectamente a través del plan que el gobierno implementa, no de un producto de cara al ciudadano.
- Pasarela de pagos propia — el módulo de pagos es un **adaptador de detección/registro**, nunca un procesador de cobros (en Uruguay no existe pasarela estatal única; en México el ATDT exige solo publicar alternativas).
- Tableros embebidos (Metabase/Superset) dentro de DiagMuni — son recomendaciones del plan generado, no componentes operados por la plataforma (ver guardarraíl AGPL en `docs/stack-tecnologico.md`).
- Onboarding self-service sin asistencia — el piloto asume una contraparte técnica designada por la intendencia (requisito de la convocatoria), no un funcionario anónimo llegando sin contexto.

## Funcionalidades

| # | Funcionalidad | Descripción |
|---|---|---|
| F1 | Cuestionario de captura | Formulario con lógica de ramificación, sin jerga técnica, respondible por un funcionario de mostrador |
| F2 | Motor de índice de madurez | Código determinista, versionado, config-driven; nunca hardcodeado |
| F3 | Generador de plan de modernización | Reglas brecha→acción (estructura enriquecida: paso administrativo/técnico/organizacional, prerrequisitos, por qué importa, costo/tiempo — nunca una línea circular tipo "habilitar X") + redacción en lenguaje natural asistida por LLM sobre esos datos ya decididos |
| F4 | Catálogo de componentes OSS recomendados | Por acción del plan, con licencia y actividad de la comunidad verificadas |
| F5 | Dimensionamiento y costeo del plan | Inversión estimada por acción, en MXN/UYU/USD, con fuente y fecha |
| F6 | Panel de seguimiento | Semáforo simple por acción del plan; mantenible por el gobierno local sin soporte externo |
| F7 | Multi-tenant y aislamiento de datos | RLS por `tenant_id`; los datos y el diagnóstico pertenecen al gobierno que los produce |
| F8 | Trazabilidad normativa | Cada regla y cada variable citan norma y artículo (MX/UY); versión de reglas queda ligada a cada diagnóstico generado |
| F9 | Verificador del plan | Tercera pieza de IA del producto: audita el plan generado por LLM contra las reglas del motor antes de mostrarlo — nunca pasa una acción alucinada o fuera de catálogo |

## Modelo conceptual de datos (alto nivel — el detalle exhaustivo va en el próximo documento, `docs/backend-schema.md`)

Entidades principales: `tenant` (gobierno local), `usuario` (funcionario, con rol), `tramite` (catálogo, por tenant), `diagnostico_tramite` (respuestas + índice calculado, versión de reglas), `plan_modernizacion` (acciones generadas), `accion_seguimiento` (estado del semáforo), `job` (async de generación de plan vía LLM).

## Requisitos no funcionales

- **Licencia**: Apache 2.0 en el repo propio; dependencias solo MIT/BSD/Apache; GPL solo como servicio separado; AGPL nunca integrado. Detalle completo en `docs/stack-tecnologico.md` principio 2.
- **Replicabilidad**: debe correr en un VPS económico o servidor único modesto — criterio rector de todo el stack, no preferencia.
- **Transferencia de capacidades**: sin dependencia del implementador original; documentación técnica en el repo desde el primer commit. El catálogo brecha→acción de F3 vive como texto estructurado editable (no hardcodeado en código) para que alguien sin conocimiento de programación pueda mantenerlo — es un catálogo finito por diseño (~10-15 entradas por país, acotado por el número de variables de diagnóstico), no un proyecto que dependa de una comunidad de contribuidores.
- **Reproducibilidad**: mismo dato de entrada → mismo índice de madurez, siempre, incluso si las reglas normativas cambian después (versionado de reglas).
- **Bilingüismo normativo**: toda variable y regla debe tener sentido tanto en el marco mexicano como en el uruguayo, sin excepciones sin etiquetar.

## Métricas de éxito del piloto

Definidas antes de implementar: número de trámites diagnosticados, índice de madurez inicial/final, tiempo de aplicación del instrumento, % de preguntas respondidas con evidencia, satisfacción del funcionario, adopción del plan (acciones iniciadas a 90 días).

## Riesgos abiertos que afectan el alcance del producto

1. **Capa de IA** — default de producción: DeepSeek + Claude vía API, con degradación a plantillas deterministas como mecanismo real de independencia de proveedor. Un modelo local cuantizado (evaluado: phi3/Phi-3-mini, MIT) queda documentado como alternativa disponible vía LiteLLM si cambia el criterio (presupuesto de API, política de datos, operación sin conexión a internet). Ver `docs/stack-tecnologico.md`.
2. **Alcance de "trámite" en México vs Uruguay** — el catálogo de trámites por país puede no ser 1:1; el modelo de datos debe soportar catálogos distintos por tenant sin asumir una lista fija compartida.

## Glosario

- **Trámite**: gestión o servicio administrativo específico que un ciudadano o empresa realiza ante el gobierno local.
- **Intendencia**: gobierno departamental en Uruguay (equivalente funcional a un municipio mexicano para efectos de este producto).
- **Índice de madurez**: nivel 0-4 de digitalización de un trámite, calculado por criterios binarios verificables. Nomenclatura de nivel (fijada en `entregables/fase-2/modelo-diagnostico.md`): 0 Presencial en papel · 1 Informativo · 2 Transaccional parcial · 3 Transaccional completo · 4 Proactivo e interoperable.
- **RLS**: Row-Level Security, mecanismo de PostgreSQL para aislar filas por `tenant_id` a nivel de motor de base de datos, no solo de aplicación.
- **CIIAR**: coalición de ciudades de Uruguay participante en la convocatoria (escribir siempre con doble I).

## Documentos relacionados

`docs/stack-tecnologico.md`, `docs/TRD.md`, `docs/ux-brief.md`, `docs/app-flow.md`, `docs/backend-schema.md`, `docs/plan-implementacion.md`.
