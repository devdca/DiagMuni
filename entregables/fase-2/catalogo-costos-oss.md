# Catálogo de costos paramétricos por componente OSS — F5 (`docs/PRD.md` líneas 53-54)

Cierre del hueco declarado en `entregables/fase-2/dimensionamiento-costos.md`, sección 8, punto 4 ("Catálogo de costos paramétricos... por país y moneda — no cubierto todavía"). Paso 2 de 4 del pendiente #2 de backend; insumo directo: `backend/app/engine/catalogo/componentes_oss.yaml` y `entregables/fase-2/catalogo-componentes-oss.md` (paso 1, ya aprobado). Fecha de esta verificación: 3 de agosto de 2026.

Objetivo: para cada una de las 6 categorías `categoria_catalogo` (`modulo_cifrado_datos`, `gestor_expediente_electronico`, `modulo_firma_electronica`, `identidad_federada`, `conector_interoperabilidad`, `adaptador_pasarela_pago`), estimar el costo de adopción por parte de un municipio pequeño (~5,000 habitantes) o una intendencia con área TIC propia (`docs/PRD.md`, "Usuario objetivo"), desglosado en licenciamiento, infraestructura/hosting e implementación/capacitación, en MXN/UYU/USD, con fuente y fecha. Mismo estándar de rigor que `entregables/fase-2/dimensionamiento-costos.md` y `entregables/fase-2/catalogo-componentes-oss.md`: ninguna cifra sin fuente citada; lo que no se pudo fundamentar con una fuente real se marca `[NO VERIFICADO]`, nunca se inventa un número para cerrar una categoría.

Resultado del cierre: **3 de 6 categorías con costo de infraestructura verificado con cifra concreta** (`gestor_expediente_electronico`, `identidad_federada`, `conector_interoperabilidad`); **2 de 6 sin costo de infraestructura aplicable porque no requieren un servicio adicional que hostear** (`modulo_cifrado_datos`, `adaptador_pasarela_pago` — declarado como hecho verificado, no como hueco); **1 de 6 con costo de infraestructura `[NO VERIFICADO]`** (`modulo_firma_electronica`, porque la fuente oficial no publica una cifra concreta). **Costo de licenciamiento verificado en 0 para las 6 categorías** (todas OSS, ya confirmado en el paso 1). **Costo de implementación/capacitación `[NO VERIFICADO]` en las 6 categorías** — no se encontró ninguna fuente pública citable de horas típicas de despliegue por componente; se documenta como hueco honesto en las 6, en vez de fabricar una cifra a partir de tarifas de mercado sueltas sin un número de horas verificable que multiplicar.

---

## 0. Tipo de cambio usado

- **MXN por USD:** 17.3562 — Banco de México, tipo de cambio FIX (serie `SF63528`), consultado directamente en `https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?sector=6&accion=consultarCuadro&idCuadro=CF373&locale=es` el 03-ago-2026. La tabla de observaciones más recientes disponible en esa consulta mostró tres columnas (29/07/2026: 17.5133; 30/07/2026: 17.3562; 31/07/2026: 17.3288). El valor **aplicable a obligaciones denominadas en USD pagaderas el 03-ago-2026 es el determinado el 30-jul-2026 (17.3562)**, no el determinado el 31-jul-2026, conforme a las Disposiciones aplicables a la determinación del tipo de cambio para solventar obligaciones denominadas en moneda extranjera pagaderas en la República Mexicana (Banco de México, Circular 3/2012, Título Tercero, Capítulo V): el FIX que se determina un día hábil bancario se publica en el DOF un día hábil después, y es el aplicable para solventar obligaciones en dólares el día hábil bancario siguiente a esa publicación — es decir, el segundo día hábil bancario después de su determinación. Contado desde el jueves 30-jul-2026, el segundo día hábil bancario siguiente (saltando sábado/domingo) es el lunes 03-ago-2026, fecha de esta verificación.
- **UYU por USD:** 40.0979 — Wise, histórico de cotización de mercado USD/UYU, `https://wise.com/us/currency-converter/usd-to-uyu-rate/history`, consultado 03-ago-2026, dato para esa fecha exacta. **Advertencia honesta:** este no es un tipo de cambio oficial del Banco Central del Uruguay ni del BROU — es una cotización de mercado de un proveedor de remesas/cambio. Se intentó obtener la cotización oficial por dos vías:
  1. `https://www.bcu.gub.uy/Estadisticas-e-Indicadores/Paginas/Cotizaciones.aspx` — la página carga el valor mediante un widget dinámico que no expone la cifra en el HTML estático obtenido; no se pudo extraer un número verificable de esta fuente en esta consulta.
  2. `https://www.brou.com.uy/cotizaciones` — mismo problema: la cotización se carga vía JavaScript/AJAX, no visible en el HTML estático.
  3. Caja Notarial del Uruguay publica una tabla histórica de la "cotización comprador pizarra BROU" en `https://www.cajanotarial.org.uy/innovaportal/v/4781/1/innova.front/cotizacion-dolar-2026-cotizacion-comprador-pizarra-brou.html?page=2` (tabla julio-diciembre 2026): al momento de la consulta, la columna de agosto 2026 estaba **vacía** (sin publicar todavía) y el último dato disponible de julio 2026 (día 3) era 39.00 UYU por USD — del mismo orden de magnitud que el dato de Wise (40.0979), lo que da una cota de contraste razonable aunque no una confirmación exacta para la fecha 03-ago-2026 específica.
  Se documenta esta limitación explícitamente en vez de presentar la cifra de Wise como si fuera la cotización oficial. Todo cálculo UYU de este documento hereda esta advertencia.

---

## 1. `modulo_cifrado_datos` — pgcrypto

**Por qué importa (contexto de uso, `backend/app/engine/reglas/datos_personales.yaml`):** "Cifrado en tránsito/reposo de los datos personales capturados (estándar, no marca)" — obligación legal transversal (LGPDPPSO arts. 20-22, 25-28 en México; Ley 18.331 + 19.670 arts. 37-40 en Uruguay), no ligada a un nivel específico del índice.

**Costo de licenciamiento:** 0 MXN/UYU/USD. Licencia estilo BSD permisiva, ya verificada en `catalogo-componentes-oss.md` sección 1.

**Costo de infraestructura:** 0 (no aplica). pgcrypto es una extensión de PostgreSQL (`contrib/pgcrypto`), no un servicio independiente. Se habilita con una sola sentencia SQL (`CREATE EXTENSION pgcrypto;`) dentro del mismo motor PostgreSQL que el sistema de trámites de la intendencia/municipio ya necesita para operar — no agrega cómputo, memoria ni un servicio nuevo que hostear. Fuente del mecanismo de habilitación: `https://www.postgresql.org/docs/current/pgcrypto.html`.

**Costo de implementación:** `[NO VERIFICADO]`. Lo que sí tiene costo real de horas de trabajo es adaptar el código de la aplicación de trámites para cifrar/descifrar los campos de datos personales (funciones `pgp_sym_encrypt`/`pgp_sym_decrypt`, entre otras) y capacitar al personal en tratamiento de datos personales — pero ese trabajo depende por completo del sistema de trámites existente de cada municipio (variable, no estandarizable) y no se encontró una fuente pública que documente un número de horas típico para ese tipo de adaptación aplicado específicamente a un sistema de trámites municipal. No se fabrica la cifra.

---

## 2. `gestor_expediente_electronico` — Mayan EDMS

**Por qué importa (`documentos_papel_digital.yaml`):** "Digitalizar el expediente y adoptar un gestor de expediente electrónico" — bloquea el paso de índice 0 a 1, prerrequisito de cualquier transaccionalidad completa.

**Costo de licenciamiento:** 0 MXN/UYU/USD. Apache-2.0, ya verificado en `catalogo-componentes-oss.md` sección 2.

**Costo de infraestructura — verificado con cifra concreta:**
- Requisitos oficiales consultados directamente en `https://docs.mayan-edms.com/chapters/requirements.html` (03-ago-2026):
  - **Mínimo:** 4 GB RAM; CPU dual-core, 64 bit, 1 GHz o más rápido; PostgreSQL 13.11 o superior.
  - **Recomendado (Docker Compose)**, el método de despliegue que el propio proyecto documenta como preferido: 16 GB RAM o más; CPU de 64 bit, 8 núcleos o más, 2 GHz o más rápido; almacenamiento SSD.
- **Cotización del piso mínimo:** Contabo Cloud VPS 4 (4 vCPU, 8 GB RAM, 100 GB SSD) — precio obtenido directamente del dato estructurado `schema.org Product/AggregateOffer` embebido en el HTML de `https://contabo.com/en/vps/` (03-ago-2026): **USD 6.60/mes** (también EUR 5.50, GBP 5.40). Esta especificación excede cómodamente el mínimo oficial de Mayan EDMS.
  - Equivalente MXN: 6.60 × 17.3562 = **114.55 MXN/mes**.
  - Equivalente UYU: 6.60 × 40.0979 = **264.65 UYU/mes** (con la advertencia de tipo de cambio de la sección 0).
  - **Advertencia de volatilidad:** distintos agregadores de terceros (no la fuente primaria de Contabo) muestran precios distintos para especificaciones equivalentes de 4 vCPU/8 GB en fechas cercanas (entre USD 4.95 y USD 7.95, según región/promoción/nomenclatura de plan) — reverificar el precio exacto directamente en contabo.com al momento de contratar, mismo criterio ya aplicado en este documento al precio de DigitalOcean.
- **Escalón recomendado (Docker Compose, 16 GB/8 núcleos):** no se cotizó con la misma verificación estructurada en esta consulta — el sitio de Contabo solo expuso datos estructurados verificables para el nivel "Cloud VPS 4"; los niveles superiores (`Cloud VPS 6/8/12/16/18`) están listados por nombre en la página pero sin precio embebido de forma estática verificable en este pase. Se marca ese escalón superior como **`[NO VERIFICADO]`** en vez de estimarlo por extrapolación.

**Costo de implementación:** `[NO VERIFICADO]`. No se encontró una fuente pública citable de horas típicas de despliegue + configuración (indexación de metadatos, flujos de OCR, permisos) + capacitación del personal de archivo/mostrador para un municipio pequeño. No se fabrica la cifra.

---

## 3. `modulo_firma_electronica` — DSS (esig/dss)

**Por qué importa (`firma_electronica.yaml`):** "Integrar verificación de firma con estándar abierto (PAdES/XAdES)" — bloquea el paso de índice 2 a 3. Se despliega como **servicio separado** por la intendencia, no linkeado al backend de DiagMuni (ver nota de `catalogo-componentes-oss.md` sección 3).

**Costo de licenciamiento:** 0 MXN/UYU/USD. LGPL-2.1, ya verificado en `catalogo-componentes-oss.md` sección 3.

**Costo de infraestructura — `[NO VERIFICADO]`:** se consultó directamente la documentación oficial de DSS, `https://ec.europa.eu/digital-building-blocks/DSS/webapp-demo/doc/dss-documentation.html`, secciones "2.1.1.1. Requirements" (DSS framework) y "2.1.2.1. Requirements" (DSS Demonstration Applications, el `dss-demo-webapp` que se ejecutaría como servicio). Ambas secciones remiten a: *"Memory and Disk: see minimal requirements for the used JVM. In general the higher available is better"* — es decir, la fuente oficial **explícitamente declina dar una cifra concreta** de RAM/CPU/disco, delegando al requisito genérico de la JVM utilizada (Java 17+ para `dss-demo-webapp` desde DSS 6.0, Tomcat 10+ o empaquetado como bundle con Tomcat 11). No se encontró en ninguna otra fuente oficial (repositorio `esig/dss`, `esig/dss-demonstrations`) una cifra de dimensionamiento específica para este servicio. Fabricar una cifra a partir de una convención genérica de aplicaciones Java/Spring Boot (que no está atada a DSS específicamente) violaría la restricción de esta tarea de no inventar números — se documenta el hueco.

**Costo de implementación:** `[NO VERIFICADO]`. Misma razón que arriba — no hay fuente pública citable de horas típicas de despliegue + configuración de listas de confianza + capacitación para este servicio en un contexto municipal.

**Nota operativa (no es una cifra de costo, es contexto):** dado que el requisito real es genérico ("una JVM con memoria suficiente"), es plausible que este servicio pudiera coexistir en el mismo VPS ya cotizado para `identidad_federada` o `conector_interoperabilidad` (ambos con headroom sobre su propio mínimo en la cotización de Contabo Cloud VPS 4), pero esto es una posibilidad de arquitectura, no una cifra de costo verificada — no se declara como ahorro cuantificado.

---

## 4. `identidad_federada` — Keycloak

**Por qué importa (`identidad_acceso.yaml`):** "Integración con proveedor de identidad federada nacional" (Llave MX / ID Uruguay) — refuerza el paso a índice 3-4.

**Costo de licenciamiento:** 0 MXN/UYU/USD. Apache-2.0, ya verificado en `catalogo-componentes-oss.md` sección 4.

**Costo de infraestructura — verificado con cifra concreta:**
- Requisito mínimo oficial, consultado directamente en la documentación de DigitalOcean para el 1-Click App de Keycloak (`https://docs.digitalocean.com/products/marketplace/catalog/keycloak/`, 03-ago-2026): *"Keycloak requires 2GB of RAM and 2CPU cores, AT MINIMUM."* La misma página documenta, en su ejemplo oficial de creación de Droplet vía API, el tamaño recomendado real para el 1-Click: `"size":"s-2vcpu-4gb"` (2 vCPU, 4 GB RAM).
  - Nota: se descartó como referencia la guía de sizing de "Red Hat build of Keycloak" / `keycloak.org/high-availability` porque esos números (ej. 1250 MB de RAM base por Pod, más de 1 vCPU por cada 15 logins/segundo) están calculados para *clústeres de alta disponibilidad multi-región a escala empresarial* — un orden de magnitud de carga muy por encima de una intendencia o municipio piloto con un puñado de funcionarios y trámites, por lo que no es la cifra relevante para este caso de uso; se prioriza el requisito mínimo documentado para un despliegue de instancia única.
- **Cotización 1 (piso mínimo):** Contabo Cloud VPS 4 (4 vCPU/8 GB) — **USD 6.60/mes** (misma fuente y precio que en la sección 2; ver advertencia de volatilidad de esa misma sección, aplicable aquí igual). Excede el mínimo oficial de Keycloak.
  - Equivalente MXN: 6.60 × 17.3562 = **114.55 MXN/mes**. Equivalente UYU: **264.65 UYU/mes**.
- **Cotización 2 (tamaño recomendado exacto del 1-Click oficial, 2 vCPU/4 GiB):** DigitalOcean Basic Droplet — **USD 24.00/mes**, según consulta del 03-ago-2026 contra `https://www.digitalocean.com/pricing/droplets`. Advertencia de método: el contenido de precios de esa página se renderiza vía JavaScript y no pudo extraerse por scraping estático directo en esta sesión; la cifra de USD 24.00/mes se tomó de una consulta agregada contra el contenido de esa misma página oficial, consistente con el precio de USD 24/mes que DigitalOcean ha publicado de forma estable para su Droplet Básico de 2 vCPU/4 GiB — se recomienda reverificar el dígito exacto directamente en el sitio al momento de contratar, mismo criterio de honestidad que ya usa `dimensionamiento-costos.md` para los precios de Hetzner/Contabo.
  - Equivalente MXN: 24.00 × 17.3562 = **416.55 MXN/mes**. Equivalente UYU: 24.00 × 40.0979 = **962.35 UYU/mes**.

**Costo de implementación:** `[NO VERIFICADO]`. No se encontró una fuente pública citable de horas típicas de configuración de realms/clientes OIDC-SAML e integración con Llave MX/ID Uruguay, ni de capacitación del personal, para un municipio pequeño. Se encontró evidencia cualitativa de que despliegues Keycloak "enterprise-ready" completos toman de 2 a 6 meses (fuente: `hoop.dev/blog/saving-engineering-hours-with-managed-keycloak-solutions`), pero es un rango para escenarios empresariales complejos, no una cifra de horas aplicable a la integración puntual de un municipio pequeño con un solo proveedor de identidad nacional — no se traduce a un número de horas/costo porque haría falta inventar el factor de reducción de escala. Se documenta el hallazgo cualitativo sin convertirlo en cifra.

---

## 5. `conector_interoperabilidad` — X-Road

**Por qué importa (`interoperabilidad.yaml`):** "Conector de interoperabilidad nacional" — requisito de índice 4 (proactivo e interoperable). Recuérdese la advertencia ya documentada en `catalogo-componentes-oss.md` sección 5: X-Road sustituye al Cliente PDI de AGESIC (sin licencia verificable) solo para efectos de este catálogo genérico; no reemplaza la obligación legal de un municipio uruguayo de integrarse con la PDI real de AGESIC (Ley 18.719 arts. 157-160). El costeo de esta sección hereda la misma advertencia: es el costo de adoptar X-Road como componente de catálogo, no el costo de la integración con la PDI de AGESIC en producción (que este documento no cubre, por no tener una implementación OSS verificable equivalente).

**Costo de licenciamiento:** 0 MXN/UYU/USD. MIT, ya verificado en `catalogo-componentes-oss.md` sección 5.

**Costo de infraestructura — verificado con cifra concreta:**
- Requisito mínimo oficial del **Security Server** (el componente que despliega cada organismo/intendencia que se conecta a la capa de interoperabilidad — distinto del Central Server y del Configuration Proxy, que son responsabilidad de quien opera la capa a nivel nacional, no de cada municipio), consultado directamente en las guías oficiales de instalación:
  - Ubuntu: `https://docs.x-road.global/Manuals/ig-ss_x-road_v6_security_server_installation_guide.html` — CPU dual-core de 64 bits (soporte AES recomendado), **4 GB RAM**, NIC de 100 Mbps.
  - RHEL: `https://docs.x-road.global/Manuals/ig-ss_x-road_v6_security_server_installation_guide_for_rhel.html` — mismos requisitos (2 núcleos de CPU, 4 GB RAM, 10 GB para partición de SO, 20-40 GB para `/var`).
  - Con los módulos de monitoreo/op-monitoring activos, el mínimo oficial también es 4 GB RAM (no sube).
- **Cotización:** Contabo Cloud VPS 4 (4 vCPU/8 GB) — **USD 6.60/mes** (misma fuente que secciones 2 y 4; ver advertencia de volatilidad de la sección 2, aplicable aquí igual). Excede el mínimo oficial de 4 GB RAM/CPU dual-core.
  - Equivalente MXN: 6.60 × 17.3562 = **114.55 MXN/mes**. Equivalente UYU: **264.65 UYU/mes**.

**Costo de implementación:** `[NO VERIFICADO]`. No se encontró en la documentación oficial de X-Road (guías de instalación, manual de usuario del Security Server) ninguna estimación de horas típicas de instalación + registro del organismo en la capa de interoperabilidad + capacitación del enlace técnico designado. No se fabrica la cifra.

---

## 6. `adaptador_pasarela_pago` — django-payments

**Por qué importa (`motor_pagos.yaml`):** "Adaptador de pago en línea configurable — nunca una pasarela única fija" — bloquea el paso a índice 3 (transaccional completo). Recuérdese que ni México ni Uruguay tienen una pasarela de pagos estatal única obligatoria (ver `entregables/fase-2/verificacion-motor-pagos.md`).

**Costo de licenciamiento:** 0 MXN/UYU/USD. BSD-3-Clause, ya verificado en `catalogo-componentes-oss.md` sección 6.

**Costo de infraestructura:** 0 (no aplica). django-payments es una **librería** Python/Django que se integra al código del propio sistema de trámites de la intendencia/municipio (patrón adaptador multi-proveedor de pago), no un servicio independiente que se despliegue y hostee por separado — así quedó documentado explícitamente en la nota de `catalogo-componentes-oss.md` sección 6 ("no como dependencia de DiagMuni" ni como servicio autónomo). No añade cómputo dedicado más allá del que ya requiere el sistema de trámites en el que se integra.

**Costo de implementación:** `[NO VERIFICADO]`. El trabajo real (configurar el adaptador para el proveedor de pago elegido por la intendencia, habilitar la cuenta bancaria institucional para cobros electrónicos, capacitar a caja/tesorería) depende por completo del sistema de trámites existente de cada municipio y del proveedor de pago que finalmente contrate — no hay un número de horas estandarizable ni una fuente pública que lo documente para este caso de uso genérico. No se fabrica la cifra.

---

## 7. Resumen

| Categoría | Licenciamiento | Infraestructura | Implementación |
|---|---|---|---|
| `modulo_cifrado_datos` | 0 (verificado) | 0, no aplica (verificado) | `[NO VERIFICADO]` |
| `gestor_expediente_electronico` | 0 (verificado) | USD 6.60/mes piso mínimo (verificado); escalón recomendado Docker `[NO VERIFICADO]` | `[NO VERIFICADO]` |
| `modulo_firma_electronica` | 0 (verificado) | `[NO VERIFICADO]` (fuente oficial no da cifra) | `[NO VERIFICADO]` |
| `identidad_federada` | 0 (verificado) | USD 6.60-24.00/mes (verificado) | `[NO VERIFICADO]` |
| `conector_interoperabilidad` | 0 (verificado) | USD 6.60/mes (verificado) | `[NO VERIFICADO]` |
| `adaptador_pasarela_pago` | 0 (verificado) | 0, no aplica (verificado) | `[NO VERIFICADO]` |

**Conclusión:** las 6 categorías cierran el costo de licenciamiento (0, por ser OSS — hecho verificado, no hueco) y 5 de 6 cierran el costo de infraestructura con una cifra concreta o con la determinación verificada de que no aplica un servicio adicional (`modulo_cifrado_datos`, `gestor_expediente_electronico` en su piso mínimo, `identidad_federada`, `conector_interoperabilidad`, `adaptador_pasarela_pago`); solo `modulo_firma_electronica` queda con el costo de infraestructura como hueco honesto porque la fuente oficial de DSS explícitamente no publica una cifra. El costo de implementación/capacitación queda `[NO VERIFICADO]` en las 6 categorías — no existe, en ninguna de las fuentes oficiales consultadas, una estimación de horas de despliegue específica por componente aplicable a un municipio pequeño; emparejar una tarifa de mercado suelta (encontrada para desarrolladores/DevOps en LATAM) con una cifra de horas inventada habría producido un número con apariencia de precisión pero sin fundamento real, exactamente lo que esta tarea prohíbe. Se deja como pendiente de dato explícito para una futura iteración, idealmente alimentado con datos reales del piloto (horas efectivamente invertidas) en vez de una estimación externa.
