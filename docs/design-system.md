# Sistema de diseño — DiagMuni

Versión 1 · 15 de septiembre de 2026
Reemplaza el enfoque de `docs/ux-brief.md` de "sobrio, gobierno digital" por un mandato distinto de Ricardo: rediseño completo tipo dashboard SaaS moderno (Linear / Notion / Vercel / Stripe Dashboard), adaptado a una app técnica/de monitoreo, sin agregar dependencias nuevas. Este documento es la fuente de verdad de los tokens — si un valor cambia en el código, este archivo se actualiza en el mismo commit (mismo criterio que `docs/ux-brief.md` ya usaba para su paleta).

## 1. Auditoría del estado actual

Contra qué se compara: el código real hoy en `frontend/src/`, no una descripción de memoria.

1. **Los tres componentes que más se repiten (`Button`, `Card`, `Badge`) son shadcn de catálogo sin ninguna decisión propia encima.** `card.tsx` es literalmente `rounded-xl border border-border bg-card p-6` — el ejemplo de la documentación de shadcn, palabra por palabra. `button.tsx` solo tiene 5 variantes genéricas (`default/outline/secondary/ghost/destructive`) sin ninguna que exprese la identidad del producto. Es exactamente el "se ve a un template sin tocar" que describe el brief.
2. **Un solo radio y una sola sombra para absolutamente todo.** `index.css` fija `.rounded-xl` (1rem) y `.rounded-lg` (0.8rem) y dos niveles de sombra (`.shadow-sm` / `.shadow`) — correcto como sistema, pero se aplican IDÉNTICOS a una tarjeta de KPI, una fila de tabla y un modal: no hay jerarquía de "peso visual" entre una superficie de dato principal y una secundaria.
3. **Los estados (semáforo, índice) usan color con criterio, pero el resto de la interfaz no tiene ningún acento propio.** `semaforo.ts`/`madurez.ts` están bien pensados (nunca solo color, siempre ícono+etiqueta), pero fuera de esos dos sistemas, TODA la interfaz vive en escala de grises (`--foreground/--muted-foreground/--atenuado/--border`) — cero personalidad tipográfica o cromática en títulos, botones, tabs, navegación de contenido.
4. **Radix se usa por su comportamiento, nunca por su expresión visual.** `accordion.tsx` solo anima la rotación del chevron (`[&[data-state=open]>svg]:rotate-180`); `tabs.tsx` solo cambia fondo/sombra en el trigger activo, sin transición de entrada del panel; `dropdown-menu.tsx` (no listado arriba, mismo patrón) no usa `data-side`/`data-state` para animar apertura. Ningún componente aprovecha `data-orientation`. Es exactamente el punto 5 del mandato de Ricardo: comportamiento nativo correcto, cero "wow" visual con él.
5. **ECharts (`GraficaTendenciaIndice.tsx`) ya tiene gradiente y tooltip enriquecido** — este es el componente MÁS trabajado del código hoy, no al revés. Lo que le falta: animación de entrada configurada explícitamente (usa el default de ECharts, nunca se afinó `animationDuration`/`animationEasing`), y la leyenda/ejes son tipografía de 10-11px sin ninguna jerarquía con el resto de la tarjeta.
6. **Tipografía: una sola escala, sin peso editorial.** Nada por debajo de `text-xs` (12px) ni una escala de display por encima de `text-4xl` salvo el índice grande — no hay un tratamiento de "esto es un dato hero" vs. "esto es una etiqueta de columna" más allá del tamaño puro; el peso (`font-bold`/`font-semibold`/`font-medium`) se usa de forma inconsistente entre pantallas (compárese `PanelResumen.tsx` y `Seguimiento.tsx`).
7. **Densidad de datos sin herramientas para manejarla:** `Seguimiento.tsx` y la pestaña "Detalle técnico" de `Plan.tsx` ya muestran tablas/acordeones largos con `hover:bg-secondary/50` como único recurso de escaneo — no hay zebra striping, no hay agrupación visual, no hay affordance de densidad (compacto/cómodo).

**Diagnóstico en una frase:** el código es correcto y bien documentado (buena base técnica), pero visualmente es la paleta neutra + shadcn default sin ningún acento, escala o composición que un usuario reconozca como "de este producto" — exactamente "genérico, apagado, sin personalidad".

## 2. Arquitectura de tokens (compartida entre las 3 direcciones)

Las 3 direcciones de la sección 3 comparten esta ARQUITECTURA (nombres de variable, escalas) y difieren en los VALORES de color/superficie — así elegir una no significa reconstruir el sistema de cero.

### Espaciado

Escala de 8 pasos en `rem` (base 4px, como Vercel) — reemplaza el uso ad-hoc actual de `gap-3`/`gap-4`/`gap-5`/`gap-6` sin criterio entre pantallas:

| Token | Valor | Uso |
|---|---|---|
| `--space-1` | 4px | separación entre ícono y su etiqueta |
| `--space-2` | 8px | padding interno de badge/chip |
| `--space-3` | 12px | gap entre campos de un formulario |
| `--space-4` | 16px | padding interno de tarjeta compacta |
| `--space-6` | 24px | padding interno de tarjeta estándar, gap entre tarjetas apiladas |
| `--space-8` | 32px | gap entre secciones de una pantalla |
| `--space-12` | 48px | separación bajo el encabezado de página |
| `--space-16` | 64px | margen superior de página bajo la nav fija |

### Radios

3 pasos, no 2 — para poder diferenciar "chip/badge" de "tarjeta de dato":

| Token | Valor | Uso |
|---|---|---|
| `--radius-sm` | 6px | inputs, badges, chips |
| `--radius-md` | 10px | tarjetas, botones |
| `--radius-lg` | 16px | tarjetas "hero" (KPI principal, franja superior) |

### Sombras (jerarquía de peso, no solo un valor "encendido/apagado")

| Token | Uso |
|---|---|
| `--shadow-flat` | ninguna sombra, solo borde de 1px — filas de tabla, chips |
| `--shadow-card` | elevación estándar de tarjeta (equivalente al `.shadow-sm` actual) |
| `--shadow-hero` | elevación de la pieza principal de la pantalla (índice global, tarjeta destacada) — la única que se permite más pronunciada |

### Estados (reemplaza rojo/amarillo/verde de Tailwind sin editar)

4 roles con nombre semántico propio, cada uno con una variable de texto/borde AA y una de "superficie tenue" para fondos de aviso — igual patrón que ya usa `semaforo.ts`, extendido a 4 roles en vez de 3, y con nombre propio de marca en vez de rojo/amarillo/verde genérico:

| Rol | Cuándo se usa | Reemplaza hoy |
|---|---|---|
| `--estado-exito` | acción completada, diagnóstico enviado | `--semaforo-completado` (se mantiene, mismo valor) |
| `--estado-alerta` | en progreso, plazo próximo a vencer | `--semaforo-en-progreso` (se mantiene) |
| `--estado-critico` | atrasado/bloqueado, error de validación | `--semaforo-atrasado` / `--destructive` (unificar en uno solo — hoy son 2 variables para el mismo significado) |
| `--estado-info` | avisos neutrales (modo degradado del plan, notas del sistema) | hoy no existe — `Plan.tsx` usa `bg-secondary` genérico para el aviso de modo degradado, sin color de rol propio |

Los valores hex exactos de estos 4 roles se definen por dirección (sección 3), no aquí — el semáforo de seguimiento (F6) y la rampa de madurez (0-4) NO cambian de significado ni de regla (siguen siendo ícono+etiqueta siempre, nunca solo color); lo que cambia es su tono exacto para que combine con la superficie de cada dirección.

### Tipografía

Sin fuente nueva (siguen `"Segoe UI", Inter, Roboto, system-ui...`, docs/ux-brief.md ya lo fijó y sigue vigente), pero con una escala de 7 pasos con letter-spacing propio en vez de los tamaños sueltos actuales:

| Token | Tamaño | Peso | Tracking | Uso |
|---|---|---|---|---|
| `--text-display` | 3.5rem (56px) | 800 | -0.03em | cifra del índice global, hero de pantalla |
| `--text-h1` | 1.75rem (28px) | 700 | -0.02em | título de página |
| `--text-h2` | 1.125rem (18px) | 600 | -0.01em | título de tarjeta/sección |
| `--text-body` | 0.9375rem (15px) | 400 | 0 | texto de párrafo, celdas de tabla |
| `--text-body-medium` | 0.9375rem (15px) | 600 | 0 | valor destacado dentro de una fila |
| `--text-label` | 0.75rem (12px) | 700 | 0.08em, mayúsculas | kicker, encabezado de columna |
| `--text-caption` | 0.75rem (12px) | 400 | 0 | ayuda, timestamp, metadato |

### Uso explícito de estados nativos de Radix (aplica a los 4 componentes ya en el repo)

- **`Accordion`** (`data-state="open"|"closed"`): además del chevron actual, el `AccordionContent` anima `grid-template-rows` de `0fr` a `1fr` (con `Radix` ya expone la altura real vía CSS, sin JS ni librería de animación) para una apertura suave, y el `AccordionTrigger` cambia `background-color` en `data-state=open` para marcar cuál brecha está expandida en una lista larga (Plan.tsx, pestaña técnica).
- **`Tabs`** (`data-state="active"|"inactive"`): un indicador deslizante (`::after` con `transform: translateX()` calculado por CSS, no JS) en vez del fondo plano actual de `TabsTrigger` — Radix ya expone qué trigger está activo vía el atributo, la transición es pura CSS.
- **`DropdownMenu`** (`data-side="top"|"bottom"|"left"|"right"`, `data-state="open"|"closed"`): entrada con `transform-origin` calculado desde `data-side` (para que el menú "crezca" desde el punto de anclaje correcto, no desde una esquina fija) + fade/scale de 95%→100% en apertura — hoy no tiene ninguna transición de entrada/salida.
- **`RadioGroup`** (usado en Diagnostico.tsx/GobiernoPerfil.tsx): el indicador interno anima `scale` de 0→1 al marcarse (Radix ya monta/desmonta el indicador vía `data-state`), en vez del cambio instantáneo actual.
- **`Progress`**: ya anima `transform` (correcto), se le suma una sutil animación de "stripes" en movimiento SOLO mientras `value < 100` (para diferenciar "cargando" de "completo al 100% y quieto") — la única animación en loop de todo el sistema, y solo mientras hay una operación real en curso.

### ECharts (aplica a `GraficaTendenciaIndice.tsx` y `GraficaAvanceSeguimiento.tsx`)

- `animationDuration: 700`, `animationEasing: "cubicOut"` explícitos (hoy usan el default de la librería, nunca configurado a propósito).
- Los gradientes ya existen (`hexConAlpha` + `LinearGradient`) — se ajustan los stops de opacidad por dirección, no se rehace la técnica.
- Tooltip: agregar una segunda línea por serie con el delta vs. el punto anterior (hoy el tooltip solo muestra el valor absoluto de cada serie).
- Usar `graphic` de ECharts para una etiqueta de "hoy"/"actualizado hace Ns" anclada dentro del lienzo de la gráfica (ya existe ese texto FUERA de la gráfica en `GraficaTendenciaIndice.tsx`; moverlo dentro con `graphic` la integra visualmente en vez de sentirse una nota aparte).

## 3. Tres direcciones

Las 3 comparten la arquitectura de la sección 2. Difieren en superficie, paleta y peso tipográfico. Mockups visuales en el canvas (ver mensaje aparte) — este documento fija los valores exactos que cada una usaría en código.

### Dirección 1 — "Fría/técnica" (referencia: Linear)

Superficie oscura por defecto (escalera de 4 pasos, sin sombra — la jerarquía la da el paso de superficie, no un shadow): `--canvas: #0a0a0c`, `--surface-1: #131316`, `--surface-2: #1a1a1f`, `--surface-3: #232329`. Texto: `--fg-primario: #f2f2f3` (blanco roto, nunca puro), `--fg-secundario: #a8acb8`, `--fg-terciario: #6b6f79`. Un solo acento de marca — reutiliza el azul ya validado de la rampa de madurez (nivel 2, `#6674d6`) como el "indigo de marca", igual rol que el `#5e6ad2` de Linear. Bordes casi invisibles (`rgba(255,255,255,0.08)`), nunca gruesos.

*Por qué funcionaría:* encaja mejor con "app técnica/de monitoreo" (así se ven las herramientas internas que un funcionario de TI reconocería como "profesionales") y reduce fatiga visual en sesiones largas de captura de datos. *Costo real a declarar:* hoy la app NO tiene interruptor claro/oscuro construido (`index.css` ya lo dice explícitamente) — esta dirección implica construirlo primero, o volver el oscuro el único modo (sin el segundo, más plano para el funcionario en un mostrador con luz de día, dato que sí importa para el usuario real del PRD).

### Dirección 2 — "Cálida/humana" (referencia: Notion + Stripe)

Superficie clara, parte de la paleta actual (`--background: #f1f1ef` ya es un gris cálido, se conserva), tarjetas casi sin borde (`border: 1px solid rgba(0,0,0,0.06)`, apoyadas en espaciado, no en línea) como Stripe. Un acento cálido PROPIO para acción primaria — terracota (`#b3552f` texto/borde, AA sobre blanco) — deliberadamente NO azul, así nunca compite con la rampa de madurez (principio ya validado en `docs/ux-brief.md`, se mantiene). Tipografía más generosa en line-height (1.6 en vez de 1.4) para sensación "menos apretada".

*Por qué funcionaría:* es la que más literalmente responde a "algo happy, con vida, no sombrío" sin tocar el significado del azul del índice — y es la que menos riesgo técnico tiene (extiende la paleta actual en vez de reemplazarla).

### Dirección 3 — "Alto contraste / denso en datos" (referencia: Vercel)

Blanco y negro puros + un solo acento (`#fafafa` fondo, `#171717` texto, cero grises intermedios en superficies — el paso lo da el borde, no un gris de relleno). Tipografía con tracking negativo en encabezados (`-0.02em` a `-0.03em`, como Geist) para un look "de ingeniería". Cero sombras, cero gradientes decorativos en superficies (el gradiente de ECharts se mantiene, es dato, no decoración). Bordes de 1px en TODO (tablas, tarjetas, botones) en vez de sombra.

*Por qué funcionaría:* es la que mejor resuelve "jerarquía clara para datos densos" (Seguimiento, Plan técnico) porque no hay nada decorativo que compita con la tabla/acordeón — y es la más barata de mantener en AA (blanco/negro puro rara vez falla contraste).

## 4. Implementado (paso 4, dirección elegida: "Fría/técnica")

Ricardo eligió la dirección 1 y pidió claro Y oscuro, aplicado a toda la app de una vez — ya implementado en código, no solo mockup:

- **Tokens reales en `frontend/src/index.css`**, ambos temas, revalidados con `validate_palette.js` (toda la paleta pasa AA salvo las excepciones del semáforo ya documentadas en `docs/ux-brief.md`).
- **Interruptor de tema real** (`frontend/src/lib/theme.ts`, `ThemeToggle.tsx`, script bloqueante en `index.html` contra el parpadeo) — antes no existía ninguno.
- **NavBar rediseñado**: deja de ser una barra navy fija, pasa a ser un paso más de la escalera de superficie; el link activo y el logo usan el acento de marca.
- **Logo por gobierno, de verdad**: `GET/PUT /api/gobierno/logo` (construido por la sesión de backend en paralelo, migración `0021_tenant_logo.py`) — el frontend lo consume vía `lib/logoGobiernoApi.ts` + `useLogoGobiernoUrl` (fetch con Authorization, blob, sin exponerlo nunca en el JWT). Se muestra junto al nombre en NavBar y como marca de agua (escala de grises, velo oscuro) en `HeroIndiceGlobal.tsx`. Subida real desde "Perfil del gobierno" (`TarjetaLogoGobierno`, solo `admin_gobierno`).
- **4 roles de estado** aplicados: reemplazan `amber-500`/`emerald-500` de Tailwind sin editar en `Plan.tsx` y `ComparadorPlan.tsx`.
- **Radix con estado visual real**: `Accordion` anima por altura real (`--radix-accordion-content-height`) y resalta el ítem abierto; `DropdownMenu` entra/sale con `transform-origin` desde `data-side` (`--radix-popper-transform-origin`); `RadioGroup` anima el indicador al marcar; `Progress` tiene la única animación en loop del sistema, y solo mientras `value < 100`.
- **ECharts**: `animationDuration`/`animationEasing` explícitos y delta vs. punto anterior en el tooltip de `GraficaTendenciaIndice.tsx`.
- Verificado: `tsc`, `eslint`, `vitest` (14/14) y `vite build` limpios; `validate_palette.js` en verde.

## 5. Pendiente / no cubierto en esta pasada

- **`graphic` de ECharts** para anclar el texto "actualizado hace Ns" dentro del lienzo — quedó fuera por tiempo, sigue como texto debajo de la gráfica.
- **Indicador de Tabs verdaderamente deslizante** (medido por posición, no solo transición de color/fondo) — se simplificó a una transición de color/fondo por `data-state`, más barata y sin JS de medición, pero no es el "sliding pill" pixel-perfecto que el plan original describía.
- **Revisión visual pantalla por pantalla** de Diagnostico.tsx/Seguimiento.tsx/AdminUsuarios.tsx/AdminSaludIA.tsx/Perfil.tsx: heredan los tokens nuevos vía `Button`/`Card`/`Badge`/`Input` (ya sin ningún color de Tailwind sin editar, confirmado por búsqueda en todo `src/`), pero no se revisó cada una al detalle con capturas.
- ~~Prueba end-to-end de la subida de logo con el archivo real de Cuajimalpa~~ — **cerrado**: verificado contra nginx real (tenant de prueba `qa-logo-test`) con el archivo real. `PUT` → 204, `GET` → 200 `image/jpeg`, bytes idénticos al original. Ciclo completo funcionando con datos reales, no solo mocks.
