# Brief de diseño UI/UX — DiagMuni

Versión 1 · 21 de julio de 2026
Tercero de los 6 documentos de blueprint de producto. Cubre apariencia y experiencia — paleta, tipografía, componentes, y cómo debería verse cada pantalla — para que la implementación no sea arbitraria. No repite decisiones ya cerradas: componentes en shadcn/ui (Radix + Tailwind, MIT, código copiado al repo — ver `docs/stack-tecnologico.md`), usuario objetivo el funcionario municipal sin perfil técnico (ver `docs/PRD.md`).

## Principios de diseño

1. **Sin jerga técnica, en ningún estado de la interfaz.** El usuario es un funcionario de mostrador, no un tecnólogo (ver `docs/PRD.md`, Usuario objetivo). Ningún texto de UI usa vocabulario de sistemas ("endpoint", "token", "payload") ni normativo sin explicar ("LNETB", "RLS") — el lenguaje es administrativo llano, en español, sin distinguir MX/UY salvo donde la variable realmente lo exige (firma-e, identidad).
2. **Tono institucional, no de producto de consumo.** DiagMuni es una herramienta de gobierno, del Laboratorio de Innovación Pública del INAP — sobrio, confiable, sin animaciones decorativas, sin lenguaje de marketing ("¡genial!", "¡tu plan está listo!"). Serio pero no burocrático: claro y directo.
3. **Debe funcionar igual en un municipio de 3 funcionarios de mostrador que en una intendencia con área TIC** — sin asumir hardware moderno ni gran ancho de banda; sin asumir alfabetización digital alta.
4. **La marca visual del Laboratorio INAP está pendiente** (no se ha definido logo/colores institucionales en este proyecto) — mientras tanto, se usa la paleta neutral validada de esta sección; sustituir cuando exista identidad de marca oficial, sin tocar la estructura de componentes.

## Tipografía

Fuente del sistema únicamente: `system-ui, -apple-system, "Segoe UI", sans-serif` — sin fuente de despliegue ni serif, en ningún lugar, incluida la cifra grande del índice de madurez. Cifras que deben alinearse en columna (tablas de seguimiento, listados de trámites) usan `font-variant-numeric: tabular-nums`; el resto, proporcional.

## Paleta — validada, no elegida a ojo

Paleta neutral de referencia (swap por marca INAP cuando exista, revalidar con `validate_palette.js` si cambia):

| Rol | Claro | Oscuro |
|---|---|---|
| Superficie de página | `#f9f9f7` | `#0d0d0d` |
| Superficie de tarjeta/panel | `#fcfcfb` | `#1a1a19` |
| Texto primario | `#0b0b0b` | `#ffffff` |
| Texto secundario | `#52514e` | `#c3c2b7` |
| Texto atenuado (ayudas, placeholders) | `#898781` | `#898781` |
| Línea divisoria | `#e1e0d9` | `#2c2c2a` |

### Índice de madurez (0-4) — rampa ordinal, un solo hue, nunca semáforo de colores dispares

El índice **no** se pinta con colores categóricos distintos por nivel (rojo→verde) — es una magnitud ordenada, no un estado bueno/malo por sí sola (un nivel 1 no es "un error", es un punto de partida). Usa la rampa secuencial azul, 5 pasos discretos:

| Nivel | Descripción | Paso | Hex (claro) |
|---|---|---|---|
| 0 | Presencial en papel | 250 | `#86b6ef` |
| 1 | Informativo | 350 | `#5598e7` |
| 2 | Transaccional parcial | 450 | `#2a78d6` |
| 3 | Transaccional completo | 550 | `#1c5cab` |
| 4 | Proactivo e interoperable | 650 | `#104281` |

El paso más claro (nivel 0) respeta el piso de contraste 2:1 para uso ordinal — nunca ir más claro que el paso 250. Modo oscuro usa la misma progresión de 5 pasos, revalidada contra la superficie oscura antes de implementar (`node scripts/validate_palette.js ... --mode dark --ordinal`). Cada nivel siempre lleva **número + etiqueta de texto** ("2 — Transaccional parcial"), nunca solo el color — el color refuerza, no reemplaza, la lectura.

### Semáforo de seguimiento (F6) — paleta de estado, fija, nunca reutilizada como color de serie

Solo 3 estados para mantener el panel "simple" (mandato de producto) — se reserva el 4º rol de la paleta de estado por si un futuro rediseño necesita distinguir "atrasado" de "bloqueado":

| Estado | Rol | Hex |
|---|---|---|
| Completado | good | `#0ca30c` |
| En progreso / a tiempo | warning | `#fab219` |
| Atrasado o bloqueado | critical | `#d03b3b` |

Regla dura: todo estado del semáforo lleva **ícono + etiqueta de texto**, nunca solo el punto de color — "warning" y "critical" caen bajo el piso de contraste 3:1 en superficie clara por diseño de la paleta, así que el color solo no basta para transmitir el estado.

## Componentes (shadcn/ui — Radix + Tailwind)

Reutilizar los componentes ya incluidos en shadcn/ui sin construir variantes propias salvo que el catálogo no cubra el caso: `Form` + `Input`/`Select`/`RadioGroup` (cuestionario F1), `Textarea` (cuestionario F1 — campo opcional de aclaración en texto libre adjunto a cada pregunta, y descripción obligatoria al elegir "Otro, especifique" en la pregunta de mecanismo de identidad; ver `entregables/fase-2/asistente-captura-f1.md`), `Table` (listado de trámites, panel de seguimiento), `Card` (resumen de índice, resumen de acción del plan), `Badge` (nivel de índice, estado de semáforo — nunca badge de color puro, siempre con texto), `Progress` (avance del cuestionario), `Accordion` (desglose de cada acción del plan: paso administrativo/técnico/organizacional). Sin componentes de terceros adicionales — shadcn/ui ya es suficiente para el alcance del MVP.

## Pantallas principales

### 1. Selección de gobierno (tenant) e ingreso
Pantalla mínima: campo "Clave del gobierno" (texto corto y legible, nunca un identificador técnico) que el funcionario escribe para identificar a su gobierno local; al resolverse contra el backend, se muestra el nombre del gobierno como confirmación antes de revelar los campos de correo y contraseña (o un selector si el funcionario tiene acceso a más de un gobierno — poco común en el MVP). Sin branding de terceros, sin distractores. Mensaje de error en lenguaje llano tanto si la clave no corresponde a ningún gobierno como si la contraseña no coincide ("La contraseña no coincide", nunca un código de error técnico). Mecanismo completo de identificación (columna `tenant.clave`, endpoint público de resolución, y cómo se conecta con `POST /api/auth/login`) en `entregables/fase-2/identificacion-gobierno-login.md`.

### 2. Panel resumen
Tarjeta superior con el índice de madurez global (cifra grande + etiqueta, paleta ordinal de arriba) y fecha de último diagnóstico. Debajo, tabla de trámites catalogados con su índice individual (`Badge`) y acceso a "continuar diagnóstico" o "ver plan". Sin gráficas de tendencia en el MVP — un solo número por trámite, no series de tiempo (no hay historia suficiente en un piloto).

Columna adicional de gestión: "Eliminar" (solo visible si el trámite todavía no tiene un diagnóstico enviado, confirmación nativa antes de borrar) y "Archivar" (siempre disponible, reversible, sin confirmación adicional — no borra nada, solo saca al trámite de esta tabla y del índice global). Un enlace "Ver archivados"/"Ver activos" alterna a la lista de trámites archivados, con "Desarchivar" como única acción disponible ahí. Un trámite archivado nunca aparece mezclado con los activos.

### 3. Cuestionario de captura (F1)
Un `Card` por pregunta, `Progress` de avance arriba, lógica de ramificación oculta preguntas que no aplican (ej. si "sin motor de pagos", no pregunta modalidad de pago). Texto de ayuda contextual bajo cada pregunta en lenguaje administrativo, nunca un tecnicismo sin explicar. Botón "Guardar y continuar después" siempre visible — un funcionario de mostrador puede ser interrumpido a media captura.

Cada `Card` incluye, además de la pregunta cerrada, un campo opcional de aclaración en texto libre (`Textarea`, colapsado por defecto bajo un enlace tipo "¿Su situación no encaja en esta opción? Explique aquí") para los casos en que la realidad del trámite no encaje limpiamente en la respuesta cerrada — se guarda siempre como evidencia de apoyo ligada a esa pregunta, nunca reemplaza por sí sola la respuesta cerrada. En la pregunta de mecanismo de identidad/acceso ciudadano, el `RadioGroup` agrega una quinta opción, "Otro, especifique", que despliega el mismo `Textarea` de forma obligatoria; el texto se envía a clasificación (ruta `economico`, ver `docs/TRD.md`) y la interfaz muestra la categoría sugerida en lenguaje llano con dos acciones igual de visibles ("Confirmar" / "Elegir manualmente") — nunca se guarda un valor de la pregunta sin que el funcionario confirme o elija manualmente. Detalle completo del mecanismo, las categorías de clasificación y el sesgo de fallo (nunca bloquea el guardado salvo que quede "Otro" sin resolver) en `entregables/fase-2/asistente-captura-f1.md`.

### 4. Plan de modernización generado (F3 + F9)
Encabezado con el índice actual → objetivo (misma paleta ordinal). Cuerpo: un `Accordion` por brecha, cada uno desplegando paso administrativo/técnico/organizacional, prerrequisitos, costo/tiempo estimado y fuente normativa (estructura acordada en `docs/TRD.md`). Párrafo introductorio en prosa (redactado por LLM, verificado por F9) resume el conjunto — nunca reemplaza la tabla estructurada, la acompaña. Aviso visible si el plan se generó en modo degradado (plantilla determinista, sin LLM disponible) — transparencia, no ocultarlo.

### 5. Panel de seguimiento (F6)
Tabla simple: acción del plan, responsable, fecha objetivo, semáforo (paleta de estado de arriba, con ícono + texto). Sin funcionalidades de gestión de proyectos (sin Gantt, sin dependencias entre tareas) — mandato explícito de producto: "nada de metodologías pesadas".

### 6. Perfil del gobierno
Pantalla dedicada (no un paso de onboarding bloqueante, no una sección dentro del Panel resumen) para las variables de contexto y capacidad institucional del gobierno, capturadas una sola vez por tenant — contrato completo de campos y endpoints en `entregables/fase-2/variables-contexto-institucional.md`. Un `Card` por bloque (contexto / capacidad institucional). Los 4 campos booleanos (`area_tic_existe`, `normativa_local_emitida`, `autoridad_gobernanza_digital`, y la pregunta de gobernanza con su texto condicionado por país) como `RadioGroup` "Sí"/"No", mismo patrón de pregunta cerrada que el cuestionario F1. `conectividad` como `Select` de 3 opciones (`estable`, `intermitente`, `sin_conexion`). `poblacion_total`, `personal_total_gobierno` y `presupuesto_tic_anual` como `Input` numérico. Guardado por campo o por bloque, sin noción de "enviar cuestionario completo" — no hay estado "incompleto" que bloquee nada.

## Accesibilidad

Contraste mínimo AA en todo texto de UI (no solo en gráficos); todo estado (índice, semáforo) con texto además de color; objetivos de toque ≥ 44px para uso en tablet en mostrador; modo oscuro soportado desde el diseño del componente, no como añadido posterior — pero no es prioridad de validación visual sobre el modo claro para el piloto.

## Documentos relacionados

`docs/PRD.md`, `docs/TRD.md`, `docs/stack-tecnologico.md`, `docs/app-flow.md` (navegación entre estas pantallas), `docs/backend-schema.md`, `docs/plan-implementacion.md`.
