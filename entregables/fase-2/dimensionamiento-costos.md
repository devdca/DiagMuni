# Dimensionamiento del VPS y costos — Capa IA (escenario de modelo local)

Dimensiona y costea un VPS capaz de correr un modelo local cuantizado (candidato evaluado: phi3/Phi-3-mini, MIT) como generador de las tareas de IA del producto (F1, F3, F9), como **alternativa documentada** a la arquitectura vigente (DeepSeek + Claude vía API — ver `docs/stack-tecnologico.md`).

## 1. Por qué este escenario es una alternativa, no el default vigente

**Decisión vigente:** DeepSeek + Claude vía API como default de producción, con degradación a plantillas deterministas si la API no responde (ver `docs/stack-tecnologico.md`, "Nota sobre la Capa IA"). Un benchmark real comparó ambos caminos con el mismo párrafo de prueba (F3, "Firma electrónica"): la API de DeepSeek generó la respuesta en 5.8 segundos (~USD 0.00016 por llamada) contra 101-194 segundos de los mejores candidatos locales con licencia limpia — una diferencia de un orden de magnitud en latencia, con costo marginal insignificante para el volumen de un piloto.

El modelo local queda disponible como alternativa vía cambio de configuración de LiteLLM (sin tocar `engine/` ni el resto del backend), útil si el criterio cambia en el futuro: presupuesto de API, política de datos, o necesidad de operar sin conexión a internet. Lo que sigue en este documento dimensiona y costea ese escenario alternativo, para que quede listo si se necesita.

## 2. Qué se está dimensionando

Cuánto costaría un VPS si el modelo local (phi3/Phi-3-mini, MIT) reemplazara la arquitectura vigente (DeepSeek + Claude vía API) como default de producción de F1, F3 y F9. No es el presupuesto del piloto tal como está aprobado hoy — es una cotización de respaldo.

Contexto relevante que este documento no repite en extenso (ver `docs/stack-tecnologico.md` para el detalle completo):

- **Replicabilidad:** el stack debe correr en un VPS económico o un servidor único modesto de una intendencia pequeña — criterio rector, no preferencia tecnológica.
- **Infraestructura interna del Laboratorio** (servidor de oficina, Huawei FusionCube 1000H-X3, sin GPU): descartada como pista de inferencia local por falta de GPU; sus usos válidos son instancia canónica multi-tenant, runner de CI y staging de demo — nunca como estándar de replicabilidad del producto.
- phi3/Phi-3-mini es licencia MIT, sin excepción al principio de licencias del stack (Apache/MIT/BSD/GPL; AGPL nunca integrado).

## 3. Piso de hardware recomendado (si se activa el modelo local)

Con phi3/Phi-3-mini Instruct (GGUF Q4, ~2.2GB en disco) y el benchmark de referencia (CPU sin GPU, 4 núcleos: ~123s por generación de ~308 tokens — ver `docs/stack-tecnologico.md`):

- **Piso mínimo para correr solo la inferencia con margen:** 4 vCPU / 8 GB RAM. El modelo cuantizado ocupa ~2-3GB de RAM en ejecución (pesos + contexto); 8GB deja margen para el proceso de Ollama y el sistema operativo, pero **no** para correr en la misma máquina Postgres + FastAPI + nginx de un piloto multi-tenant con más de un tenant activo simultáneamente.
- **Piso recomendado si el VPS aloja todo el stack en una sola máquina** (Docker Compose completo: nginx + backend + db + Ollama): 8 vCPU / 16 GB RAM, para dejar 8-10GB disponibles a Postgres y al backend sin competir por memoria con el modelo cargado en cada generación.
- CPU moderna (2025-2026) de cualquier proveedor listado abajo tiene mejor IPC y soporte AVX2/AVX-512 que el hardware del benchmark — es razonable esperar latencia igual o mejor por núcleo, nunca peor, en igualdad de núcleos asignados. No se dispone de un benchmark propio en un VPS real al momento de escribir esto — el número de abajo es una traducción conservadora, no una medición.

## 4. Opciones de proveedor (4 vCPU / 8GB, piso mínimo) — precios y fuente

| Proveedor | Plan | Specs | Precio mensual aprox. | Fuente |
|---|---|---|---|---|
| Hetzner Cloud | CPX31 (shared vCPU, AMD) | 4 vCPU, 8 GB RAM, 160 GB NVMe | ~€16.49-19.49 (~USD 18-21) | [hetzner.com/cloud/regular-performance](https://www.hetzner.com/cloud/regular-performance) |
| Contabo | Cloud VPS 20 (o equivalente) | 4 vCPU, 8 GB RAM, ~200 GB SSD | ~USD 6.99-11.00 (varía por región/promoción) | confirmar precio exacto vigente en contabo.com al momento de compra |
| DigitalOcean | Basic Droplet / Premium AMD, 8 GiB | 4 vCPU (shared), 8 GB RAM | ~USD 48-54 (Premium AMD 8GiB) o USD 63 (CPU dedicada "General Purpose") | [digitalocean.com/pricing/droplets](https://www.digitalocean.com/pricing/droplets) |

## 5. Opción con headroom (8 vCPU / 16GB, recomendado para stack completo en una sola máquina)

| Proveedor | Plan | Specs | Precio mensual aprox. | Fuente |
|---|---|---|---|---|
| Hetzner Cloud | CPX41 | 8 vCPU, 16 GB RAM, 240 GB NVMe | ~€43-120 según región — verificar región exacta al contratar | [hetzner.com/cloud/regular-performance](https://www.hetzner.com/cloud/regular-performance) |
| Contabo | Cloud VPS con 6 vCores / 16GB (no ofrecen exactamente 8/16) | 6 vCore, 16 GB RAM | ~USD 11.00 | [comparevps.com/hosting/contabo](https://www.comparevps.com/hosting/contabo) |

Nota: los proveedores publican precios que cambian con frecuencia y varían por región/moneda/promoción — estos números son un piso orientativo para presupuestar, no una cotización firme; reverificar al momento de aprovisionar.

## 6. Nota de latencia esperada en un VPS moderno (rango conservador, no una promesa)

El benchmark real disponible es **122.8 segundos por generación de 308 tokens** (phi3/Phi-3-mini), en un CPU sin GPU de más de una década de antigüedad. Sin haber corrido el mismo benchmark en un VPS moderno, un rango conservador razonable para un VPS 4-8 vCPU actual (mejor IPC/AVX por núcleo) sería **40-100 segundos por generación de un párrafo similar (~300 tokens)** — en el mismo orden de magnitud que el piso de referencia de la arquitectura async del producto (30-60s típico vía API externa; ver "Job asíncrono" en `docs/TRD.md`), aunque en el extremo superior de ese rango; nunca prometer un número por debajo de ese rango sin repetir el benchmark en el proveedor y plan finalmente elegido.

## 7. Impacto en el presupuesto del piloto (techo USD 10,000)

No se tuvo acceso a un desglose línea por línea del presupuesto del piloto — no se debe inventar el total. Dato concreto a considerar si este escenario se activa:

- **Costo mensual adicional de VPS (si reemplaza, no se suma, al costo de API de DeepSeek/Claude):** ~USD 18-21/mes (piso mínimo 4 vCPU/8GB) o ~USD 45-70/mes (recomendado 8 vCPU/16GB, todo el stack en una máquina), según proveedor.
- **Comparación relevante:** esto no es un costo *adicional* neto si sustituye por completo el gasto variable de API por diagnóstico (DeepSeek/Claude) — ver sección 8 para el dato de costo por llamada ya medido.
- Si el piloto ya reserva una partida de infraestructura de servidor (probable, dado el techo de USD 10,000 total), un VPS de ~USD 20-70/mes cabe cómodamente dentro de cualquier partida mensual de infraestructura ya contemplada para 1-2 meses de piloto — el riesgo presupuestario de esta pieza específica es bajo.

## 8. Huecos declarados

Estos son huecos reales que este análisis no cubre todavía. No se fabrica ninguna cifra para cerrarlos; se documentan como pendientes de dato.

1. **Costo por diagnóstico completo, API externa vs. modelo local, mismo denominador.** Sin el dato de costo por diagnóstico vía API (DeepSeek/Claude) no se puede afirmar que el modelo local sea más barato en total — solo que el VPS en sí es barato.

   **Parcialmente cubierto:** prueba real contra la API de DeepSeek (`deepseek-v4-flash`), mismo prompt F3 ("Firma electrónica") que los benchmarks locales: 244 tokens de entrada, 460 de salida, 5.8s totales (incl. red), a precio vigente $0.14/millón tokens entrada (cache miss) y $0.28/millón tokens salida ⇒ **~USD 0.000163 por llamada de F3**. Sigue faltando el conteo equivalente para F1 y F9 (prompts más cortos, previsiblemente más baratos) para completar el costo por diagnóstico. A ese costo marginal, la diferencia de infraestructura entre API y modelo local es irrelevante para el presupuesto del piloto — lo que de verdad pesa en la decisión es la latencia (5.8s vs. 101-194s).
2. **Desglose línea por línea del presupuesto del piloto** (horas de implementación, viáticos, documentación, licenciamiento) — depende de decisiones de alcance y calendario del piloto concreto.
3. **Dimensionamiento y costo de VPS para la arquitectura actualmente vigente (API externa, sin modelo local).** El dimensionamiento de las secciones 3-6 es explícitamente para cargar el modelo local; no hay una cotización equivalente de VPS "económico genérico" para la arquitectura vigente (Docker Compose: nginx + backend + FastAPI + Postgres, sin Ollama ni modelo local en memoria), que previsiblemente requeriría specs menores y por tanto un costo mensual menor.
4. **Catálogo de costos paramétricos** (infraestructura, licenciamiento cero por OSS, capacitación, horas de implementación) por país y moneda (MXN/UYU/USD) — **atendido en `entregables/fase-2/catalogo-costos-oss.md` (03-ago-2026)**: costo de licenciamiento verificado en 0 para las 6 categorías del catálogo OSS (`backend/app/engine/catalogo/componentes_oss.yaml`); costo de infraestructura verificado con cifra concreta en 3 de 6 (`gestor_expediente_electronico`, `identidad_federada`, `conector_interoperabilidad`) y verificado como "no aplica" (sin servicio adicional que hostear) en otras 2 (`modulo_cifrado_datos`, `adaptador_pasarela_pago`); 1 de 6 (`modulo_firma_electronica`) queda `[NO VERIFICADO]` porque la fuente oficial de ese componente no publica una cifra de dimensionamiento. Costo de implementación/capacitación por hora de trabajo técnico queda `[NO VERIFICADO]` en las 6 categorías — sigue siendo un hueco real, no cerrado por esa iteración. Datos completos y fuentes en `backend/app/engine/catalogo/costos_oss.yaml` y `entregables/fase-2/catalogo-costos-oss.md`.
