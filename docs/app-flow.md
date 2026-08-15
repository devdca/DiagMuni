# App Flow — DiagMuni

Versión 1 · 21 de julio de 2026
Cuarto de los 6 documentos de blueprint de producto. Cubre todas las páginas de la aplicación, la navegación entre ellas, el recorrido del usuario y qué pasa exactamente cuando hace clic en cada botón — para que la implementación no invente rutas ni transiciones no especificadas. Construido sobre las 5 pantallas de `docs/ux-brief.md` y las funcionalidades F1-F9 de `docs/PRD.md`.

## Mapa de rutas (frontend)

| Ruta | Pantalla | Acceso |
|---|---|---|
| `/login` | Selección de gobierno e ingreso | Sin sesión |
| `/` | Panel resumen | Requiere sesión |
| `/tramites/:tramiteId/diagnostico` | Cuestionario de captura (F1) | Requiere sesión |
| `/tramites/:tramiteId/plan` | Plan de modernización (F3 + F9) | Requiere sesión, requiere diagnóstico completo |
| `/seguimiento` | Panel de seguimiento (F6) | Requiere sesión |
| `/gobierno/perfil` | Perfil del gobierno (variables de contexto y capacidad institucional) | Requiere sesión |

Nav superior fija en todas las pantallas con sesión: nombre del gobierno local (tenant, texto plano — nunca un selector visible, ver `docs/ux-brief.md` pantalla 1), enlaces "Inicio", "Perfil del gobierno" y "Seguimiento", botón "Cerrar sesión". Sin sidebar — 6 rutas no lo justifican.

## Diagrama de navegación

```mermaid
flowchart TD
    A[/login] -->|credenciales válidas| B[/ - Panel resumen]
    B -->|clic en trámite sin iniciar o en progreso| C[/tramites/:id/diagnostico]
    B -->|clic en trámite con plan listo| D[/tramites/:id/plan]
    B -->|clic en "Seguimiento" en nav| E[/seguimiento]
    B -->|clic en "Perfil del gobierno" en nav| G[/gobierno/perfil]
    C -->|Guardar y continuar después| B
    C -->|Enviar diagnóstico completo| F{Job: generar plan}
    F -->|plan listo o degradado| D
    D -->|clic en "Seguimiento" en nav| E
    E -->|clic en acción| D
    D -->|clic en "Inicio" en nav| B
    E -->|clic en "Inicio" en nav| B
    G -->|clic en "Inicio" en nav| B
    G -->|clic en "Seguimiento" en nav| E
    B -->|Cerrar sesión| A
    C -->|Cerrar sesión| A
    D -->|Cerrar sesión| A
    E -->|Cerrar sesión| A
    G -->|Cerrar sesión| A
```

## Estados del trámite (máquina de estados)

| Estado | Significado | Transición de entrada | Transición de salida |
|---|---|---|---|
| `sin_iniciar` | Trámite catalogado, cuestionario no abierto | Alta del trámite en el catálogo | Funcionario abre el cuestionario → `en_progreso` |
| `en_progreso` | Cuestionario parcialmente respondido | "Guardar y continuar después" | Funcionario reabre y completa → dispara cálculo de índice |
| `diagnosticado` | Cuestionario completo, índice calculado (F2, síncrono, determinista) | Envío del cuestionario completo | Se dispara automáticamente el job de generación de plan (F3) — nunca requiere una acción manual adicional del funcionario |
| `generando_plan` | Job `pending`/`running` (ver `docs/TRD.md`, ciclo de vida del job) | Fin de `diagnosticado` | Job termina `done` → `plan_listo`; si falla dos veces → `plan_listo` en modo degradado (plantilla determinista) |
| `plan_listo` | Plan visible en `/tramites/:id/plan`, con o sin aviso de modo degradado | Job completado | El funcionario puede reabrir el diagnóstico para corregir una respuesta → vuelve a `en_progreso`, y el plan anterior queda marcado como versión anterior (nunca se borra, ver versionado en `docs/TRD.md`) |

No existe un estado "plan aprobado" ni flujo de aprobación — el plan es informativo para el funcionario, no requiere firma dentro de la plataforma (eso es papel del gobierno, fuera de alcance del MVP).

## Flujo principal, paso a paso

1. **Ingreso**: el funcionario entra a `/login`, captura credenciales. Si fallan: mensaje en lenguaje llano, sin código de error técnico (ver `docs/ux-brief.md`). Si el JWT expira en cualquier pantalla posterior, se redirige a `/login` preservando la ruta destino para volver ahí tras reingresar.
2. **Panel resumen (`/`)**: ve el índice global y la lista de trámites catalogados de su gobierno, cada uno con su estado (badge de la máquina de estados de arriba, en la paleta ordinal si ya tiene índice calculado).
3. **Diagnóstico (`/tramites/:id/diagnostico`)**: responde el cuestionario con ramificación (F1). Puede salir en cualquier momento con "Guardar y continuar después" — el estado queda `en_progreso`, nada se pierde. Al enviar completo, ve una pantalla de espera breve (el índice F2 es síncrono y rápido — código puro) y es redirigido automáticamente a `/tramites/:id/plan` una vez el job de plan termina; si el job tarda, ve un indicador de "generando plan" sin bloquear el resto de la navegación (puede irse al panel resumen y volver después).
4. **Plan (`/tramites/:id/plan`)**: ve el índice actual→objetivo, el desglose por brecha (acordeón), y si aplica, el aviso de modo degradado. Desde aquí puede ir a `/seguimiento` para dar seguimiento a las acciones de ese plan.
5. **Seguimiento (`/seguimiento`)**: tabla de todas las acciones de todos los trámites con plan generado, semáforo por acción. Clic en una fila lleva de vuelta a `/tramites/:id/plan` para ver el detalle completo de esa acción (nunca edita el semáforo desde ahí sin contexto — mandato de producto de "sin metodologías pesadas", el cambio de estado del semáforo es una acción simple en la misma tabla, no una pantalla aparte).

## Casos especiales

- **Diagnóstico corregido después de tener plan**: reabrir y modificar respuestas regresa el trámite a `en_progreso`; al reenviar, se genera una nueva versión del plan (versionado del motor, `docs/TRD.md`) — la versión anterior no se pierde, pero la vista `/tramites/:id/plan` siempre muestra la más reciente.
- **Sin ninguna API de LLM disponible**: el job de plan nunca falla de forma visible al funcionario — degrada a plantilla determinista (ver `docs/stack-tecnologico.md`, capa IA) y `/tramites/:id/plan` muestra el aviso correspondiente, nunca un error genérico.
- **Trámite sin brechas** (índice ya en 4 en todas las variables): el plan generado indica explícitamente que no hay acciones pendientes — no se fuerza una recomendación donde no hay brecha real.
- **Multi-tenant**: la nav nunca ofrece cambiar de gobierno — un funcionario pertenece a un tenant (ver `docs/ux-brief.md`); si en el futuro un usuario necesita acceso a más de uno, es un caso fuera del alcance del MVP, no contemplado en este flujo.
- **Eliminar/archivar un trámite** (panel resumen, `docs/ux-brief.md`): un trámite sin diagnóstico enviado puede borrarse físicamente; uno ya diagnosticado solo puede archivarse (reversible, oculta del panel/seguimiento sin perder su historial ni sus planes versionados) — ver `docs/backend-schema.md`, tabla `tramite`, para el guard exacto.

## Documentos relacionados

`docs/PRD.md`, `docs/TRD.md`, `docs/ux-brief.md`, `docs/backend-schema.md` (modela los estados de arriba como columnas/enums reales), `docs/plan-implementacion.md`.
