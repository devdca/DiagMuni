# DiagMuni

Plataforma open source de diagnóstico y modelado de la modernización municipal, del Laboratorio de Innovación Pública del INAP.

DiagMuni permite a un gobierno local (municipio en México, intendencia en Uruguay) autodiagnosticar su nivel de madurez digital trámite por trámite y recibir un plan de modernización a la medida: tecnología a adoptar, inversión estimada, personal y capacitación requeridos.

Principio rector: **motor determinista primero, IA después**. El índice de madurez y las reglas normativas son código puro, testeable y reproducible; los modelos de lenguaje solo redactan el plan en lenguaje natural, clasifican texto libre y asisten la captura.

Proyecto desarrollado para el Eje 1 (Atención Ciudadana) de **GovTech Connect** (BID Lab / Red de Innovación Local), con un piloto de código abierto previsto en una ciudad de la coalición CIIAR Uruguay.

## Estado

En desarrollo activo — sin release todavía. Motor determinista, modelo de datos y API REST del backend funcionan de punta a punta (ver `backend/`), con capa de IA (fallback Claude → Claude respaldo → local/Ollama → plantilla) probada contra Ollama real. Las pantallas del frontend (login, panel de resumen, diagnóstico, plan y su comparador, seguimiento, perfil del gobierno, perfil propio y dos vistas de administración) ya existen; el camino principal está cubierto por tests E2E (Playwright) contra un stack Docker real y tests unitarios (Vitest + Testing Library), con lint propio (ESLint) en cada PR.

Soporta los tres órdenes de gobierno (`nivel_gobierno`, reglas y factibilidad por nivel) e integración con INEGI (población, sincronización, bitácora de correcciones de la IA). Cobertura de backend medida en 89%, con Postgres real en CI, y ciclo backup→restore probado de punta a punta. Auditoría de seguridad cerrada (hallazgos H-01 a H-13, incluyendo un prompt injection y un bypass de rate limit encontrados con PentAGI), más escaneo de CVEs conocidas en cada PR (pip-audit, npm audit) y gobernanza OSS básica (`CODEOWNERS`, `CODE_OF_CONDUCT.md`, `SECURITY.md`).

**Ciclo 2026 de GovTech Connect:** el proyecto no se postuló a la convocatoria 2026, cuyo cierre fue el 25 de agosto de 2026. El repositorio queda como activo público, disponible para una siguiente ventana de la convocatoria o para cualquier gobierno que quiera adoptarlo por su cuenta: nada de lo que hay acá depende de esa postulación para usarse.

## Cómo correr el proyecto

```
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head
```

Guía paso a paso, con verificación de que quedó arriba y solución a los errores más comunes, en `docs/runbook-despliegue.md`. Alta del primer gobierno (tenant + usuario) en `docs/runbook-alta-gobierno.md`.

Documentación técnica completa en `docs/` (producto, arquitectura, esquema de datos, flujo de la aplicación) y `entregables/` (catálogo normativo del motor de diagnóstico, teoría de cambio).

## Licencia

[Apache License 2.0](LICENSE) — ver también [NOTICE](NOTICE). Toda dependencia debe tener licencia compatible (MIT, BSD, Apache); GPL solo como servicio independiente sin linking de código; AGPL nunca como dependencia integrada.

## Transferencia de capacidades

El código, los datos y el diagnóstico generado pertenecen al gobierno local que los produce. DiagMuni no genera dependencia de su implementador original: despliegue por contenedores, documentación técnica desde el primer commit, sin componentes privativos.
