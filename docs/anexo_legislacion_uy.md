# Anexo: Marco jurídico uruguayo de digitalización de trámites en gobiernos departamentales y municipios

**Propósito:** base normativa para el diseño del software open source de diagnóstico de modernización municipal (postulación GovTech Connect — BID Lab / Red de Innovación Local, piloto en ciudades CIIAR Uruguay).
**Fecha de corte de la investigación:** 14 de julio de 2026. Fuentes primarias: IMPO (impo.com.uy), gub.uy/Agesic, Parlamento.
**Convención:** cada afirmación se marca como **[VERIFICADO]** (texto legal cotejado en IMPO o página oficial gub.uy) o **[NO CONFIRMADO]** (dato plausible de fuente secundaria o que no pudo cotejarse en fuente oficial).

**Nota estructural clave para todo el anexo [VERIFICADO en cuanto a su base constitucional]:** en Uruguay los Gobiernos Departamentales (19 intendencias) gozan de autonomía consagrada en los artículos 262 y 297 de la Constitución. Por eso, las **leyes** nacionales (18.600, 18.331, 19.179, 19.355 en sus artículos de alcance general) sí alcanzan a intendencias y municipios, mientras que los **decretos del Poder Ejecutivo** (184/015, 276/013, etc.) solo obligan a la Administración Central; a las intendencias llegan por **adhesión voluntaria mediante convenios con Agesic**. Este es el dato de diseño más importante para el software: la digitalización municipal uruguaya es jurídicamente *habilitada* por ley, pero operativamente *voluntaria y convenial*.

---

## 1. Agesic: rectoría del gobierno digital y su alcance territorial

La Agencia de Gobierno Electrónico y Sociedad de la Información y del Conocimiento (Agesic) fue creada por el **artículo 72 de la Ley N° 17.930** (Presupuesto Nacional, 19 de diciembre de 2005) como agencia con autonomía técnica dependiente de Presidencia de la República **[VERIFICADO]**. Su denominación y cometidos fueron ampliados por la Ley N° 18.046 (2006, arts. 54-55), la Ley N° 18.172 (2007, arts. 118-121) y la Ley N° 18.362 (2008, arts. 70-80), que la puso en pleno funcionamiento **[VERIFICADO en fuente oficial de Presidencia]**.

El **Decreto N° 184/015** (14 de julio de 2015) consolida su misión y cometidos. Su artículo 1 le asigna, entre otros: formular la política y estrategia nacional de gobierno electrónico; **asistir y asesorar a las "Entidades Públicas, estatales y no estatales"** en planes de gobierno electrónico (literal c); dictar normas técnicas TIC para las entidades públicas (literal f); y desarrollar planes de trámites y servicios en línea e interoperabilidad (literal h) **[VERIFICADO, texto cotejado en IMPO]**. Sin embargo, el artículo 3 del mismo decreto acota el poder vinculante: las normas técnicas y regulaciones de la iniciativa "Trámites 100% en línea" son "de observancia obligatoria **para toda la Administración Central**" — no para los Gobiernos Departamentales **[VERIFICADO]**.

**Conclusión sobre la rectoría:** Agesic es rectora plena sobre la Administración Central; frente a intendencias y municipios actúa como **asesora y proveedora de plataformas por convenio**. Existe un **Convenio Marco de Cooperación Interinstitucional Agesic–Congreso de Intendentes** (firmado en 2013 y renovado/ampliado después), bajo el cual Agesic pone a disposición de las intendencias soluciones como plataforma de trámites en línea, gestión documental (expediente electrónico), portal institucional, datos abiertos y servicios de seguridad de la información **[VERIFICADO en páginas oficiales de Agesic y del Congreso de Intendentes; ejemplo concreto: segundo acuerdo específico Intendencia de Rivera–Agesic]**.

**Agenda digital vigente:** la **Agenda Uruguay Digital 2025** fue aprobada por **Decreto N° 134/021** (4 de mayo de 2021) y su revisión de medio término por **Decreto N° 285/024** (24 de octubre de 2024), con 12 objetivos y ~57 metas monitoreadas en el Mirador de Gobierno Abierto **[VERIFICADO]**. Complementa el **Plan de Gobierno Digital 2025** de Agesic. En el marco del presupuesto 2026-2030, Agesic elabora una **nueva estrategia de gobierno digital 2030**, que a la fecha de este anexo **no consta como aprobada por decreto** **[NO CONFIRMADO su estado de aprobación; verificar antes de citar en la postulación]**.

Fuentes:
- https://www.impo.com.uy/bases/leyes/17930-2005/72
- https://www.impo.com.uy/bases/decretos/184-2015
- https://www.gub.uy/presidencia/institucional/creacion-evolucion-historica
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/politicas-y-gestion/programas/agenda-digital-del-uruguay
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/politicas-y-gestion/plan-gobierno-digital-2025
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/politicas-y-gestion/convenios/congreso-intendentes-agesic-0
- https://www.rivera.gub.uy/portal/idr-firma-el-2-acuerdo-especifico-con-agesic/
- https://miradordegobiernoabierto.agesic.gub.uy/SigesVisualizador/gu/o/AUD2025

**Variable de diagnóstico derivada:** existencia de convenio vigente de la intendencia/municipio con Agesic y grado de adopción de sus plataformas (proxy de madurez institucional); alineación de los trámites locales con el catálogo y estándares de tramites.gub.uy.

---

## 2. Ley 19.355 (arts. 73-76) y Decreto 184/015: trámites en línea

La **Ley N° 19.355** (Presupuesto Nacional 2015-2019, promulgada el 19 de diciembre de 2015) contiene el núcleo legal del programa de trámites en línea. Textos cotejados artículo por artículo en IMPO **[VERIFICADO]**:

- **Art. 73:** crea en Agesic el Proyecto "Trámites en Línea", "con el objetivo de promover y desarrollar estrategias de simplificación, priorización y puesta en línea de trámites **en todas las entidades públicas**", asignando a Agesic su dirección, gestión y contralor.
- **Art. 74:** "Reconócese el **derecho de las personas a relacionarse con las entidades públicas por medios electrónicos**, sin exclusión de los medios tradicionales."
- **Art. 75:** obliga a las entidades públicas a constituir **domicilio electrónico** y **autoriza expresamente a los Gobiernos Departamentales** (junto al Poder Ejecutivo y organismos de los arts. 220 y 221 de la Constitución) a imponer a las personas la constitución de domicilio electrónico, previo asesoramiento de Agesic.
- **Art. 76:** obliga a las entidades públicas a **simplificar trámites**, a **no solicitar copias de documentación** obtenible por medios electrónicos ni información que ya posea otra entidad pública, y a **publicar cada trámite** con requisitos, costo total, plazo máximo y dependencia responsable, con revisión periódica fechada; prohíbe exigir requisitos adicionales a los publicados.

El **Decreto N° 184/015** creó la iniciativa **"Trámites 100% en línea"** (art. 2), cuyo objetivo es "impulsar la disponibilidad de los Trámites y Servicios de la Administración Central **y otras Entidades Públicas** por vía electrónica"; el art. 3 encomienda a Agesic dirigirla, con normas técnicas obligatorias **solo para la Administración Central** **[VERIFICADO]**. La meta de 100% de trámites de Administración Central iniciables en línea se alcanzó hacia 2020 según comunicaciones de Agesic **[NO CONFIRMADO el porcentaje exacto y la fecha en fuente primaria; usar con cautela]**.

**Alcance para intendencias:** los arts. 74-76 usan el término "entidades públicas" sin restricción, por lo que la doctrina y la práctica los consideran aplicables a los Gobiernos Departamentales (y el art. 75 los menciona expresamente); en cambio, la obligación operativa de poner el 100% de los trámites en línea con estándares Agesic solo es exigible a la Administración Central **[VERIFICADO el texto; la interpretación de alcance es análisis propio apoyado en el art. 75]**. Las intendencias que digitalizan trámites lo hacen vía convenio (sección 1) usando la plataforma de trámites en línea de Agesic o desarrollos propios (ej. tramites.montevideo.gub.uy).

Fuentes:
- https://www.impo.com.uy/bases/leyes-originales/19355-2015/73
- https://www.impo.com.uy/bases/leyes-originales/19355-2015/74
- https://www.impo.com.uy/bases/leyes-originales/19355-2015/75
- https://www.impo.com.uy/bases/leyes-originales/19355-2015/76
- https://www.impo.com.uy/bases/decretos/184-2015
- https://tramites.montevideo.gub.uy/

**Variables de diagnóstico derivadas:** (a) **trámites disponibles** y % iniciables/completables en línea (medida contra el estándar nacional "100% en línea"); (b) **publicación de requisitos, costos y plazos** por trámite (cumplimiento del art. 76); (c) **documentos en papel vs digital**: si el trámite exige copias o información que otra entidad pública ya posee, hay incumplimiento del art. 76 (indicador directo de rezago).

---

## 3. Ley 18.600: documento electrónico y firma electrónica

La **Ley N° 18.600** (21 de septiembre de 2009) reconoce la admisibilidad, validez y eficacia jurídica del documento electrónico y de la firma electrónica **[VERIFICADO, texto completo cotejado en IMPO]**. Puntos clave:

- **Art. 2 lit. K:** define la **firma electrónica avanzada (FEA)**: identificación unívoca del firmante, control exclusivo, verificable por terceros, vinculada al documento (detección de alteraciones) y basada en certificado reconocido válido.
- **Art. 4:** los documentos electrónicos satisfacen el requerimiento de escritura y tienen el mismo valor que los escritos.
- **Art. 6:** la FEA tiene **idéntica validez y eficacia que la firma autógrafa** en documento público o privado con firmas certificadas.
- **Art. 8 (clave municipal):** "El Estado, **los Gobiernos Departamentales**, los entes autónomos, los servicios descentralizados y, en general, todos los órganos del Estado **podrán** ejecutar o realizar actos, celebrar contratos y expedir cualquier documento, dentro de su ámbito de competencia, suscribiéndolos por medio de firma electrónica o firma electrónica avanzada." Es habilitación expresa (no obligación) para intendencias y, por extensión orgánica, para municipios.
- **Arts. 12-15:** crean la **Unidad de Certificación Electrónica (UCE)** como órgano desconcentrado de Agesic (regulador/acreditador) y designan a **Agesic como Autoridad Certificadora Raíz Nacional**.
- **Arts. 31-33 (agregados por el art. 28 de la Ley N° 19.535, de 25 de septiembre de 2017):** crean los **Prestadores de Servicios de Confianza**, la **FEA con custodia centralizada** (misma validez que la FEA clásica) y la **equivalencia funcional de la identificación digital** con la identificación presencial. Reglamentados por el **Decreto N° 70/018** (19 de marzo de 2018) y, más recientemente, por el **Decreto N° 71/025 (25 de febrero de 2025)** — esta es la actualización normativa más reciente del régimen **[VERIFICADO que el Decreto 71/025 reglamenta el art. 31, según las notas oficiales de IMPO; su contenido detallado no fue cotejado en el texto completo — NO CONFIRMADO en detalle]**.

Otros reglamentos: Decretos 436/011, 36/012 y 276/013. Sobre esta base operan **Firma.gub.uy** (firma con cédula de identidad electrónica) y los servicios de identidad/firma que Agesic ofrece a organismos **[VERIFICADO en publicaciones oficiales de Agesic]**.

Fuentes:
- https://www.impo.com.uy/bases/leyes/18600-2009
- https://www.impo.com.uy/bases/decretos/70-2018
- https://www.impo.com.uy/bases/decretos/71-2025 (referenciado desde IMPO)
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/comunicacion/publicaciones/documentacion-tecnica-firmagubuy/documentacion-tecnica-firmagubuy/firma

**Variable de diagnóstico derivada:** **uso de firma electrónica** — si los actos, resoluciones y constancias del municipio/intendencia se firman con FE o FEA (art. 8) o siguen exigiendo firma autógrafa; y si el gobierno local acepta identificación digital del ciudadano (art. 33) en lugar de comparecencia presencial.

---

## 4. Expediente electrónico: Ley 16.736 (arts. 694-697) y decretos

La **Ley N° 16.736** (Presupuesto, 5 de enero de 1996, arts. 694 a 697) es la norma fundacional: autorizó la sustanciación de actuaciones de la Administración Pública y el dictado de actos administrativos por **medios informáticos**, otorgando a la documentación emergente — cuando es redactada por funcionario competente, con las formas requeridas — el carácter de **instrumento público con plena fe** **[VERIFICADO en fuentes oficiales y doctrina; el art. 697 fue derogado por el art. 28 de la Ley 18.600]**. El **Decreto N° 65/998** reglamentó el expediente electrónico (validez del documento electrónico, firma, archivo) y el **Decreto N° 276/013** (3 de septiembre de 2013) reguló el **procedimiento administrativo electrónico** actualizado, reglamentando también la Ley 18.600 **[VERIFICADO existencia y objeto; articulado no cotejado íntegro]**.

**Alcance municipal:** la habilitación legal (Ley 16.736) alcanza a toda la Administración Pública; los decretos reglamentarios, en cambio, rigen para la Administración Central. Las intendencias adoptan expediente electrónico mediante sus propias normas departamentales o adhiriendo a la plataforma de **gestión documental (GDoc/expediente electrónico) que Agesic ofrece por convenio** a intendencias y al Congreso de Intendentes **[VERIFICADO que la solución se ofrece por convenio; el nivel de adopción por intendencia NO CONFIRMADO — es justamente lo que el diagnóstico debe medir]**.

Fuentes:
- https://www.impo.com.uy/bases/leyes/16736-1996
- https://www.impo.com.uy/bases/decretos-originales/65-1998
- https://www.impo.com.uy/bases/decretos/276-2013
- https://www.informatica-juridica.com/trabajos/normas-expediente-electronico-uruguay/

**Variables de diagnóstico derivadas:** (a) **documentos en papel vs digital** dentro del back-office (¿el expediente nace y circula electrónico o se imprime?); (b) **funcionarios involucrados por trámite** — el expediente electrónico permite trazar pases y actuaciones; su ausencia obliga a medirlo por relevamiento manual.

---

## 5. Protección de datos personales: Ley 18.331 y actualizaciones

La **Ley N° 18.331** (11 de agosto de 2008) consagra la protección de datos personales como derecho inherente a la persona y la acción de habeas data; **aplica a bases de datos públicas y privadas**, lo que incluye sin excepción a intendencias y municipios **[VERIFICADO]**. Crea la **Unidad Reguladora y de Control de Datos Personales (URCDP)** como órgano desconcentrado de Agesic. Uruguay cuenta con reconocimiento de adecuación por la Unión Europea **[VERIFICADO el hecho; la fecha de la última revalidación NO CONFIRMADA en fuente oficial durante esta investigación]**.

Actualización principal: **arts. 37 a 40 de la Ley N° 19.670** (Rendición de Cuentas, octubre de 2018, vigente desde enero de 2019), reglamentados por el **Decreto N° 64/020** (febrero de 2020) **[VERIFICADO]**. Introducen: (i) **notificación obligatoria de vulneraciones de seguridad** a la URCDP y a los titulares; (ii) **responsabilidad proactiva** (privacidad desde el diseño, evaluaciones de impacto); (iii) **delegado de protección de datos obligatorio para las entidades públicas** — incluidas intendencias — y privadas que traten datos masivos o sensibles; (iv) aplicación extraterritorial. No se identificaron modificaciones sustantivas posteriores específicas de esta ley en las Rendiciones de Cuentas 2023-2025 **[NO CONFIRMADO de forma exhaustiva; conviene una verificación puntual de la Ley 20.212 y siguientes antes de publicar]**.

Fuentes:
- https://www.impo.com.uy/bases/leyes/18331-2008
- https://www.gub.uy/unidad-reguladora-control-datos-personales/comunicacion/publicaciones/cambios-legislacion-sobre-proteccion-datos-personales
- https://www.guyer.com.uy/posts-&-news/informe-especial-modificaciones-en-materia-de-proteccion-de-datos-personales

**Variables de diagnóstico derivadas:** (a) existencia de **delegado de protección de datos** designado en la intendencia (obligación legal vigente, indicador binario de cumplimiento); (b) tratamiento de los datos de los **ciudadanos que demandan el servicio** (bases registradas, consentimiento, seguridad) — condición de diseño para el propio software de diagnóstico, que deberá minimizar datos personales.

---

## 6. Interoperabilidad, ID Uruguay y pagos en línea

**Interoperabilidad (fuerza de ley):** los **arts. 157 a 160 de la Ley N° 18.719** (Presupuesto, 27 de diciembre de 2010), reglamentados por el **Decreto N° 178/013**, obligan al **intercambio de información entre entidades públicas, estatales o no estatales**, canalizado por la **Plataforma de Interoperabilidad (PDI)** de la Plataforma de Gobierno Electrónico de Agesic; además obligan a expedir **constancias y certificados en versión digital firmados con FEA** **[VERIFICADO en IMPO/Decreto 178/013 y en el centro de conocimiento de Agesic]**. El cliente Java de la PDI está publicado como open source en GitHub (AGESIC-UY) **[VERIFICADO]** — antecedente útil para la propuesta OSS.

**Identidad digital (ID Uruguay / Usuario gub.uy):** plataforma de autenticación única del Estado operada por Agesic, con base jurídica en el art. 33 de la Ley 18.600 (equivalencia de la identificación digital) y el Decreto 70/018; más de 1,6 millones de personas registradas y acceso a cientos de servicios **[VERIFICADO su existencia y operación en fuentes oficiales; las cifras exactas de usuarios a 2026 NO CONFIRMADAS]**. La Intendencia de Montevideo ya exige "usuario gub.uy" para su portal de facturas, lo que demuestra la reutilización departamental **[VERIFICADO]**.

**Pagos:** **no se confirmó la existencia de una pasarela de pagos estatal única y obligatoria tipo "ePagos"** **[NO CONFIRMADO / hallazgo negativo relevante]**. Lo que existe y está verificado: (i) Agesic publica la **arquitectura de referencia y los requisitos que debe cumplir una pasarela de pagos** para integrarse a los trámites en línea del Estado ("Pagos en Línea en Trámites y Servicios del Estado — Pasarelas de Pago: requisitos", y la "Guía para disponibilizar Pagos en Línea"); (ii) los pagos al sector público se apoyan en **redes de cobranza habilitadas** (Abitab, Redpagos) y débitos/transferencias bancarias; (iii) las intendencias operan **soluciones propias de pago en línea** (Montevideo "Mi gestión de facturas", Paysandú, Treinta y Tres, etc.), integradas con bancos y redes **[VERIFICADO]**. Es decir: hay estándar técnico nacional y ecosistema, pero la adopción de un motor de pagos es decisión de cada intendencia.

Fuentes:
- https://www.impo.com.uy/bases/leyes/18719-2010
- https://www.impo.com.uy/bases/decretos/178-2013/17
- https://centrodeconocimiento.agesic.gub.uy/web/ccio/plataforma-de-interoperabilidad
- https://github.com/AGESIC-UY/cliente-java-plataforma-interoperabilidad
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/comunicacion/publicaciones/guia-para-disponibilizar-pagos-linea
- https://www.gub.uy/agencia-gobierno-electronico-sociedad-informacion-conocimiento/sites/agencia-gobierno-electronico-sociedad-informacion-conocimiento/files/documentos/publicaciones/Pagos_enLinea_PasarelaPagos.pdf
- https://www.gub.uy/tramites/red-cobros-pagos-pagos-sector-publico
- https://tramites.montevideo.gub.uy/ ; https://www.paysandu.gub.uy/tramites/pagos-en-linea/ ; https://treintaytres.gub.uy/pago-en-linea/

**Variables de diagnóstico derivadas:** (a) **existencia de motor de pagos** en línea del gobierno local y su conformidad con los requisitos Agesic; (b) uso de **ID Uruguay** como autenticación (vs. registros propios); (c) consumo de la **PDI** para no pedir documentos al ciudadano (conecta con la variable papel vs digital del art. 76 de la Ley 19.355).

---

## 7. Descentralización: Ley 19.272 y competencias sobre trámites locales

La **Ley N° 19.272** (Ley de Descentralización y Participación Ciudadana, 18 de septiembre de 2014) regula el **tercer nivel de gobierno: los Municipios** (arts. 262, 287 y disposición transitoria Y de la Constitución) **[VERIFICADO, texto completo cotejado en IMPO]**. Puntos relevantes para el diagnóstico:

- **Art. 1:** todo centro poblado de más de 2.000 habitantes constituye un Municipio.
- **Art. 6:** la **materia departamental** (intendencias) incluye la política de recursos financieros y humanos y los programas presupuestales municipales — es decir, las intendencias controlan los recursos con los que un municipio podría digitalizarse.
- **Art. 7:** la **materia municipal** comprende asuntos locales (vialidad local, alumbrado, espacios públicos, necrópolis, residuos), la celebración de convenios (num. 7) y la **participación en proyectos de cooperación internacional** que comprendan su circunscripción (num. 10) — base jurídica directa para que un municipio CIIAR participe del piloto GovTech Connect.
- **Arts. 12-13:** atribuciones y cometidos (administrar recursos humanos y financieros asignados, supervisar oficinas propias, rendición de cuentas anual y audiencia pública).
- **Arts. 19-20:** financiamiento (programa presupuestal dentro del presupuesto departamental + **Fondo de Incentivo para la Gestión de los Municipios**, redacción dada por el art. 665 de la Ley N° 19.924 de 2020).
- **Art. 8:** donde no hay Municipio, las competencias municipales las ejerce el Gobierno Departamental.

**Implicación clave:** los "trámites municipales" en Uruguay son, en su enorme mayoría, **trámites departamentales** (tributos, permisos de construcción, habilitaciones comerciales, licencias de conducir los gestiona la intendencia); el municipio opera atención de cercanía y servicios locales. El software de diagnóstico debe distinguir ambos niveles. Sobre modificaciones posteriores: no se encontró ninguna "Ley 20.033" modificatoria de este régimen **[NO CONFIRMADO que exista; probablemente un error de numeración — la única modificación relevante hallada es la de la Ley 19.924]**. El número actual de municipios (112 tras la Ley 19.319 de 2015; se citan cifras mayores tras las elecciones de 2025) **[NO CONFIRMADO el conteo vigente a 2026]**.

Fuentes:
- https://www.impo.com.uy/bases/leyes/19272-2014
- https://www.gub.uy/presidencia/institucional/normativa/ley-n-19272-fecha-18092014-ley-descentralizacion-participacion-ciudadana
- https://www.plenariodemunicipios.gub.uy/index.php/inicio-plenario/regimen-municipal.html

**Variables de diagnóstico derivadas:** (a) **mapa competencial del trámite** (¿lo presta el municipio, la intendencia o es delegado?) — variable estructural previa a todas las demás; (b) **funcionarios involucrados por trámite**, distinguiendo funcionarios municipales (art. 12 num. 2) de departamentales; (c) **ciudadanos que demandan el servicio** por circunscripción municipal (población >2.000 hab. como unidad de análisis).

---

## 8. Software libre en el Estado: Ley 19.179

La **Ley N° 19.179** (27 de diciembre de 2013) regula el uso de **software libre y formatos abiertos en el Estado**, reglamentada por el **Decreto N° 44/015** (30 de enero de 2015) **[VERIFICADO]**. Su alcance incluye **expresamente a los Gobiernos Departamentales y las Juntas Departamentales**, además de los tres Poderes, entes autónomos, servicios descentralizados y empresas con mayoría estatal **[VERIFICADO en el texto legal]**. Dispone:

- **Art. 1:** toda información del Estado debe distribuirse y aceptarse en al menos un **formato abierto, estándar y libre**.
- **Art. 2:** en la contratación de licencias **se dará preferencia al software libre**; optar por software privativo exige **fundamentación**; y el software que el Estado contrate o desarrolle, al ser distribuido, **se licenciará como software libre**, con inclusión del código fuente.

Es un régimen de **preferencia fundamentada**, no de obligación absoluta de uso de software libre. Para la postulación GovTech Connect es un argumento jurídico directo: un software de diagnóstico **open source** encaja en la preferencia legal de contratación de las intendencias uruguayas y en la práctica de Agesic de liberar componentes (GitHub AGESIC-UY).

Fuentes:
- https://www.impo.com.uy/bases/leyes/19179-2013
- https://www.impo.com.uy/bases/decretos/44-2015
- https://parlamento.gub.uy/documentosyleyes/leyes/ley/19179

**Variable de diagnóstico derivada:** política de licenciamiento del gobierno local (¿usa/prefiere software libre?, ¿publica en formatos abiertos?) — además, la ley **habilita la adopción del propio software de diagnóstico** por las intendencias sin barrera de licenciamiento.

---

## Tabla final: norma → variable de diagnóstico municipal

| Norma (año / última modificación) | Qué obliga o habilita a nivel departamental/municipal | Variable del diagnóstico |
|---|---|---|
| Ley 17.930 art. 72 (2005) + Decreto 184/015 (2015) — Agesic | Rectoría plena solo en Adm. Central; asesoría y plataformas a intendencias por convenio (Convenio Agesic–Congreso de Intendentes) | Existencia de convenio con Agesic y adopción de sus plataformas (índice de madurez) |
| Ley 19.355 arts. 73-76 (2015) + Decreto 184/015 | Derecho ciudadano al canal electrónico; domicilio electrónico (art. 75 nombra a Gob. Departamentales); simplificación y publicación de trámites; prohibición de pedir documentos que el Estado ya tiene | **Trámites disponibles** y % en línea; publicación de requisitos/costos/plazos; **documentos papel vs digital** exigidos al ciudadano |
| Ley 18.600 (2009; mod. Ley 19.535/2017; Decretos 70/018 y 71/025) | Art. 8 habilita expresamente a Gob. Departamentales a firmar actos y contratos con FE/FEA; identificación digital equivalente a presencial | **Firma electrónica**: uso de FE/FEA en actos y trámites locales; aceptación de identidad digital |
| Ley 16.736 arts. 694-697 (1996) + Decretos 65/998 y 276/013 | Validez de actuaciones y actos administrativos electrónicos como instrumentos públicos; expediente electrónico | **Papel vs digital en back-office**; **funcionarios involucrados por trámite** (trazabilidad de pases) |
| Ley 18.331 (2008; mod. Ley 19.670 arts. 37-40/2018; Decreto 64/020) | Aplica a bases de datos de intendencias/municipios; delegado de protección de datos obligatorio en entidades públicas; notificación de brechas | Designación de **delegado de datos**; gestión de datos de los **ciudadanos que demandan servicios**; requisito de diseño del propio software |
| Ley 18.719 arts. 157-160 (2010) + Decreto 178/013 — PDI | Obligación de intercambio de información entre entidades públicas; constancias digitales con FEA | Consumo de la **Plataforma de Interoperabilidad**; reducción de documentos solicitados |
| Requisitos Agesic de pasarelas de pago (soft law técnico; no hay pasarela estatal única confirmada) | Estándar técnico nacional para pagos en línea; redes de cobranza; soluciones propias por intendencia | **Existencia de motor de pagos** en línea y su conformidad con requisitos Agesic |
| Ley 19.272 (2014; mod. Ley 19.924 art. 665/2020) | Define materia municipal vs departamental; convenios y cooperación internacional municipal (art. 7 nums. 7 y 10) | **Mapa competencial del trámite**; **funcionarios** por nivel de gobierno; población/**demanda ciudadana** por municipio |
| Ley 19.179 (2013) + Decreto 44/015 (2015) | Preferencia por software libre y formatos abiertos; alcanza expresamente a Gob. y Juntas Departamentales | Política de licenciamiento local; **viabilidad jurídica de adoptar el software OSS de diagnóstico** |

---

## Síntesis de lo NO confirmado (pendientes de verificación)

1. Estado de aprobación de la **estrategia de gobierno digital 2030 / nueva Agenda Uruguay Digital** (en elaboración según Agesic; sin decreto identificado a jul-2026).
2. Cifra y fecha oficial del logro "100% de trámites de Administración Central en línea".
3. Contenido detallado del **Decreto 71/025** (2025, prestadores de servicios de confianza) — solo verificada su existencia y objeto vía IMPO.
4. **No existe evidencia de una pasarela de pagos estatal única obligatoria** ("ePagos"); confirmado solo el estándar técnico Agesic y soluciones por intendencia (hallazgo negativo, útil para el diseño).
5. Número vigente de municipios a 2026 (112 en 2015; cifras posteriores sin cotejar) y grado de adopción real de expediente electrónico por intendencia.
6. Inexistencia de una "Ley 20.033" modificatoria de la Ley 19.272 (no se encontró; presunta errata) y verificación puntual de la Ley 20.212 en materia de datos personales.
