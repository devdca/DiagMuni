# Modelo de diagnóstico — catálogo brecha→acción

Versión 1 · 21 de julio de 2026
Primer borrador del catálogo de reglas brecha→acción (formato acordado en `docs/TRD.md`). Cubre las 6 variables de diagnóstico por trámite × 2 países = 12 entradas — catálogo finito por diseño, no un proyecto abierto. Fuente de cada ancla normativa: entregables/fase-1/matriz-normativa.md (aprobada 22-jul-2026) y, directamente, anexo_legislacion_mx.md/anexo_legislacion_uy.md. La mayoría de las anclas ya están verificadas contra fuente oficial; las marcas [NO VERIFICADO] que permanecen en celdas específicas señalan huecos puntuales aún pendientes (ver lista en 'Pendiente'), no la totalidad del catálogo. Este documento es el borrador humano-legible; en fase C del plan de implementación se transcribe mecánicamente a los archivos YAML de `backend/app/engine/reglas/`.

## Índice de madurez — niveles (referencia)

0 Presencial en papel · 1 Informativo · 2 Transaccional parcial · 3 Transaccional completo · 4 Proactivo e interoperable — nomenclatura definida en este catálogo (`docs/PRD.md` y `docs/backend-schema.md` solo fijan el rango numérico `indice_madurez` 0-4; pendiente sincronizar estos 5 nombres de nivel en el glosario de `docs/PRD.md`).

## Catálogo

### 1. Documentos requeridos — papel vs. digital

| Campo | México | Uruguay |
|---|---|---|
| Criterio de detección | `documentos_digitalizados == false` | `documentos_digitalizados == false` |
| Paso administrativo | Iniciar gestión documental electrónica del expediente conforme a la Ley General de Archivos | Adoptar expediente electrónico conforme a la Ley 16.736 |
| Paso técnico | Digitalizar el expediente y adoptar un gestor de expediente electrónico (categoría, no marca — candidato específico pendiente en catálogo OSS) | Igual |
| Paso organizacional | Capacitar al personal de archivo/mostrador en captura y resguardo digital | Igual |
| Prerrequisitos | Definir política de resguardo/retención documental | Igual |
| Por qué importa | Bloquea el paso de índice 0 a 1 como mínimo; prerrequisito de cualquier transaccionalidad completa | Igual |
| Fuente normativa | LNETB arts. 76-78, Expediente Digital Ciudadano — prohibición de exigir documentos ya en el expediente (verificado) + Ley General de Archivos arts. 41-49, 62 (verificado — ver anexo_legislacion_mx.md §1-2 y entregables/fase-1/matriz-normativa.md) | Ley 16.736 arts. 694-696 (verificado; el art. 697 fue derogado por el art. 28 de la Ley 18.600) + Ley 19.355 art. 76 (verificado) |
| Categoría de catálogo | `gestor_expediente_electronico` | `gestor_expediente_electronico` |

### 2. Motor de pagos

| Campo | México | Uruguay |
|---|---|---|
| Criterio de detección | `motor_pagos == false` | `motor_pagos == false` |
| Paso administrativo | Publicar alternativas de pago en el Portal Ciudadano Único; evaluar obligación de CFDI si el trámite genera cobro | Evaluar solución de pago propia de la intendencia (sin pasarela estatal única) alineada al estándar Agesic |
| Paso técnico | Adaptador de pago en línea configurable — nunca una pasarela única fija | Igual |
| Paso organizacional | Capacitar a caja/tesorería en conciliación de pagos en línea | Igual |
| Prerrequisitos | Cuenta bancaria institucional habilitada para cobros electrónicos | Igual |
| Por qué importa | Bloquea el paso a índice 3 (transaccional completo) | Igual |
| Fuente normativa | LNETB art. 54-XI (verificado); CFDI — CFF art. 29 (verificado) y mecanismo de dos piezas de la LISR (art. 79-XXIII + art. 86, 5º párr.) `[VERIFICADO — confianza alta por concordancia de fuentes oficiales/oficiales-adyacentes independientes, sin cotejo literal del PDF de LeyesBiblio; ver entregables/fase-2/verificacion-motor-pagos.md §1.3]` | Estándar Agesic para pasarelas de pago + soluciones propias por intendencia (verificado); ausencia de pasarela estatal única `[NO VERIFICADO — hallazgo negativo, ver anexo_legislacion_uy.md §6]` |
| Categoría de catálogo | `adaptador_pasarela_pago` | `adaptador_pasarela_pago` |

### 3. Firma electrónica

| Campo | México | Uruguay |
|---|---|---|
| Criterio de detección | `firma_electronica_habilitada == false` | `firma_electronica_habilitada == false` |
| Paso administrativo | Suscribir convenio de homologación con la e.firma del SAT + ley estatal aplicable | Acogerse a la habilitación del art. 8 de la Ley 18.600 |
| Paso técnico | Integrar verificación de firma con estándar abierto (PAdES/XAdES) | Igual; considerar custodia centralizada (Ley 19.535) |
| Paso organizacional | Capacitar a funcionarios de mostrador en uso del certificado y verificación de firmas | Igual |
| Prerrequisitos | Conectividad estable | Igual |
| Por qué importa | Bloquea el paso de índice 2 a 3 | Igual |
| Fuente normativa | LNETB art. 25-III (verificado) + LFEA y su Reglamento, régimen de homologación de e.firma SAT (verificado objeto y régimen); ley estatal de firma electrónica aplicable `[NO VERIFICADO — depende de la entidad federativa del municipio evaluado]` | Ley 18.600 art. 8 + arts. 31-33 (agregados por art. 28 de la Ley 19.535), custodia centralizada (verificado); contenido detallado del Decreto 71/025 `[NO VERIFICADO]` |
| Categoría de catálogo | `modulo_firma_electronica` | `modulo_firma_electronica` |

### 4. Interoperabilidad con otros registros

| Campo | México | Uruguay |
|---|---|---|
| Criterio de detección | `interoperabilidad == false` | `interoperabilidad == false` |
| Paso administrativo | Habilitar el intercambio de datos del trámite conforme al Expediente Digital Ciudadano (LNETB arts. 76-84) y a las obligaciones generales de plataformas digitales y validez de documentos electrónicos (LNETB art. 16, fracs. III, IV, VII, XI) | Integrar con la Plataforma de Interoperabilidad (PDI) de AGESIC |
| Paso técnico | Conector de interoperabilidad nacional (categoría) | Cliente PDI de AGESIC (ya en catálogo OSS, `docs/stack-tecnologico.md`) |
| Paso organizacional | Designar enlace técnico responsable del intercambio de datos | Igual |
| Prerrequisitos | Trámite ya digitalizado (depende de la brecha 1) | Igual |
| Por qué importa | Requisito de índice 4 (proactivo e interoperable) | Igual |
| Fuente normativa | LNETB art. 16 (fracs. III, IV, VII, XI) + arts. 76-84, Expediente Digital Ciudadano (verificado, ver anexo_legislacion_mx.md §1 y entregables/fase-1/matriz-normativa.md) — Llave MX/arts. 64-75 excluida de esta fila (variable Identidad); aporte de código al Repositorio Nacional de Tecnología Pública (art. 16-VIII) excluido de esta fila (variable Base para adoptar OSS) | Ley 18.719 arts. 157-160 (verificado) — cliente Java de la PDI publicado como OSS (verificado) |
| Categoría de catálogo | `conector_interoperabilidad` | `conector_interoperabilidad` (cliente PDI ya identificado, no genérico) |

### 5. Datos personales tratados

| Campo | México | Uruguay |
|---|---|---|
| Criterio de detección | `proteccion_datos_incompleta == true` (México: ausencia de aviso de privacidad conforme a LGPDPPSO arts. 20-22) | `proteccion_datos_incompleta == true` (Uruguay: ausencia de delegado de protección de datos conforme a Ley 19.670 arts. 37-40) |
| Paso administrativo | Publicar aviso de privacidad conforme a la LGPDPPSO; identificar responsable ante la Secretaría Anticorrupción y Buen Gobierno | Designar delegado de protección de datos conforme a la Ley 18.331 + 19.670 |
| Paso técnico | Cifrado en tránsito/reposo de los datos personales capturados (estándar, no marca) | Igual |
| Paso organizacional | Capacitar al personal en tratamiento de datos personales | Igual |
| Prerrequisitos | Inventario de datos personales tratados por trámite | Igual |
| Por qué importa | Obligación legal transversal — no bloquea un nivel específico del índice, pero es requisito de cumplimiento en cualquier nivel ≥ 1 | Igual |
| Fuente normativa | LGPDPPSO arts. 20-22 (aviso de privacidad) y 25-28 (medidas de seguridad); autoridad: Secretaría Anticorrupción y Buen Gobierno, art. 3-XXVI (verificado) | Ley 18.331 + Ley 19.670 arts. 37-40, delegado de protección de datos obligatorio (verificado) |
| Categoría de catálogo | `modulo_cifrado_datos` | `modulo_cifrado_datos` |

### 6. Identidad / acceso ciudadano

| Campo | México | Uruguay |
|---|---|---|
| Criterio de detección | `mecanismo_identidad == "ninguno"` | `mecanismo_identidad == "ninguno"` |
| Paso administrativo | Evaluar adopción de Llave MX como acceso único | Evaluar adopción de ID Uruguay (Agesic) |
| Paso técnico | Integración con proveedor de identidad federada nacional (categoría) | Igual |
| Paso organizacional | Informar al ciudadano el nuevo mecanismo de acceso al trámite | Igual |
| Prerrequisitos | Trámite con canal digital habilitado | Igual |
| Por qué importa | Refuerza el paso a índice 3-4; mejora la trazabilidad de usos exigida por LNETB art. 15 | Reduce la fricción de registro del ciudadano al reutilizar una credencial de identidad digital con equivalencia funcional a la identificación presencial (art. 33 Ley 18.600 y Decreto 70/018), ya exigida operativamente por la Intendencia de Montevideo para su portal de facturas (anexo_legislacion_uy.md §6) |
| Fuente normativa | Llave MX — LNETB arts. 64-75 (verificado) | ID Uruguay/usuario gub.uy — art. 33 Ley 18.600 + Decreto 70/018 (verificado existencia y operación; cifras de usuarios `[NO VERIFICADO]`) |
| Categoría de catálogo | `identidad_federada` | `identidad_federada` |

## Nota sobre costo/tiempo

Deliberadamente ausente de esta tabla — corresponde a una capa de costeo paramétrica separada (por país/moneda, con fuente y fecha), nunca mezclada con el contenido normativo/técnico de arriba (estable vs. volátil, ver `docs/TRD.md`).

## Pendiente

- Verificar las citas puntuales que aún quedan marcadas [NO VERIFICADO] (CFDI/CFF-LISR, ley estatal de firma-e específica del municipio evaluado, contenido detallado del Decreto 71/025, ausencia de pasarela de pagos única en Uruguay, cifras de usuarios de ID Uruguay) — el resto del catálogo ya está respaldado por anexo_legislacion_mx.md/anexo_legislacion_uy.md y por la matriz normativa aprobada.
- Agregar la capa de costeo paramétrico por entrada.
- Al iniciar la fase C del plan de implementación, transcribir mecánicamente cada fila a su archivo YAML correspondiente en `backend/app/engine/reglas/`.
