# Catálogo de componentes OSS por categoría — F4 (`docs/PRD.md` líneas 53-54)

Cierre del pendiente #2 de backend, paso 1 de 4. Objetivo: para cada una de las 6 categorías `categoria_catalogo` que ya existen en `backend/app/engine/reglas/*.yaml` (verificadas por el coordinador, una única aparición por archivo, idénticas en las ramas `mx`/`uy`), recomendar un componente OSS real y concreto, con licencia y actividad de comunidad verificadas contra la fuente primaria. Fecha de la verificación: 3 de agosto de 2026. Método: lectura directa de archivos `LICENSE`/`LICENSE.txt` en la rama por defecto del repositorio oficial (vía `raw.githubusercontent.com`) y de metadatos de actividad vía la API de GitHub (`api.github.com/repos/...`), complementado con WebSearch para descubrir candidatos y contexto institucional. Mismo estándar de rigor que `entregables/fase-2/verificacion-motor-pagos.md` y que la nota de LiteLLM en `docs/stack-tecnologico.md` (verificación contra el archivo real del repositorio, no inferencia por patrón de organización o lenguaje).

Resultado del cierre: **6 de 6 categorías con componente verificado** (0 huecos `[NO VERIFICADO]`). No se fuerza ninguna cita ni licencia — donde la fuente originalmente sugerida por el proyecto (Cliente PDI de AGESIC) no pudo verificarse, se documenta el hallazgo negativo y se sustituye por una alternativa que sí se pudo verificar, con la sustitución declarada explícitamente (ver sección 5).

---

## 1. `modulo_cifrado_datos` — cifrado de datos personales en tránsito/reposo

**Regla de origen:** `datos_personales.yaml`, `paso_tecnico`: "Cifrado en tránsito/reposo de los datos personales capturados (estándar, no marca)".

**Candidatos investigados:**
- **HashiCorp Vault** — descartado sin llegar a verificación de licencia: HashiCorp migró sus productos (incluido Vault) de MPL-2.0 a la Business Source License (BSL) en agosto de 2023; BSL no es una licencia OSI-approved y no está en la lista MIT/BSD/Apache/GPL del Principio 2 de `docs/stack-tecnologico.md`. Se descarta sin más búsqueda porque el motivo de descarte es estructural (licencia), igual que n8n y Camunda 8 en ese mismo documento.
- **age** (`FiloSottile/age`) — herramienta de cifrado de archivos de propósito general (BSD-3-Clause), pero no es un "módulo" integrable a nivel de columna/base de datos para el caso de uso (cifrado de campos de datos personales en un sistema de trámites); se descarta por ajuste al caso de uso, no por licencia.
- **pgcrypto** — elegido. Es la extensión criptográfica que ya se distribuye dentro del propio código fuente de PostgreSQL (`contrib/pgcrypto`), el motor de base de datos ya fijado en `docs/stack-tecnologico.md` (PostgreSQL 16). Provee cifrado simétrico/asimétrico a nivel de columna (`pgp_sym_encrypt`/`pgp_pub_encrypt`, entre otras), exactamente el tipo de mecanismo que un municipio necesitaría para cifrar campos de datos personales en su propio sistema de trámites.

**Verificación de licencia (03-ago-2026):** lectura directa del encabezado de `contrib/pgcrypto/pgcrypto.c` en la rama `master` de `github.com/postgres/postgres`: "Copyright (c) 2001 Marko Kreen. All rights reserved. Redistribution and use in source and binary forms, with or without modification, are permitted provided that..." — texto de licencia permisiva estilo BSD (2 cláusulas: atribución de copyright + disclaimer de garantía), sin cláusula de cambio de nombre ni restricción de uso comercial. Fuente exacta: `https://raw.githubusercontent.com/postgres/postgres/master/contrib/pgcrypto/pgcrypto.c`. Adicionalmente, `contrib/pgcrypto/pgcrypto.control` en la rama `REL_16_STABLE` (PostgreSQL 16, versión ya fijada del stack) declara `default_version = '1.3'`, confirmando que el módulo está incluido y versionado dentro de esa rama estable concreta: `https://raw.githubusercontent.com/postgres/postgres/REL_16_STABLE/contrib/pgcrypto/pgcrypto.control`.

**Evidencia de actividad (03-ago-2026):** consulta a `https://api.github.com/repos/postgres/postgres/commits?path=contrib/pgcrypto&per_page=3` — el commit más reciente sobre esa ruta específica es del 2026-06-22 ("pgcrypto: avoid recursive ResourceOwnerForget()", corrección de un bug reportado). El repositorio `postgres/postgres` en sí tiene `pushed_at: 2026-08-03` (el mismo día de esta verificación). No tiene ciclo de releases independiente — se distribuye con cada release trimestral de PostgreSQL, lo cual es la señal de actividad relevante para un módulo `contrib` del núcleo (no un proyecto satélite).

**Conclusión:** verificado. Licencia BSD-style permisiva, actividad de mantenimiento confirmada dentro del propio ciclo de vida de PostgreSQL 16.

---

## 2. `gestor_expediente_electronico` — expediente electrónico

**Regla de origen:** `documentos_papel_digital.yaml`, `paso_tecnico`: "Digitalizar el expediente y adoptar un gestor de expediente electrónico (categoría, no marca)". Este es el hueco que `docs/stack-tecnologico.md` (sección "Pendiente de catálogo") ya declaraba explícitamente como pendiente de una futura iteración — esta tarea lo cierra.

**Candidatos investigados:**
- **OpenKM Community Edition** — descartado por licencia: GPL-2.0 (copyleft fuerte). Se prefiere un candidato sin ninguna condición de copyleft si existe uno técnicamente equivalente, para no tener que documentar la excepción de "servicio separado" del Principio 2.
- **Alfresco Community Edition** — descartado por licencia: LGPL-3.0 (copyleft débil, pero con condiciones adicionales de la versión 3 más estrictas que LGPL-2.1); además su modelo de distribución "Community" ha tenido cambios de gobernanza recientes (Hyland) que introducen incertidumbre sobre continuidad de la edición libre a mediano plazo.
- **Mayan EDMS** — elegido. Sistema de gestión documental (DMS) en Python/Django, con indexación de metadatos personalizables, OCR, versionado de documentos y verificación de firma electrónica — cubre exactamente el caso de uso de expediente electrónico digitalizado con captura y resguardo.

**Verificación de licencia (03-ago-2026):** lectura directa de `https://raw.githubusercontent.com/mayan-edms/Mayan-EDMS/master/LICENSE` — el archivo declara: "Copyright 2011 Roberto Rosario. Licensed under the Apache License, Version 2.0 (the "License")..." — Apache-2.0 sin condiciones adicionales. Confirmado además por el campo `license.key: "other"` de la API de GitHub (el detector automático de GitHub no siempre reconoce el texto exacto cuando el encabezado de copyright es no estándar, por lo que se prioriza la lectura directa del archivo sobre el campo automático — mismo criterio aplicado a LiteLLM en `docs/stack-tecnologico.md`).

**Evidencia de actividad (03-ago-2026):** `https://api.github.com/repos/mayan-edms/Mayan-EDMS` — `pushed_at: 2026-05-23`, 823 estrellas, solo 5 issues abiertos (backlog bajo, indicio de que los reportes se atienden y no se acumulan). No se pudo obtener un release etiquetado vía el endpoint `/releases/latest` en esta consulta, pero el historial de commits recientes y el bajo backlog de issues son evidencia suficiente de un proyecto vivo, no abandonado.

**Conclusión:** verificado. Apache-2.0 sin ambigüedad, actividad reciente confirmada.

---

## 3. `modulo_firma_electronica` — firma electrónica (PAdES/XAdES)

**Regla de origen:** `firma_electronica.yaml`, `paso_tecnico`: "Integrar verificación de firma con estándar abierto (PAdES/XAdES)" — la propia regla ya nombra el estándar técnico exacto que el componente debe implementar.

**Candidatos investigados:**
- **OpenPDF** (fork de iText 4) — implementa manipulación de PDF con soporte de firma, pero no es una implementación de referencia de los estándares PAdES/XAdES/CAdES en sí; se descarta por ajuste al caso de uso (herramienta de bajo nivel, no un servicio de firma/validación).
- **DSS (Digital Signature Service, `esig/dss`)** — elegido. Es la implementación de referencia mantenida institucionalmente por la Comisión Europea (European Commission, "Digital Building Blocks") para creación, extensión y validación de firmas electrónicas avanzadas — soporta explícitamente XAdES, CAdES, PAdES, JAdES y ASiC, exactamente los estándares que la propia regla `firma_electronica.yaml` nombra.

**Verificación de licencia (03-ago-2026):** lectura directa de `https://raw.githubusercontent.com/esig/dss/master/LICENSE` — encabezado "GNU LESSER GENERAL PUBLIC LICENSE Version 2.1, February 1999". Confirmado también por el campo `license.key: "lgpl-2.1"` de `https://api.github.com/repos/esig/dss` (aquí sí coincide el detector automático de GitHub con la lectura directa). Se revisó además el listado de la raíz del repositorio (`https://api.github.com/repos/esig/dss/contents/`): un único archivo `LICENSE` en la raíz, sin un directorio separado tipo `enterprise/` con licencia distinta (a diferencia de LiteLLM) — no hay ambigüedad de licencias mixtas dentro del repositorio.

**Nota sobre LGPL-2.1 (familia GPL):** LGPL-2.1 es copyleft débil — permite enlazar/usar la librería desde software con licencia distinta sin contaminarlo, siempre que las modificaciones a la propia librería LGPL se compartan. Bajo el Principio 2 de `docs/stack-tecnologico.md` ("GPL solo si se documenta explícitamente por qué no contamina la distribución, ej. servicio separado, no linkeado"), se documenta aquí: DSS se recomienda como **servicio de validación/firma desplegado de forma separada** por la intendencia (mismo patrón que la recomendación de osTicket GPL-2.0-or-later y Metabase AGPL-3.0 ya existentes en el catálogo de `docs/stack-tecnologico.md`) — nunca como librería integrada al backend Python/FastAPI de DiagMuni. No hay linking de código entre DSS (Java) y el repositorio de DiagMuni.

**Evidencia de actividad (03-ago-2026):** `https://api.github.com/repos/esig/dss` — `pushed_at: 2026-07-24`, 1016 estrellas, solo 4 issues abiertos (backlog muy bajo). Último release etiquetado: `6.4`, publicado 2026-03-06 (`https://api.github.com/repos/esig/dss/releases/latest`). Mantenimiento institucional activo confirmado por releases recientes de la Comisión Europea relacionados con cambios regulatorios (actualización de listas de confianza según el Diario Oficial de la UE, abril 2026).

**Conclusión:** verificado. LGPL-2.1 admisible con la nota de "servicio separado" ya documentada, actividad institucional y técnica confirmada.

---

## 4. `identidad_federada` — identidad federada / acceso único

**Regla de origen:** `identidad_acceso.yaml`, `paso_tecnico`: "Integración con proveedor de identidad federada nacional (categoría, no marca)".

**Candidatos investigados:**
- **Ory Kratos/Hydra** — suite de identidad moderna, Apache-2.0, pero fragmentada en múltiples proyectos separados para cada función (identidad, OAuth2, permisos); se prefiere un componente único y más maduro para el caso de uso de "acceso único a un proveedor de identidad federada nacional" (Llave MX, ID Uruguay).
- **Keycloak** — elegido. Solución de gestión de identidad y acceso (IAM) madura, con soporte nativo de OIDC y SAML — los dos protocolos estándar mediante los cuales un municipio integraría su sistema de trámites con un proveedor de identidad federada nacional como Llave MX o ID Uruguay/gub.uy, sin necesidad de implementar el protocolo desde cero.

**Verificación de licencia (03-ago-2026):** lectura directa de `https://raw.githubusercontent.com/keycloak/keycloak/main/LICENSE.txt` — encabezado "Apache License, Version 2.0". Confirmado también por el campo `license.key: "apache-2.0"` de `https://api.github.com/repos/keycloak/keycloak`.

**Evidencia de actividad (03-ago-2026):** `https://api.github.com/repos/keycloak/keycloak` — `pushed_at: 2026-08-03` (mismo día de esta verificación), 35967 estrellas, 3102 issues abiertos (volumen alto pero consistente con un proyecto de esta escala, con triage visible en releases de parche frecuentes). Último release: `26.7.0`, publicado 2026-07-09 (`https://api.github.com/repos/keycloak/keycloak/releases/latest`); se identificaron además releases de parche recientes (`26.6.1`, `26.6.2`, `26.6.3`) anunciados en `keycloak.org/2026/04/keycloak-2661-released` y posts sucesivos — cadencia de release mensual sostenida.

**Conclusión:** verificado. Apache-2.0 sin ambigüedad, uno de los proyectos OSS de IAM con mayor actividad y adopción verificable.

---

## 5. `conector_interoperabilidad` — interoperabilidad con otros registros

**Regla de origen:** `interoperabilidad.yaml`. La rama `mx` pide "Conector de interoperabilidad nacional (categoría, no marca)"; la rama `uy` cita textualmente "Cliente PDI de AGESIC (ya en catálogo OSS, docs/stack-tecnologico.md)" — es decir, el propio YAML de reglas apunta a una recomendación que `docs/stack-tecnologico.md` ya dejó marcada como **`[NO VERIFICADO]`** por ausencia de archivo `LICENSE`.

**Recotejo del hallazgo de `docs/stack-tecnologico.md` (03-ago-2026):** se repitió la verificación, ahora con lectura directa vía la API de GitHub en lugar de solo WebSearch:
- `https://api.github.com/repos/AGESIC-UY/cliente-java-plataforma-interoperabilidad/license` → **404 Not Found**.
- Se amplió el recotejo al repositorio hermano `AGESIC-UY/pdi-core` (el núcleo de la plataforma, no solo el cliente Java), con el mismo resultado: `https://api.github.com/repos/AGESIC-UY/pdi-core` devuelve `"license": null`, y `https://api.github.com/repos/AGESIC-UY/pdi-core/license` responde **404 Not Found**.
- Conclusión: se confirma el hallazgo negativo ya documentado en `docs/stack-tecnologico.md` — ni el cliente Java ni el núcleo de la PDI de AGESIC declaran licencia verificable. No se fuerza esta cita.

**Sustitución propuesta — X-Road (`nordic-institute/X-Road`):** dado que la fuente originalmente señalada por el proyecto no pudo verificarse, se buscó una alternativa que sí pudiera verificarse con el mismo rigor, cumpliendo el mismo propósito funcional (capa de intercambio de datos/interoperabilidad entre organismos públicos). X-Road es la capa de intercambio de datos ("data exchange layer") desarrollada originalmente en Estonia y hoy mantenida por el Nordic Institute for Interoperability Solutions (NIIS, consorcio interestatal Estonia-Finlandia), en producción real en varios países (Estonia, Finlandia, Islas Feroe, Islandia) como infraestructura nacional de interoperabilidad — el mismo tipo de rol que cumple la PDI de AGESIC en Uruguay, aunque son implementaciones distintas y no intercambiables en producción.

**Verificación de licencia (03-ago-2026):** lectura directa de `https://raw.githubusercontent.com/nordic-institute/X-Road/develop/LICENSE` — encabezado "The MIT License. Copyright (c) 2019- Nordic Institute for Interoperability Solutions (NIIS)...". Nótese que el campo automático `license.key` de la API de GitHub devuelve `"other"` para este repositorio (el detector no reconoce el encabezado de copyright no estándar), por lo que de nuevo se prioriza la lectura directa del archivo — mismo patrón ya visto en Mayan EDMS y en pgcrypto.

**Evidencia de actividad (03-ago-2026):** `https://api.github.com/repos/nordic-institute/X-Road` — `pushed_at: 2026-08-03` (mismo día de esta verificación), 826 estrellas, 43 issues abiertos. Repositorio de desarrollo activo con `X-Road-development` (repositorio satélite de gobernanza del proceso de desarrollo) y `X-Road-tests` (repositorio satélite de pruebas), señal de un proceso de mantenimiento organizado y no ad-hoc.

**Advertencia honesta sobre el alcance de esta sustitución:** X-Road no es la plataforma que Uruguay usa en producción (Uruguay usa la PDI propia de AGESIC, sin licencia verificable) ni sustituye la obligación legal de un municipio uruguayo de integrarse con la PDI real conforme a los arts. 157-160 de la Ley 18.719. Esta entrada del catálogo resuelve el requisito de F4 ("componente OSS recomendado, con licencia y actividad verificadas") para la categoría genérica `conector_interoperabilidad`; no reemplaza la integración legalmente exigida con la PDI de Agesic en Uruguay, que sigue siendo obligatoria independientemente de qué software se recomiende en este catálogo. Se deja esta distinción explícita también en el campo `nota` del YAML de datos.

**Conclusión:** verificado (componente sustituido respecto a lo sugerido en `docs/stack-tecnologico.md`, con la sustitución declarada y justificada). MIT sin ambigüedad, actividad confirmada el mismo día de la verificación.

---

## 6. `adaptador_pasarela_pago` — adaptador de pago en línea

**Regla de origen:** `motor_pagos.yaml`, `paso_tecnico`: "Adaptador de pago en línea configurable — nunca una pasarela única fija" — la propia regla exige explícitamente un patrón de adaptador sobre múltiples proveedores, no un procesador de pagos específico, coherente con el hallazgo ya documentado en `entregables/fase-2/verificacion-motor-pagos.md` de que ni México ni Uruguay tienen una pasarela de pagos estatal única obligatoria.

**Candidatos investigados:**
- **Omnipay** (`thephpleague/omnipay`) — librería de PHP con patrón de adaptador multi-pasarela, MIT (`https://api.github.com/repos/thephpleague/omnipay` → `license.key: "mit"`, confirmado). Actividad: `pushed_at: 2026-07-10`, pero el paquete meta `omnipay/omnipay` no tiene un release etiquetado desde 2021 (`v3.2.1`, 2021-06-05); el paquete núcleo real (`omnipay/omnipay-common`, del que dependen todos los adaptadores) sí tiene releases recientes (`v3.5.1`, 2026-02-13). Se descarta en favor de una alternativa más alineada al ecosistema Python del backend de DiagMuni, aunque la licencia y actividad de `omnipay-common` en sí son sólidas.
- **django-payments** (`jazzband/django-payments`) — elegido. Librería Python/Django con el mismo patrón de adaptador multi-proveedor de pago (Stripe, PayPal, Authorize.Net, y proveedores comunitarios adicionales), mantenida bajo Jazzband (cooperativa de mantenimiento colectivo de paquetes Python que evita el riesgo de abandono de un solo mantenedor individual).

**Verificación de licencia (03-ago-2026):** lectura directa de `https://raw.githubusercontent.com/jazzband/django-payments/main/LICENSE` — texto de licencia permisiva de 3 cláusulas (atribución de copyright, disclaimer de garantía, prohibición de usar el nombre del proyecto/mantenedores para promoción sin permiso expreso) — BSD-3-Clause. El campo automático `license.key` de la API de GitHub devuelve `"other"` (mismo patrón de no reconocimiento automático ya visto en Mayan EDMS, pgcrypto y X-Road); se prioriza la lectura directa del texto, que corresponde exactamente a la plantilla estándar de BSD de 3 cláusulas.

**Evidencia de actividad (03-ago-2026):** `https://api.github.com/repos/jazzband/django-payments` — `pushed_at: 2026-07-27`, 89 issues abiertos. Se revisaron los tags del repositorio (`https://api.github.com/repos/jazzband/django-payments/tags`): existe el tag `v4.0.0`, más reciente que el último release formal etiquetado en la página de Releases (`0.14.0`, 2021-02-01) — se confirmó vía pull requests recientemente fusionados (`https://api.github.com/repos/jazzband/django-payments/pulls?state=closed`) que el PR "Prepare changelog for v4.0.0" se fusionó el 2026-06-20, y PRs posteriores de mantenimiento (ej. soporte de Django 6, corrección de build de documentación) se fusionaron hasta el 2026-07-08. Es decir: el proyecto está en desarrollo activo con una versión mayor (v4.0.0) recién preparada, aunque la página de "Releases" de GitHub no refleja todavía ese tag como release formal — se documenta esta discrepancia con honestidad en vez de citar el número de release desactualizado (`0.14.0`) como si fuera el estado actual del proyecto.

**Advertencia sobre ajuste de ecosistema:** django-payments es una librería del framework Django, no de FastAPI (el framework backend de DiagMuni fijado en `docs/stack-tecnologico.md`). Esto no descalifica la recomendación porque F4 recomienda componentes para el sistema de trámites de la propia intendencia (que puede o no estar en Django), no para el backend de DiagMuni — se documenta este matiz explícitamente en el campo `nota` del YAML de datos para que quien lea el catálogo no asuma que se está proponiendo una dependencia de DiagMuni.

**Conclusión:** verificado. BSD-3-Clause sin ambigüedad, actividad de desarrollo confirmada (aunque con la discrepancia declarada entre el tag más reciente y el release formal más reciente).

---

## 7. Resumen para el YAML

| Categoría | Componente | Licencia | Estado |
|---|---|---|---|
| `modulo_cifrado_datos` | pgcrypto | BSD-style permisiva | Verificado |
| `gestor_expediente_electronico` | Mayan EDMS | Apache-2.0 | Verificado |
| `modulo_firma_electronica` | DSS (esig/dss) | LGPL-2.1 (servicio separado, no linkeado) | Verificado |
| `identidad_federada` | Keycloak | Apache-2.0 | Verificado |
| `conector_interoperabilidad` | X-Road | MIT | Verificado (sustituye al Cliente PDI de AGESIC, sin licencia verificable) |
| `adaptador_pasarela_pago` | django-payments | BSD-3-Clause | Verificado |

6 de 6 categorías cerradas con componente verificado; 0 huecos `[NO VERIFICADO]`. Ninguna licencia ni cifra de actividad se citó sin cotejo directo contra la fuente primaria (archivo `LICENSE` en la rama por defecto del repositorio oficial, o metadatos de la API de GitHub del repositorio oficial).
