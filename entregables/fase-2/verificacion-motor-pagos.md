# Verificación de citas normativas — `motor_pagos.yaml`

Verificación de dos citas marcadas `[NO VERIFICADO]` en `backend/app/engine/reglas/motor_pagos.yaml` (líneas 12 y 20). Fecha de la verificación: 3 de agosto de 2026. Método: búsqueda en línea contra fuentes oficiales/oficiales-adyacentes, y contraste contra los anexos base ya verificados del proyecto (`docs/anexo_legislacion_mx.md`, `docs/anexo_legislacion_uy.md`, corte 14-jul-2026).

---

## 1. México — `mx.fuente_normativa`

Cita original: `"LNETB art. 54-XI; CFDI — CFF art. 29 y LISR art. 86 5º párr. [NO VERIFICADO]"`.

### 1.1 LNETB art. 54-XI (no era el objeto de esta tarea, pero se recotejó)

`docs/anexo_legislacion_mx.md` §1 y §7 ya lo dan por **cotejado contra el PDF oficial** de Diputados: el art. 54 enumera los campos mínimos que todo trámite debe tener registrado en el Portal Ciudadano Único, y la fracción XI es "monto de derechos o aprovechamientos y alternativas para realizar el pago". Esto sustenta directamente el `paso_administrativo` de la regla ("Publicar alternativas de pago en el Portal Ciudadano Único"). No se encontró nada en la verificación que lo contradiga.

**Conclusión: verificada, tal cual estaba.**

### 1.2 CFF art. 29

Búsqueda directa en línea (03-ago-2026) contra fuentes que citan el texto vigente del Código Fiscal de la Federación (incluye referencia a `diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf` y compendios fiscales 2026 como sdv.com.mx). Texto relevante (paráfrasis fiel de fuente): "cuando las leyes fiscales establezcan la obligación de expedir comprobantes fiscales por los actos o actividades que realicen, por los ingresos que se perciban o por las retenciones de contribuciones que efectúen, los contribuyentes deberán emitirlos mediante documentos digitales a través de la página de Internet del SAT", cumpliendo los requisitos del art. 29-A.

Es la norma general que sustenta la obligación de emitir CFDI (Comprobante Fiscal Digital por Internet). No regula específicamente a los municipios, pero es el fundamento genérico correcto para "obligación de expedir comprobantes fiscales digitales" — coincide con lo que la regla afirma.

**Conclusión: verificada.** (Nota: existe una reforma en trámite/reciente al art. 29-A, fracción IX, con efectos desde el 1-ene-2026, sobre materialidad de operaciones — no afecta el fundamento aquí citado, que es la obligación general de expedición del art. 29, no la fracción nueva de 29-A.)

### 1.3 LISR art. 86, 5º párrafo

Este era el punto central de la tarea: el brief advertía que el art. 86 del Título III de la LISR ("Del Régimen de las Personas Morales con Fines no Lucrativos") tradicionalmente regula obligaciones de asociaciones/entidades no lucrativas privadas, no necesariamente de los municipios — y que había que confirmar si el fundamento correcto para "el municipio debe emitir CFDI por lo que cobra" es realmente el art. 86 o algún otro.

**Verificación del mecanismo completo (dos artículos, no solo uno):**

- **LISR art. 79, fracción XXIII** (verificado contra `sat.gob.mx/articulo/23073/articulo-79` y comentarios de vLex/SAT): clasifica expresamente a "la Federación, las Entidades Federativas, los Municipios y las instituciones que por Ley estén obligadas a entregar al Gobierno Federal el importe íntegro de su remanente de operación" como personas morales con fines no lucrativos del Título III. Es decir: los municipios **sí** están dentro del régimen de este Título, con un tratamiento distinto al genérico art. 81 (que exime a estos entes del ISR salvo enajenación de bienes/intereses/premios).
- **LISR art. 86, quinto párrafo** (verificado, con concordancia entre al menos tres fuentes independientes: materiales oficiales de capacitación fiscal gubernamental estatal — `caceg.guanajuato.gob.mx`, `egobierno2.aguascalientes.gob.mx` —, compendios fiscales especializados — sdv.com.mx, vigente sin reformas posteriores al 01-abr-2024, verificado 2026 —, y guías de llenado de CFDI del propio SAT para "CFDI emitidos por la Federación, Entidades Federativas..." en `sat.gob.mx/minisitio/Factura/documentos/Guia_llenadoCFDI_DPA.pdf`): estos entes (Federación, entidades federativas, municipios, instituciones obligadas a entregar remanente) tienen la obligación específica de **expedir comprobantes fiscales digitales por las contribuciones, productos y aprovechamientos que cobren**, así como por los apoyos o estímulos que otorguen, y de exigir comprobante fiscal a terceros cuando les hagan pagos sujetos a esa obligación.

Esto es exactamente el fundamento que la regla necesita: si un trámite municipal cobra un derecho o aprovechamiento, el municipio (como ente del art. 79-XXIII) está obligado por el art. 86, 5º párr., a expedir CFDI por ese cobro.

**Advertencia epistémica honesta:** no se logró leer el texto literal del PDF oficial de la LISR (`diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf`) párrafo por párrafo por búsqueda en línea — este método solo devuelve resúmenes/fragmentos de terceros, no el PDF completo. La verificación se basa en la **concordancia de múltiples fuentes oficiales o oficiales-adyacentes independientes** (SAT, gobiernos estatales, compendios fiscales fechados 2026 sin reformas posteriores reportadas), no en lectura directa del articulado. Este es el mismo nivel de rigor que ya declara `docs/anexo_legislacion_mx.md` §8 para esta misma cita ("verificado solo en fuentes secundarias... no en el PDF de la LISR, cotejar antes de citar textualmente") — con el añadido de que esta verificación sí confirmó el mecanismo completo (art. 79-XXIII + art. 86 5º párr., no solo el número de párrafo aislado) y confirmó que no hay indicio de renumeración reciente.

**Conclusión: verificada con nivel de confianza alto (concordancia de fuentes oficiales/gubernamentales secundarias), sin cotejo literal del PDF de LeyesBiblio.** No se encontró ningún artículo distinto que sea el fundamento más correcto — el par 79-XXIII/86-5º párr. es preciso y jurídicamente coherente con la afirmación de la regla.

**Fuentes consultadas (03-ago-2026):**
- https://www.sat.gob.mx/articulo/23073/articulo-79
- https://www.sat.gob.mx/minisitio/Factura/documentos/Guia_llenadoCFDI_DPA.pdf
- https://caceg.guanajuato.gob.mx/sites/default/files/training/C_FISCALES_GUBERNAMENTALES_.pdf
- https://egobierno2.aguascalientes.gob.mx/Servicios/SAC/SAC_Archivo/35%2012Agto2022%20Material%20Obligaciones%20Fiscales%20Gubernamentales%202022...pdf
- https://sdv.com.mx/compendio/ley-isr/articulo-86/
- https://contadormx.com/cfdi-derechos-productos-aprovechamientos-dpas-dependencias-gobierno/
- https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf (art. 29, referencia de contexto)
- https://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf (no se pudo leer el texto íntegro por búsqueda en línea; referencia de ubicación oficial de la ley)

---

## 2. Uruguay — `uy.fuente_normativa`

Cita original: `"Estándar Agesic para pasarelas de pago + soluciones propias por intendencia; ausencia de pasarela estatal única [NO VERIFICADO — hallazgo negativo]"`.

Es un hallazgo negativo: no existe pasarela de pagos estatal única y obligatoria en Uruguay. `docs/anexo_legislacion_uy.md` §6 ya trae este hallazgo trabajado con detalle ("no se confirmó la existencia de una pasarela de pagos estatal única y obligatoria tipo 'ePagos' [NO CONFIRMADO / hallazgo negativo relevante]"), con documentos Agesic nombrados explícitamente. Esta verificación amplió y confirmó esa base.

**Documentos oficiales identificados y confirmados por búsqueda en línea (03-ago-2026), todos publicados por Agesic (Agencia de Gobierno Electrónico y Sociedad de la Información y del Conocimiento) en su Centro de Recursos / gub.uy:**

1. **"Pagos en Línea en Trámites y Servicios del Estado — Pasarelas de Pago: Requisitos"** (PDF, `centroderecursos.agesic.gub.uy` y espejado en `gub.uy`): documento técnico que fija los requisitos que debe cumplir una pasarela de pagos para integrarse a los trámites en línea del Estado. Es un **estándar técnico (soft law)**, no una ley ni un decreto — no tiene rango normativo vinculante para las intendencias (que solo adoptan a través de convenio, conforme a la nota estructural del anexo, art. 262 CPEUM/CN uruguaya: los decretos de la Administración Central no alcanzan a los Gobiernos Departamentales).
2. **"Guía para disponibilizar Pagos en Línea"** (Agesic, gub.uy): guía operativa complementaria, mismo estatus (técnica, no legal).
3. **Wiki "Arquitectura para Trámites — Pasarela de Pagos"** (`centroderecursos.agesic.gub.uy`, wiki de Arquitectura de Gobierno): describe el flujo técnico genérico (token, redirección, conciliación) sin imponer un proveedor único.
4. **Convenio Agesic–RENEFISA (República Negocios Fiduciarios S.A.)**, firmado 09-dic-2014: acuerdo de cooperación interinstitucional para coordinar medios de pago en línea mediante un fideicomiso de administración. Es relevante porque podría sugerir un mecanismo centralizado — pero, tras revisar su objeto, es un **mecanismo de adhesión voluntaria adicional** (mismo patrón que el resto del ecosistema Agesic frente a organismos y, por extensión, a intendencias vía convenio), no una pasarela única obligatoria. No contradice el hallazgo negativo; lo matiza con un dato adicional (existe además esta vía de fideicomiso, opcional).
5. **Redes de cobranza habilitadas** (Abitab, Redpagos, Correo): confirmado como mecanismo de pago presencial/mixto complementario, no una pasarela digital única.
6. **Soluciones propias por intendencia**: confirmado que Montevideo, Paysandú y Treinta y Tres (entre otras) operan sus propios sistemas de pago en línea, integrados de forma independiente con bancos y redes — consistente con "no existe pasarela estatal única".

**No se encontró** ninguna ley ni decreto que imponga una pasarela de pagos estatal única y obligatoria para trámites (se buscó explícitamente "pasarela de pagos del Estado", "Red de Cobranza [uy]", Ley 19.355 arts. 73-76, Ley 18.719/PDI — ninguna de estas normas menciona una pasarela de pagos específica; regulan derecho al canal electrónico, publicación de trámites e interoperabilidad, no medios de pago).

**Conclusión: hallazgo negativo confirmado, con fuente documental citable (documentos técnicos oficiales de Agesic, sin rango normativo).** Se corrige el formato de la cita para dejar de simular una cita de ley: pasa a nombrar los documentos técnicos exactos de Agesic y a declarar explícitamente que la ausencia de pasarela única es una constatación empírica sin fundamento legal (no hay ley/decreto que la imponga ni que la prohíba — simplemente no existe, y cada intendencia resuelve por su cuenta).

**Fuentes consultadas (03-ago-2026):**
- https://centroderecursos.agesic.gub.uy/documents/portlet_file_entry/31472/Pasarela+de+Pagos.+Requisitos+-+Pagos+en+Línea+en+Trámites+y+Servicios+del+Estado.pdf/dac65650-d988-e7d4-2e07-1ca7bf18a781?status=0&download=true
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/comunicacion/publicaciones/guia-para-disponibilizar-pagos-linea
- https://centroderecursos.agesic.gub.uy/web/arquitectura-de-gobierno/arquitectura-para-tramites/-/wiki/Arquitectura+para+Tr%C3%A1mites/Pasarela+de+pagos
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/politicas-y-gestion/convenios/republica-negocios-fiduciarios-sa-renefisa-agesic
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/sites/agencia-gobierno-electronico-sociedad-informacion-conocimiento/files/documentos/convenios/Acuerdo_Esp_RENEFISA_AGESIC.pdf
- https://www.gub.uy/tramites/red-cobros-pagos-pagos-sector-publico
- `docs/anexo_legislacion_uy.md` §6 (fuente base ya verificada del proyecto, corte 14-jul-2026)

---

## 3. Resumen de conclusiones para el YAML

| Cita | Estado final | Cambio en `motor_pagos.yaml` |
|---|---|---|
| MX — LNETB art. 54-XI | Verificada (ya lo estaba) | Se mantiene, sin marcador |
| MX — CFF art. 29 | Verificada | Se mantiene, sin marcador |
| MX — LISR art. 86, 5º párr. | Verificada (concordancia de fuentes oficiales secundarias; sin cotejo literal del PDF) | Se retira `[NO VERIFICADO]`; se deja nota breve de nivel de verificación |
| UY — ausencia de pasarela estatal única | Hallazgo negativo confirmado, con documentos Agesic citables (sin rango normativo) | Se retira `[NO VERIFICADO]`; se reemplaza "Estándar Agesic" genérico por los dos documentos exactos + aclaración de que es constatación operativa, no obligación legal |

Ninguna cita quedó sin verificar; ninguna se inventó. El nivel de verificación de LISR art. 86 es "alta confianza por concordancia de fuentes secundarias oficiales", no "cotejo literal del texto legal" — se declara así explícitamente, tanto aquí como en el propio YAML, en vez de presentarlo como verificación absoluta.
