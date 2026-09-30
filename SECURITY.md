# Política de seguridad

DiagMuni es software para gobiernos locales — trata cualquier hallazgo de
seguridad con la seriedad correspondiente. Gracias por reportarlo de forma
responsable.

## Cómo reportar una vulnerabilidad

**No abras un issue público.** Escribe directamente a:

**analista.tecnico@fibroptica.com.mx**

Incluye, en la medida de lo posible:

- Descripción del problema y su impacto (qué se puede hacer, sobre qué datos).
- Pasos para reproducirlo, o una prueba de concepto.
- Versión/commit exacto contra el que se probó.
- Tu información de contacto, para poder dar seguimiento y acreditarte si lo
  autorizas.

## Qué esperar

Somos un equipo pequeño (ver `CODEOWNERS`) — sin un SLA formal todavía, pero el
compromiso es:

1. Confirmar recepción en un plazo razonable.
2. Investigar y validar el hallazgo.
3. Avisarte cuando el fix esté listo, antes de cualquier divulgación pública.
4. Acreditar el reporte (si así lo autorizas) en el changelog del fix.

## Alcance

Aplica a este repositorio (backend, frontend, infraestructura en
`docker-compose*.yml`/`nginx/`). Un despliegue de terceros que use DiagMuni
pero con su propia configuración, secretos o infraestructura es
responsabilidad de quien lo opera — reporta ahí el hallazgo también si aplica
a esa instancia específica, pero repórtalo aquí si el problema está en el
código o la configuración de referencia del proyecto.

## Historial de auditorías

Este proyecto ya pasó por rondas de auditoría externa (PentAGI, Strix) con
hallazgos remediados — ver el historial de commits de la rama de parches de
seguridad para el detalle de cada corrección. No se publica un changelog de
seguridad separado todavía (ver `CHANGELOG.md` para el historial general de
versiones una vez que exista el primer release).

Además de las auditorías puntuales, cada pull request corre un escaneo
automatizado de CVEs conocidos en las dependencias (`pip-audit` en el backend,
`npm audit` en el frontend) — no reemplaza una auditoría manual, pero evita
que una vulnerabilidad ya conocida se cuele sin que nadie la note.
