---
name: Reporte de bug
about: Algo no funciona como debería
title: ""
labels: bug
---

**Describe el bug**
Qué esperabas que pasara, y qué pasó en realidad.

**Cómo reproducirlo**
Pasos exactos para reproducirlo:
1. ...
2. ...

**Entorno**
- Commit/versión: `git rev-parse HEAD` o el tag si corriste un release.
- ¿Local (`docker compose up`) o un despliegue real?
- Navegador (si es un bug de frontend).

**Logs/capturas**
`docker compose logs backend` (o el servicio que corresponda) suele tener el
detalle real -- pégalo aquí si aplica.

**¿Es un hallazgo de seguridad?**
Si esto expone datos de un gobierno, credenciales, o permite saltarse
autenticación/autorización -- **no lo reportes aquí**, sigue `SECURITY.md`.
