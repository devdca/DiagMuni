# Anexo A — Marco jurídico mexicano vigente (2025–2026) para la digitalización de trámites y servicios municipales

**Fecha de corte de la investigación:** 14 de julio de 2026.
**Método:** verificación contra fuentes oficiales (DOF, Cámara de Diputados/LeyesBiblio, gob.mx, Banxico) y fuentes secundarias jurídicas. Al final de cada sección se listan las URL consultadas; la sección 8 distingue lo verificado de lo no confirmado.

---

## 0. Advertencia previa: el marco cambió radicalmente en 2024–2025

Quien diseñe hoy un diagnóstico de modernización municipal en México debe partir de que **el régimen de mejora regulatoria vigente hasta 2025 ya no existe**. La secuencia verificada es la siguiente:

1. **28 de noviembre de 2024** — Reforma a la Ley Orgánica de la Administración Pública Federal (DOF): se crea la **Agencia de Transformación Digital y Telecomunicaciones (ATDT)**, con rango de Secretaría de Estado, que concentra las políticas de gobierno digital, inclusión digital, TIC y telecomunicaciones. Inició operaciones el 1 de enero de 2025.
2. **20 de diciembre de 2024** — Reforma constitucional de "simplificación orgánica" (DOF): desaparecen siete órganos autónomos, entre ellos el **INAI**.
3. **20 de marzo de 2025** — Se publican en el DOF (edición vespertina) la **nueva LGPDPPSO**, la **nueva Ley General de Transparencia y Acceso a la Información Pública** y la nueva **LFPDPPP** (particulares). Las versiones de 2017/2015 quedan abrogadas.
4. **15 de abril de 2025** — Reforma constitucional a los **artículos 25 (párrafo décimo) y 73, fracción XXIX-Y** (DOF): la simplificación administrativa y la digitalización de trámites se vuelven mandato constitucional para **los tres órdenes de gobierno**, y se faculta al Congreso para expedir una ley nacional en la materia.
5. **16 de julio de 2025** — Se publica la **Ley Nacional para Eliminar Trámites Burocráticos (LNETB)** (DOF, en vigor 17-jul-2025), que **abroga la Ley General de Mejora Regulatoria (2018) y todas las leyes locales derivadas de ella**, y **extingue la CONAMER**. La ATDT asume como Autoridad Nacional de Simplificación y Digitalización.

Consecuencia práctica para el software de diagnóstico: las referencias "CONAMER", "Catálogo Nacional de Regulaciones, Trámites y Servicios" y "Registro Municipal de Trámites y Servicios" (RETyS) corresponden al régimen abrogado; sus equivalentes vigentes son la **ATDT**, el **Portal Ciudadano Único de Trámites y Servicios** y el **Registro Nacional de Regulaciones**.

**Fuentes:**
- https://www.dof.gob.mx/nota_detalle.php?codigo=5744005&fecha=28/11/2024 (reforma LOAPF, creación ATDT)
- https://www.dof.gob.mx/nota_detalle.php?codigo=5745905&fecha=20/12/2024 (reforma constitucional simplificación orgánica / extinción INAI)
- https://idconline.mx/corporativo/2025/04/16/simplificacion-administrativa-via-reforma-constitucional (reforma arts. 25 y 73 XXIX-Y, DOF 15-abr-2025)
- https://dof.gob.mx/nota_detalle.php?codigo=5763166&fecha=16/07/2025 (decreto LNETB)
- https://www.diputados.gob.mx/LeyesBiblio/abro/lgmr.htm (constancia de abrogación de la LGMR)

---

## 1. Ley Nacional para Eliminar Trámites Burocráticos (LNETB) — la norma eje

**Nombre exacto:** Ley Nacional para Eliminar Trámites Burocráticos.
**Publicación:** DOF 16 de julio de 2025 (nueva ley; en vigor 17-jul-2025). Reglamentaria del artículo 25 constitucional (art. 1). Texto verificado directamente en el PDF oficial de la Cámara de Diputados (30 pp.).

**Qué obliga o habilita a nivel municipal** (artículos cotejados en el texto oficial):

- **Art. 7**: los municipios son sujetos obligados junto con la administración pública federal y estatal y las demarcaciones de CDMX.
- **Art. 11**: los poderes ejecutivos **estatales y municipales** deben contar con una **Autoridad Local de Simplificación y Digitalización**, transversal, con al menos cinco áreas sustantivas (Simplificación; Digitalización; Atención Ciudadana; Buenas prácticas regulatorias; Desarrollo de Soluciones Tecnológicas). Los municipios deben tener "al menos, el personal suficiente para mantener actualizadas las soluciones tecnológicas que reciban".
- **Arts. 14–15**: cada sujeto obligado designa un **Enlace de Simplificación y Digitalización** (nivel mínimo director general u homólogo) que debe, entre otras cosas, llevar "un estricto inventario de la totalidad de trámites, servicios y requisitos" (art. 15-IV) y "mantener una métrica actualizada de los usos de cada trámite y servicio" (art. 15-X).
- **Art. 16**: obligaciones generales: mantener actualizados los trámites en el Portal Ciudadano Único (fracc. III) y el Registro de Regulaciones (IV); habilitar plataformas digitales (VII); **compartir el código fuente** de las soluciones desarrolladas, para integrarlo al Repositorio Nacional de Tecnología Pública (VIII) — la ley institucionaliza una lógica de software público compartido, muy alineada con un proyecto open source; reconocer e implementar **Llave MX** como autenticación e inicio de sesión único (IX y X); reconocer validez jurídica plena a los documentos digitales (XI); privilegiar alojamiento en infraestructura propia o en territorio nacional (XII).
- **Arts. 24–25**: los titulares pueden simplificar por **acuerdos generales** (habilitar medios digitales, reducir plazos, eliminar requisitos y costos). Los municipios sin capacidades técnicas o presupuestales **pueden celebrar convenios con la ATDT** para usar soluciones del Repositorio Nacional de Tecnología Pública o con la autoridad estatal para acompañamiento. Los desarrollos deben usar librerías estables y ampliamente utilizadas, integrar Llave MX, **permitir el uso de firmas electrónicas** (art. 25-III) y cumplir estándares de ciberseguridad.
- **Arts. 51–54 (Portal Ciudadano Único de Trámites y Servicios)**: medio nacional de registro de **todos** los trámites y servicios de los tres órdenes de gobierno; ninguna autoridad puede exigir requisitos no inscritos (art. 51). El art. 53 obliga a inscribir y mantener actualizada la información, con plazo de 5 días hábiles para corregir errores y sanción conforme a la Ley General de Responsabilidades Administrativas. El **art. 54** enumera los campos mínimos del registro — que son, de facto, el modelo de datos mínimo de cualquier inventario municipal de trámites: nombre y clave; modalidad; disponibilidad en línea o presencial; fundamento jurídico; descripción en lenguaje ciudadano; requisitos; inspecciones asociadas; medios de contacto; plazo de resolución y ficta aplicable; plazos de prevención; **monto de derechos o aprovechamientos y alternativas para realizar el pago**; vigencia de las resoluciones; oficinas de recepción; horarios.
- **Arts. 55–56**: **Registro Nacional de Regulaciones**, administrado por la ATDT; los municipios deben inscribir y mantener actualizadas sus regulaciones (reglamentos, bandos, etc.).
- **Arts. 64–75 (Llave MX)**: mecanismo nacional de autenticación asociado a la CURP; cuando la CURP tiene biométricos asociados funciona como documento nacional de identificación digital (art. 67); toda plataforma municipal de trámites debe integrarla como inicio de sesión único (arts. 69 y 74); las entidades pueden mantener mecanismos propios de autenticación de forma complementaria (art. 68).
- **Arts. 76–84 (Expediente Digital Ciudadano)**: interoperabilidad de documentos del ciudadano; **prohibición de pedir documentos que ya obren en el expediente** (art. 78); validez jurídica y probatoria plena de documentos y notificaciones digitales (arts. 80–81); obligación de conservar mensajes de datos y documentos digitales (art. 83) y de garantizar autenticidad, integridad y control archivístico (art. 84, puente con la Ley General de Archivos).
- **Arts. 102–104**: la ATDT otorga **Certificaciones de Simplificación y Digitalización** a sujetos obligados (un "sello" al que un municipio puede aspirar; el diagnóstico puede medir la distancia a ese estándar).
- **Arts. 108–112**: Registro Nacional de Visitas Domiciliarias y Padrón Nacional de Inspectores (transparencia de inspecciones/verificaciones municipales).
- **Transitorios** (verificado en fuentes secundarias jurídicas, no en el texto íntegro): lineamientos de los Modelos Nacionales a cargo de la ATDT en ~30 días hábiles; autoridades estatales y municipales deben adecuar sus regulaciones en un plazo de **180 días hábiles**; migración del anterior Catálogo Nacional al nuevo Portal.

**Variables de diagnóstico que se derivan de la LNETB:**
- ¿Existe Autoridad Municipal de Simplificación y Digitalización designada y con las 5 áreas del art. 11? (art. 11)
- ¿Hay Enlace de Simplificación y Digitalización designado? (art. 14)
- ¿Existe inventario completo de trámites, servicios y requisitos? ¿Cuántos trámites tiene el municipio? (art. 15-IV → variable "trámites disponibles")
- ¿Se lleva métrica de usos por trámite? (art. 15-X → variable "ciudadanos que demandan el servicio")
- ¿Los trámites están inscritos y actualizados en el Portal Ciudadano Único, con los 15 campos del art. 54? (arts. 53–54)
- ¿El trámite está disponible en línea o solo presencial? (art. 54-III)
- ¿Se publican monto y **alternativas de pago**? ¿Existe motor de pagos digital? (art. 54-XI)
- ¿Las plataformas municipales integran Llave MX y aceptan firma electrónica? (arts. 16-IX/X, 25-III, 74)
- ¿Se solicita al ciudadano documentación que ya obra en poder del gobierno (violación al art. 78)? (→ variable "documentos en papel vs digital")
- ¿El municipio comparte/reutiliza código del Repositorio Nacional de Tecnología Pública? (arts. 16-VIII, 25, 91–93)
- Nota: la ley no fija cuántos funcionarios pueden intervenir por trámite, pero los principios de simplificación y la obligación de eliminar requisitos y costos burocráticos (art. 24) sustentan la variable "funcionarios involucrados por trámite" como indicador de carga burocrática.

**Fuentes:**
- Texto oficial: https://www.diputados.gob.mx/LeyesBiblio/pdf/LNETB.pdf
- DOF: https://dof.gob.mx/nota_detalle.php?codigo=5763166&fecha=16/07/2025
- Síntesis jurídicas: https://mexico.justia.com/blog/entra-en-vigor-la-ley-nacional-para-eliminar-tramites-burocraticos-de-que-trata-esta-ley/ ; https://www.taxtodaymexico.com/simplificacion-administrativa-y-gobierno-digital-alcances-de-la-nueva-ley-nacional-para-eliminar-tramites-burocraticos/ ; https://www.garrigues.com/en_GB/new/mexico-what-you-should-know-about-new-national-law-eliminate-bureaucratic-procedures

### 1.bis Ley General de Mejora Regulatoria (referencia histórica, ABROGADA)
Publicada en DOF 18-may-2018, última reforma 20-may-2021, **abrogada el 16-jul-2025**. Era la fuente del Catálogo Nacional de Regulaciones, Trámites y Servicios (arts. 38 y ss.) y de los Registros (estatales y municipales) de Trámites y Servicios. Solo debe citarse como antecedente; los catálogos municipales construidos bajo ese régimen son el insumo que migra al Portal Ciudadano Único. Fuente: https://www.diputados.gob.mx/LeyesBiblio/abro/lgmr.htm

---

## 2. Ley General de Archivos (LGA)

**Nombre exacto:** Ley General de Archivos. **Publicación:** DOF 15 de junio de 2018 (vigente desde junio de 2019). **Última reforma:** DOF **14 de noviembre de 2025** (reforma menor de supletoriedad procesal, dentro del decreto de armonización con el Código Nacional de Procedimientos Civiles y Familiares; la reforma 1 fue 05-abr-2022). Artículos cotejados en el PDF oficial de Diputados.

**Qué obliga a nivel municipal:** los municipios son sujetos obligados (art. 1). Obligaciones clave verificadas:
- **Art. 11**: administrar, organizar y conservar homogéneamente los documentos de archivo; contar con sistema institucional de archivos, grupo interdisciplinario e instrumentos de control archivístico.
- **Art. 12**: mantener los documentos conforme a los procesos de gestión documental (producción, organización, acceso, consulta, valoración, disposición, conservación).
- **Capítulo de documentos de archivo electrónicos (arts. 41–49)**:
  - Art. 41: la gestión documental **electrónica** debe incorporar acceso, seguridad, almacenamiento, uso y trazabilidad.
  - Art. 42: el programa anual debe prever generación, administración, uso, control y **migración de formatos electrónicos** y planes de preservación de largo plazo.
  - Art. 44: medidas técnicas y tecnológicas para recuperar y preservar documentos electrónicos en sistemas automatizados, bases de datos y correos.
  - **Art. 45**: obligación de **implementar sistemas automatizados de gestión documental y administración de archivos** (SIGDA).
  - Art. 46: lineamientos del Consejo Nacional de Archivos para sistemas y repositorios electrónicos, con fomento de **formatos abiertos**.
  - Art. 47: la digitalización **no autoriza a destruir** el soporte papel salvo previsión legal expresa.
  - Art. 48: los trámites con **firma electrónica avanzada** generan documentos de archivo electrónico con validez jurídica.
  - Art. 49: proteger documentos, sistemas y firma electrónica contra la obsolescencia tecnológica.
- **Art. 62**: se permite gestionar documentos electrónicos en **servicios de nube** que cumplan condiciones de seguridad, interoperabilidad y auditabilidad.
- La definición legal de **expediente electrónico** (art. 4: "conjunto de documentos electrónicos correspondientes a un procedimiento administrativo") es la base conceptual del expediente digital de trámites.

**Variables de diagnóstico derivadas:** proporción de documentos gestionados en papel vs digital por trámite (arts. 41–45 y 47); ¿existe sistema automatizado de gestión documental (art. 45)?; ¿existe programa anual de archivos con estrategia de preservación digital (arts. 42–43)?; ¿los documentos firmados electrónicamente se archivan con validez (art. 48)?

**Fuentes:**
- Texto oficial: https://www.diputados.gob.mx/LeyesBiblio/pdf/LGA.pdf
- Historial de reformas: https://www.diputados.gob.mx/LeyesBiblio/ref/lga.htm
- Reforma 3 (14-nov-2025): http://www.diputados.gob.mx/LeyesBiblio//ref/lga/LGA_ref03_14nov25.pdf
- Decreto original: https://www.dof.gob.mx/nota_detalle.php?codigo=5526593&fecha=15/06/2018

---

## 3. Firma electrónica

### 3.1 Ley de Firma Electrónica Avanzada (LFEA, federal)
**Publicación:** DOF 11 de enero de 2012. **Última reforma:** DOF **14 de noviembre de 2025** (verificado en el encabezado del PDF oficial). Regula el uso de la FEA en actos de la **Administración Pública Federal** (arts. 1–2); no rige directamente a los municipios, pero prevé **convenios de coordinación para el reconocimiento de certificados digitales homologados** entre el Ejecutivo Federal (SHCP/ Economía/ SAT) y "los gobiernos de las entidades federativas, municipios y órganos político-administrativos de la Ciudad de México" (régimen de homologación, verificado en la propia ley y su Reglamento). Es decir: un municipio puede aceptar la e.firma del SAT en sus trámites mediante convenio.

### 3.2 e.firma del SAT
Fundamento: **art. 17-D del Código Fiscal de la Federación** (certificados de firma electrónica avanzada emitidos por el SAT). En la práctica es la credencial FEA más extendida entre ciudadanos y empresas, y la que los portales estatales/municipales suelen aceptar vía homologación. (Fundamento normativo notorio; no se cotejó el texto íntegro del CFF en esta corrida.)

### 3.3 Leyes estatales de firma electrónica y gobierno digital (las que sí obligan al municipio)
La firma electrónica en trámites municipales se rige por la legislación **estatal**: existen leyes como la **Ley de Firma Electrónica Avanzada para el Estado de Jalisco y sus Municipios**, la Ley de Firma Electrónica del Estado de Zacatecas, la Ley de Firma Electrónica Avanzada y Uso de Medios Electrónicos de Campeche, la Ley sobre el Uso de Medios Electrónicos y Firma Electrónica de Guanajuato, o la Ley de Gobierno Digital del Estado de México y Municipios (esta última citada como categoría; no verificada en esta corrida). El diagnóstico debe capturar **qué ley estatal aplica al municipio evaluado**.

### 3.4 LNETB como norma de cierre
El art. 25-III LNETB obliga a que toda solución tecnológica municipal de trámites "**permita el uso de Firmas Electrónicas**", y los arts. 80–81 dan validez jurídica y probatoria plena a documentos y actuaciones digitales. Llave MX (arts. 64 y ss.) funciona como **autenticación/identificación**, distinta de la firma; ambas conviven.

**Variables de diagnóstico derivadas:** ¿los trámites municipales admiten firma electrónica (avanzada o estatal)? (LNETB art. 25-III; ley estatal aplicable); ¿el municipio tiene convenio de homologación para aceptar e.firma del SAT? (LFEA y su Reglamento); ¿las resoluciones que emite el municipio se firman electrónicamente y se archivan con validez? (LGA art. 48).

**Fuentes:**
- Texto oficial LFEA: https://www.diputados.gob.mx/LeyesBiblio/pdf/LFEA.pdf
- Reglamento LFEA: https://www.diputados.gob.mx/LeyesBiblio/regley/Reg_LFEA.pdf y http://www.ordenjuridico.gob.mx/Documentos/Federal/html/wo93113.html
- Decreto original: https://dof.gob.mx/nota_detalle.php?codigo=5228864&fecha=11/01/2012
- Ejemplo estatal (Jalisco): https://congresoweb.congresojal.gob.mx/bibliotecavirtual/legislacion/Leyes/Ley%20de%20Firma%20Electr%C3%B3nica%20Avanzada%20para%20el%20Estado%20de%20Jalisco%20y%20sus%20Municipios.doc

---

## 4. Pagos electrónicos y comprobantes en la hacienda municipal

### 4.1 Base constitucional y leyes de ingresos
El **art. 115, fracción IV, CPEUM** reserva a los municipios su hacienda (contribuciones sobre propiedad inmobiliaria, derechos por servicios públicos), recaudada conforme a la **Ley de Ingresos municipal** que aprueba anualmente la legislatura estatal y a la ley de hacienda municipal de cada estado. No existe una ley federal que obligue a los municipios a cobrar en línea; la obligación práctica más cercana es el **art. 54-XI LNETB**: publicar en el Portal Ciudadano Único el monto de derechos/aprovechamientos "así como las alternativas para realizar el pago". (Art. 115 citado por notoriedad; texto no cotejado en esta corrida.)

### 4.2 CoDi y SPEI (habilitadores, no obligaciones)
**CoDi (Cobro Digital)** es el esquema de solicitudes de pago sobre **SPEI** desarrollado por Banxico (operación plena desde el 4T de 2019); su marco operativo son las reglas del SPEI (**Circular 14/2017 de Banxico y sus modificaciones**, entre ellas las de 2019 que incorporaron las órdenes CoDi, y la Circular 1/2022). Es un habilitador de recaudación digital sin comisiones que municipios como Mérida ya usan para predial (con tope por operación). **No confirmado:** el número exacto de la circular que introdujo CoDi (8/2019 ó 12/2019) — verificar en Banxico antes de citarlo en un documento formal.

### 4.3 CFDI por cobros municipales
- **Art. 29 del CFF**: quien recaude contribuciones debe expedir comprobante fiscal digital por internet (CFDI).
- **Mecanismo de dos piezas en la Ley del ISR** (ambas necesarias; ninguna basta por sí sola):
  - **Art. 79, fracción XXIII, de la LISR**: clasifica expresamente a la Federación, las entidades federativas, **los municipios** y las instituciones que por ley estén obligadas a entregar al Gobierno Federal el importe íntegro de su remanente de operación, como personas morales con fines no lucrativos del Título III. Esta fracción es la que sitúa jurídicamente al municipio dentro de este régimen (verificado vía `sat.gob.mx/articulo/23073/articulo-79`; ver detalle y fuentes en `entregables/fase-2/verificacion-motor-pagos.md`, sección 1.3).
  - **Art. 86, quinto párrafo, de la LISR**: para esos mismos entes del Título III (Federación, entidades federativas, municipios e instituciones obligadas a entregar su remanente), impone la obligación específica de **expedir CFDI por las contribuciones, productos y aprovechamientos que cobran**, y por los apoyos o estímulos que otorgan.
  - En conjunto, el art. 79-XXIII es la pieza que **clasifica/habilita** (el municipio es un ente del Título III) y el art. 86, 5º párr., es la pieza que **obliga en concreto** a expedir el CFDI; ninguna de las dos por separado sustenta completa la afirmación "el municipio debe emitir CFDI por lo que cobra". (Verificado por concordancia de fuentes oficiales/oficiales-adyacentes independientes — SAT, materiales de capacitación fiscal de gobiernos estatales de Aguascalientes y Guanajuato, compendios fiscales especializados y la guía de llenado de CFDI del propio SAT —, **no por lectura directa del texto íntegro de la LISR**; cotejar párrafo exacto en el PDF oficial de LeyesBiblio antes de citar textualmente. Ver `entregables/fase-2/verificacion-motor-pagos.md`, sección 1.3, que documenta el detalle de fuentes de esta verificación.)
- Consecuencia práctica documentada: sin CFDI del municipio, el contribuyente no puede deducir predial o derechos; muchos municipios aún no emiten CFDI de forma automática, lo que lo convierte en un excelente indicador de madurez.

**Variables de diagnóstico derivadas:** ¿existe motor de pagos en línea para derechos y contribuciones municipales? (LNETB art. 54-XI); ¿acepta transferencia SPEI/CoDi además de tarjeta y ventanilla bancaria?; ¿el municipio emite CFDI automáticamente por cada cobro? (CFF art. 29; LISR arts. 79-XXIII y 86, 5º párr.); ¿los pagos se concilian con el trámite (folio de pago vinculado al expediente)?

**Fuentes:**
- CoDi Banxico: https://www.banxico.org.mx/sistemas-de-pago/codi-avances-banco-mexico.html y https://www.codi.org.mx/secundarias/cobrar.html
- Circular 14/2017 (reglas SPEI): https://www.banxico.org.mx/marco-normativo/normativa-emitida-por-el-banco-de-mexico/circular-14-2017/sistema-pagos-spei-disposicio.html
- CFF: http://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf
- LISR art. 79, fracción XXIII (clasificación de municipios como entes del Título III): https://www.sat.gob.mx/articulo/23073/articulo-79
- Guía de llenado de CFDI del SAT para entes públicos (LISR art. 86, 5º párr.): https://www.sat.gob.mx/minisitio/Factura/documentos/Guia_llenadoCFDI_DPA.pdf
- Obligaciones fiscales gubernamentales (LISR 86, CFDI municipal): https://caceg.guanajuato.gob.mx/sites/default/files/training/C_FISCALES_GUBERNAMENTALES_.pdf
- CFDI predial/tenencia: https://www.elcontribuyente.mx/2025/02/pide-tu-factura-sin-cfdi-no-podras-deducir-el-pago-de-predial-y-tenencia/
- Verificación del mecanismo completo (dos artículos) y detalle de fuentes: `entregables/fase-2/verificacion-motor-pagos.md`, sección 1.3

---

## 5. Protección de datos personales en posesión de sujetos obligados (régimen post-INAI)

**Nombre exacto:** Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados — **NUEVA ley del mismo nombre**, publicada en el **DOF el 20 de marzo de 2025** (edición vespertina), en vigor 21-mar-2025, **última reforma 14-nov-2025** (verificado en el encabezado del PDF oficial). La LGPDPPSO de 26-ene-2017 quedó **abrogada**.

**Cambios institucionales verificados:**
- El **INAI desapareció** (reforma constitucional de simplificación orgánica, DOF 20-dic-2024).
- La autoridad rectora nacional es ahora la **Secretaría Anticorrupción y Buen Gobierno** (art. 3, fracc. XXVI, define "Secretaría"; la ley distribuye competencias entre la Secretaría y las "Autoridades garantes", art. 2-II).
- Las **"Autoridades garantes"** (art. 3-II) ya no son organismos autónomos: son los órganos de control/contralorías internas de cada poder u orden de gobierno (incluidos los de las entidades federativas). Para un municipio, la supervisión recae en la cadena de contraloría de su entidad federativa y, en lo nacional, en la Secretaría Anticorrupción y Buen Gobierno. Los organismos garantes locales autónomos del régimen 2017 desaparecen del esquema.

**Qué obliga a nivel municipal (artículos cotejados):** los municipios siguen siendo sujetos obligados (arts. 1–2: la ley protege datos "de la Federación, partidos políticos, las Entidades Federativas y los municipios"). Obligaciones operativas relevantes para trámites digitales:
- **Arts. 20–22**: **aviso de privacidad** (integral y simplificado) al recabar datos en cualquier trámite, físico o digital, con contenido mínimo (art. 21).
- **Arts. 25–28**: **medidas de seguridad** administrativas, físicas y técnicas; análisis de brecha, plan de trabajo y monitoreo (art. 27); documentación de las medidas (art. 28, funciona como el "documento de seguridad").
- Deber de **notificar vulneraciones** que afecten significativamente derechos, a la Secretaría o a la Autoridad garante.
- **Evaluación de impacto en protección de datos** para tratamientos intensivos (arts. 69–72 del nuevo texto, verificados por referencia interna).
- La LNETB remite expresamente a esta ley: el Expediente Digital Ciudadano exige consentimiento del titular y trazabilidad (LNETB arts. 77 y 82).

**Variables de diagnóstico derivadas:** ¿cada trámite (formulario físico o digital) tiene aviso de privacidad conforme a los arts. 20–22?; ¿existen documento de seguridad y análisis de brecha (arts. 26–28)?; ¿hay unidad/responsable de datos personales designado?; ¿la plataforma registra consentimiento y trazabilidad de acceso a datos (LNETB arts. 77–78)?

**Fuentes:**
- Texto oficial vigente: https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPDPPSO.pdf
- DOF 20-mar-2025 (edición vespertina): https://datos-personales.scjn.gob.mx/sites/default/files/normativa-materia/LGPDPPSO-DOF-20Mar2025.pdf
- Ley abrogada (2017): https://www.diputados.gob.mx/LeyesBiblio/abro/lgpdppso_2017.htm
- Análisis: https://www.gtlaw.com/en/insights/2025/3/nueva-ley-general-proteccion-de-datos ; https://www.bakertilly.mx/en/insights/nuevas-disposiciones-en-materia-de-datos-personales

---

## 6. Otras normas del ecosistema (contexto)

- **Ley General de Transparencia y Acceso a la Información Pública (nueva, DOF 20-mar-2025):** los municipios mantienen obligaciones de transparencia activa (información de trámites, requisitos y formatos en la Plataforma Nacional de Transparencia), ahora bajo la arquitectura post-INAI. Relevante como fuente secundaria de la variable "trámites publicados". (Existencia y fecha verificadas; articulado no cotejado.)
- **Ley en Materia de Telecomunicaciones y Radiodifusión (DOF 16-jul-2025):** consolida a la ATDT/CRT en el sector telecom tras la extinción del IFT; contexto de conectividad, sin obligaciones municipales directas de trámites. (Existencia verificada; articulado no cotejado.)
- **CURP biométrica (reformas de 2025 a la Ley General de Población):** la LNETB (art. 67) ya prevé que la CURP con biométricos funja como documento nacional de identificación digital; el detalle de la reforma poblacional no se cotejó en esta corrida.
- **Ley General de Responsabilidades Administrativas:** es el régimen sancionador aplicable a servidores públicos municipales que incumplan la actualización del Portal (LNETB art. 53).

---

## 7. Tabla final: norma → variable de diagnóstico

| Norma (vigencia) | Disposición | Variable del diagnóstico municipal |
|---|---|---|
| LNETB (DOF 16-jul-2025) | Art. 11 | Existe Autoridad Municipal de Simplificación y Digitalización (y sus 5 áreas) |
| LNETB | Arts. 14–15 (fracc. IV) | Inventario total de trámites, servicios y requisitos → **número de trámites disponibles** |
| LNETB | Art. 15, fracc. X | Métrica de usos por trámite → **ciudadanos que demandan el servicio** |
| LNETB | Arts. 53–54 | Trámite inscrito/actualizado en el Portal Ciudadano Único con los 15 campos mínimos |
| LNETB | Art. 54, fracc. III | Trámite disponible **en línea o solo presencial** |
| LNETB | Art. 54, fracc. XI | Monto y alternativas de pago publicadas → **existencia de motor de pagos** |
| LNETB | Arts. 16-IX/X, 64–75 | Plataforma integra **Llave MX** como inicio de sesión único |
| LNETB | Art. 25, fracc. III | La solución tecnológica **permite firma electrónica** |
| LNETB | Arts. 76–78 | No se piden documentos ya disponibles en el Expediente Digital → **papel vs digital** |
| LNETB | Arts. 16-VIII, 91–93 | Reutilización/aporte de código al Repositorio Nacional de Tecnología Pública (open source) |
| LNETB | Art. 24 | Acuerdos de simplificación emitidos (reducción de requisitos, plazos, costos) → proxy de **funcionarios involucrados por trámite** |
| LGA (2018, ref. 14-nov-2025) | Arts. 41–45 | Gestión documental electrónica y **sistema automatizado de archivos** → documentos papel vs digital |
| LGA | Art. 42–43 | Programa anual con preservación digital de largo plazo |
| LGA | Art. 48 | Documentos firmados electrónicamente con validez archivística |
| LGA | Art. 62 | Uso de nube con controles → infraestructura del municipio |
| LFEA (2012, ref. 14-nov-2025) + Reglamento | Régimen de homologación | Convenio para aceptar e.firma (SAT) en trámites municipales |
| Ley estatal de firma-e / gobierno digital | Según entidad | Qué firma electrónica estatal aplica y si el municipio la usa |
| CFF art. 29 + LISR arts. 79, fracc. XXIII y 86 (5º párr.) | Comprobantes | El municipio **emite CFDI automático** por derechos y aprovechamientos |
| Circular 14/2017 Banxico (SPEI/CoDi) | Habilitador | El motor de pagos acepta SPEI/CoDi |
| CPEUM art. 115-IV + Ley de Ingresos municipal | Hacienda | Catálogo tarifario vinculado a cada trámite |
| Nueva LGPDPPSO (DOF 20-mar-2025) | Arts. 20–22 | Aviso de privacidad en cada formulario/trámite |
| Nueva LGPDPPSO | Arts. 25–28 | Documento de seguridad, análisis de brecha, responsable de datos |
| Nueva LGPDPPSO + LNETB arts. 77, 82 | Consentimiento | Trazabilidad y consentimiento en el expediente digital |
| LGTAIP (nueva, 2025) | Transparencia activa | Publicación de trámites en la Plataforma Nacional de Transparencia |

---

## 8. Qué está verificado y qué no

**Verificado contra texto oficial (PDF LeyesBiblio/DOF, leído directamente):**
- LNETB: fecha, vigencia, abrogación de la LGMR y extinción de CONAMER; artículos 1, 7, 11–16, 24–25, 51–56, 64–84, 102–112 (citas textuales cotejadas).
- LGA: fecha, última reforma 14-nov-2025; artículos 11, 12, 41–49 y 62 (citas textuales cotejadas).
- Nueva LGPDPPSO: publicación 20-mar-2025, última reforma 14-nov-2025; artículos 1–3 (incl. definición de Secretaría = Anticorrupción y Buen Gobierno y de Autoridades garantes), 20–22, 25–28 (cotejados).
- LFEA: publicación 11-ene-2012, última reforma 14-nov-2025; objeto (arts. 1–2) cotejado.
- Creación de la ATDT (DOF 28-nov-2024) y reforma constitucional arts. 25/73 XXIX-Y (DOF 15-abr-2025): verificadas en fuentes oficiales y jurídicas.

**Verificado solo en fuentes secundarias (usar con cautela / cotejar antes de citar textualmente):**
- Transitorios de la LNETB (plazo de 180 días hábiles para adecuación estatal/municipal; 30 días hábiles para lineamientos ATDT): el texto de los transitorios no aparecía en la extracción del PDF; confirmado por síntesis jurídicas (TaxToday, Garrigues).
- LISR art. 79, fracción XXIII (clasificación de los municipios como entes del Título III) y art. 86, quinto párrafo (CFDI municipal obligatorio): confirmado por concordancia de fuentes oficiales/oficiales-adyacentes independientes (SAT, materiales fiscales de gobiernos estatales, compendios fiscales y guía de llenado de CFDI del SAT), no por lectura directa del PDF de la LISR. Verificación ampliada documentada en `entregables/fase-2/verificacion-motor-pagos.md`, sección 1.3.
- CFF arts. 17-D y 29: citados por notoriedad, no cotejados en esta corrida.

**No confirmado / pendiente:**
- Número exacto de la circular de Banxico que incorporó CoDi a las reglas del SPEI (¿8/2019 o 12/2019?): las fuentes consultadas difieren; solo es seguro que el marco es la Circular 14/2017 y sus modificaciones.
- Si la ATDT ya publicó los **lineamientos** de los Modelos Nacionales y del Portal Ciudadano Único (previstos en transitorios); a la fecha de corte no se localizó su publicación en el DOF — el software debería tratarlos como "parámetro configurable" hasta confirmarlos.
- Estado real de la migración del antiguo Catálogo Nacional (catalogonacional.gob.mx) al nuevo Portal Ciudadano Único, y la URL definitiva de éste.
- El detalle de las reformas 2025 a la Ley General de Población (CURP biométrica) y el contenido de las leyes estatales de gobierno digital distintas de los ejemplos citados.
- El decreto del 14-nov-2025 reformó en bloque LGA, LFEA y LGPDPPSO (armonización procesal); el alcance exacto por ley se verificó solo para la LGA (arts. 3–4, supletoriedad).
