# Brief de diseño UI/UX — DiagMuni

Versión 1 · 21 de julio de 2026
Tercero de los 6 documentos de blueprint de producto. Cubre apariencia y experiencia — paleta, tipografía, componentes, y cómo debería verse cada pantalla — para que la implementación no sea arbitraria. No repite decisiones ya cerradas: componentes en shadcn/ui (Radix + Tailwind, MIT, código copiado al repo — ver `docs/stack-tecnologico.md`), usuario objetivo el funcionario municipal sin perfil técnico (ver `docs/PRD.md`).

## Principios de diseño

1. **Sin jerga técnica, en ningún estado de la interfaz.** El usuario es un funcionario de mostrador, no un tecnólogo (ver `docs/PRD.md`, Usuario objetivo). Ningún texto de UI usa vocabulario de sistemas ("endpoint", "token", "payload") ni normativo sin explicar ("LNETB", "RLS") — el lenguaje es administrativo llano, en español, sin distinguir MX/UY salvo donde la variable realmente lo exige (firma-e, identidad).
2. **Tono institucional, no de producto de consumo.** DiagMuni es una herramienta de gobierno, del Laboratorio de Innovación Pública del INAP — sobrio, confiable, sin animaciones decorativas, sin lenguaje de marketing ("¡genial!", "¡tu plan está listo!"). Serio pero no burocrático: claro y directo.
3. **Debe funcionar igual en un municipio de 3 funcionarios de mostrador que en una intendencia con área TIC** — sin asumir hardware moderno ni gran ancho de banda; sin asumir alfabetización digital alta.
4. **La marca visual del Laboratorio INAP está pendiente** (no se ha definido logo/colores institucionales en este proyecto) — mientras tanto, se usa la paleta neutral validada de esta sección; sustituir cuando exista identidad de marca oficial, sin tocar la estructura de componentes.
5. **Sobrio no es plano.** La primera versión de la paleta (gris/crema con azul marino apagado) se descartó tras revisión de diseño por leerse genérica y sin pulir — sobrio e institucional (principio 2) no significa bajo contraste ni un solo acento débil. Una segunda versión ("Índigo confiado") corrigió eso, pero puso el mismo índigo en navegación, botones, foco Y en la rampa del índice de madurez a la vez — se leía "todo azul", sin jerarquía entre lo accionable y el dato. La paleta vigente ("Tinta neutra", sección "Paleta") separa ambos roles: la acción/navegación es tinta casi-negra (casi-blanca en oscuro) y el azul de la rampa del índice, ya validado, queda como el único color con significado propio de toda la interfaz — sigue habiendo separación real entre superficies, bordes visibles y contraste intencional, solo que ya no compiten dos sistemas de color por la misma atención.

## Tipografía

Fuente del sistema únicamente: `system-ui, -apple-system, "Segoe UI", sans-serif` — sin fuente de despliegue ni serif, en ningún lugar, incluida la cifra grande del índice de madurez. Cifras que deben alinearse en columna (tablas de seguimiento, listados de trámites) usan `font-variant-numeric: tabular-nums`; el resto, proporcional.

## Paleta — validada, no elegida a ojo

"Tinta neutra": gris verdadero, sin sesgo de color (principio "elegir el neutro, no heredarlo" — antes tenía sesgo azul, que terminaba filtrándose a todo), con la acción/navegación en tinta casi-negra (casi-blanca en oscuro) sobre tarjetas blancas con separación real del fondo. El único color con significado propio en toda la interfaz es el azul de la rampa del índice de madurez (sección siguiente) — deliberadamente no se reutiliza en ningún otro lugar. Revalidar con `frontend/scripts/validate_palette.js` si cambia. Fuente de verdad: `frontend/src/index.css` — esta tabla la documenta, no al revés; si un valor futuro cambia, el commit que lo cambia también actualiza esta tabla.

| Rol | Claro | Oscuro |
|---|---|---|
| Superficie de página | `#f1f1ef` | `#121212` |
| Superficie de tarjeta/panel | `#ffffff` | `#1c1c1a` |
| Texto primario | `#161614` | `#f5f4f0` |
| Texto secundario | `#504f4a` | `#c7c5be` |
| Texto atenuado (ayudas, placeholders) | `#4a4945` | `#8f8d86` |
| Línea divisoria | `#75746d` | `#727169` |
| Acción primaria (fondo / texto) | `#202020` / `#f7f7f5` | `#f2f1ec` / `#121212` |
| Acción secundaria (fondo / texto) | `#e6e5e0` / `#161614` | `#242320` / `#f5f4f0` |
| Destructivo (fondo / texto) | `#ad2a24` / `#fff5f4` | `#e8635c` / `#280604` |

Nota histórica: la primera versión de esta tabla (crema/beige con azul marino, `#f4f3ee`/`#243447`) generaba AA real pero se abandonó por lectura genérica; la segunda ("Índigo confiado", `#eceef5`/`#2b3a9e`) resolvió eso pero puso el mismo índigo en acción, navegación y rampa del índice a la vez — ver principio 5 arriba. Ninguna de las dos era un problema de contraste; ambos cambios fueron de jerarquía y significado del color, no de accesibilidad.

Junto con esta paleta se retiraron los gradientes decorativos de fondo, el glassmorphism generalizado en tarjetas/nav y el `translateY` de hover que tenía la versión anterior — no comunicaban estado y contradecían el principio 2 ("sin animaciones decorativas"). La única superficie que conserva un tratamiento glass es el login (pantalla 1, deliberado y opaco, no transparente — ver esa sección).

### Índice de madurez (0-4) — rampa ordinal, un solo hue, nunca semáforo de colores dispares

El índice **no** se pinta con colores categóricos distintos por nivel (rojo→verde) — es una magnitud ordenada, no un estado bueno/malo por sí sola (un nivel 1 no es "un error", es un punto de partida). Usa la rampa secuencial índigo, 5 pasos discretos, con **dos variantes por nivel** (`frontend/src/lib/madurez.ts`) — nunca la misma para los dos usos:

| Nivel | Descripción | Decorativo (`hexClaro`, piso 2:1, solo swatch/punto `aria-hidden`) | Texto/borde (`varTexto`, AA 4.5:1, claro) | Texto/borde (`varTexto`, AA 4.5:1, oscuro) |
|---|---|---|---|---|
| 0 | Presencial en papel | `#9ea8e5` | `#2d3ea9` | `#cad0f6` |
| 1 | Informativo | `#8f9be3` | `#253393` | `#b1baf1` |
| 2 | Transaccional parcial | `#6674d6` | `#1c297d` | `#98a3eb` |
| 3 | Transaccional completo | `#4152c4` | `#141e61` | `#808de5` |
| 4 | Proactivo e interoperable | `#28349e` | `#0b1341` | `#7583e1` |

`hexClaro` **nunca** se usa como color de texto ni de borde — solo alcanza un piso de 2:1, insuficiente para AA. Cuando el nivel se pinta como texto o borde (cifra grande del índice, borde/texto del `Badge` de índice), siempre se usa `varTexto`, que ya es la variable CSS theme-aware (`--madurez-nivel-N-texto` en `frontend/src/index.css`, con valores propios bajo `.dark` — reutilizar el hex claro en modo oscuro rompía AA en varios niveles). Revalidar ambas variantes con `node scripts/validate_palette.js --ordinal` (agregar `--mode dark` o `--mode light` para uno solo) cada vez que se toquen estos hex. Cada nivel siempre lleva **número + etiqueta de texto** ("2 — Transaccional parcial"), nunca solo el color — el color refuerza, no reemplaza, la lectura.

### Semáforo de seguimiento (F6) — paleta de estado, fija, nunca reutilizada como color de serie

Solo 3 estados para mantener el panel "simple" (mandato de producto) — se reserva el 4º rol de la paleta de estado por si un futuro rediseño necesita distinguir "atrasado" de "bloqueado". Theme-aware por variable CSS (`frontend/src/lib/semaforo.ts`), no hex directo:

| Estado | Rol | Hex claro | Hex oscuro |
|---|---|---|---|
| Completado | good | `#0d770d` | `#4dcb4d` |
| En progreso / a tiempo | warning | `#fab219` | `#fab219` |
| Atrasado o bloqueado | critical | `#d03b3b` | `#d03b3b` |

Regla dura: todo estado del semáforo lleva **ícono + etiqueta de texto**, nunca solo el punto de color. "Completado" cumple AA 4.5:1 en ambos modos (por eso tiene un valor propio por modo); "en progreso" y "atrasado" quedan como excepción documentada — mismo hex en los dos modos, caen bajo el piso de contraste por diseño de la paleta, así que el color solo no basta para transmitir el estado.

## Componentes (shadcn/ui — Radix + Tailwind)

Reutilizar los componentes ya incluidos en shadcn/ui sin construir variantes propias salvo que el catálogo no cubra el caso: `Form` + `Input`/`Select`/`RadioGroup` (cuestionario F1), `Textarea` (cuestionario F1 — campo opcional de aclaración en texto libre adjunto a cada pregunta, y descripción obligatoria al elegir "Otro, especifique" en la pregunta de mecanismo de identidad; ver `entregables/fase-2/asistente-captura-f1.md`), `Table` (listado de trámites, panel de seguimiento), `Card` (resumen de índice, resumen de acción del plan), `Badge` (nivel de índice, estado de semáforo — nunca badge de color puro, siempre con texto), `Progress` (avance del cuestionario), `Accordion` (desglose de cada acción del plan: paso administrativo/técnico/organizacional). Sin componentes de terceros adicionales — shadcn/ui ya es suficiente para el alcance del MVP.

## Pantallas principales

### 1. Selección de gobierno (tenant) e ingreso
Pantalla mínima: campo "Clave del gobierno" (texto corto y legible, nunca un identificador técnico) que el funcionario escribe para identificar a su gobierno local; al resolverse contra el backend, se muestra el nombre del gobierno como confirmación antes de revelar los campos de correo y contraseña (o un selector si el funcionario tiene acceso a más de un gobierno — poco común en el MVP). Sin branding de terceros, sin distractores. Mensaje de error en lenguaje llano tanto si la clave no corresponde a ningún gobierno como si la contraseña no coincide ("La contraseña no coincide", nunca un código de error técnico). Mecanismo completo de identificación (columna `tenant.clave`, endpoint público de resolución, y cómo se conecta con `POST /api/auth/login`) en `entregables/fase-2/identificacion-gobierno-login.md`.

Única pantalla de toda la app con imagen de fondo (`frontend/public/branding/login-fondo.png`, imagen propia) — momento de bienvenida antes de entrar, no una superficie de trabajo; el resto de las pantallas se queda en superficie plana (sección "Paleta"). La imagen lleva un velo neutro oscuro (no azul, para no reintroducir "todo azul" en la puerta de entrada) y la tarjeta de login es glassmorphism **deliberadamente opaco, no transparente** (`--card` al ~92% + blur) — se lee como vidrio sobre la foto sin depender de lo que haya detrás para mantener el contraste AA ya validado de `--card`.

### 2. Panel resumen
Tarjeta superior con el índice de madurez global (cifra grande + etiqueta, paleta ordinal de arriba), fecha de último diagnóstico y una gráfica de tendencia apilada: cuántos trámites activos hay en cada nivel de la rampa (0-4) en el tiempo, área por nivel con los mismos 5 colores ya validados de esa rampa (`frontend/src/lib/madurez.ts`) — nunca colores nuevos ni series inventadas para "verse más llena". Debajo, tabla de trámites catalogados con su índice individual (`Badge`) y acceso a "continuar diagnóstico" o "ver plan".

La tendencia es dato real, no una serie de tiempo regular ni una animación: cada punto (el promedio global Y la distribución por nivel) se recalcula en el instante exacto de un envío o corrección de diagnóstico (`backend/app/aplicacion/historial_indice_global.py`, migración 0015 ampliada por la 0017 — tabla append-only, RLS por tenant igual que `evento_historial`). Con menos de 2 puntos se muestra un texto en vez de dibujar algo que parezca dato sin serlo. `GET /api/tramites/indice-global/historial`, refrescado cada 30s (`refetchInterval`, no un stream) para que dos funcionarios viendo el panel al mismo tiempo vean el punto nuevo sin recargar. Construida con ECharts (línea/área apilada, tooltip real, exportar como imagen) en vez de SVG a mano.

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
