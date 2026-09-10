# Runbook — Respaldo (backup) de la base de datos

Guía operativa para quien opera el despliegue (la contraparte técnica designada, `docs/PRD.md` "Fuera de alcance": sin onboarding self-service). No hay ningún script de backup en este repositorio a propósito — el pipeline completo son dos comandos encadenados, documentados aquí en texto plano en vez de vivir en un archivo `.sh` nuevo.

## Requisito previo

El stack ya arriba (`docs/runbook-despliegue.md`), con el servicio `db` corriendo. No se necesita ninguna herramienta adicional al propio `docker compose`.

## Hacer un respaldo

```
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > diagmuni-$(date +%Y%m%d-%H%M%S).sql.gz
```

`$POSTGRES_USER`/`$POSTGRES_DB` deben coincidir con los valores de `.env` (por default, `diagmuni`). Usa ese rol superusuario a propósito, no `diagmuni_app` — `diagmuni_app` queda sujeto a Row-Level Security, y un dump corrido con ese rol saldría filtrado por el `tenant_id` de la sesión en vez de contener todos los gobiernos.

Verificar que el archivo no quedó vacío ni corrupto:

```
gunzip -t diagmuni-20260818-140000.sql.gz && echo "OK"
```

## Programarlo (crontab)

```
0 3 * * * cd /ruta/al/repo && docker compose exec -T db pg_dump -U diagmuni diagmuni | gzip > /ruta/de/respaldos/diagmuni-$(date +\%Y\%m\%d).sql.gz
```

Dos detalles que rompen esto si se copian sin ajustar:

- `cd /ruta/al/repo &&` es obligatorio — cron no hereda el directorio de trabajo de una sesión interactiva, así que sin esto `docker compose` no encuentra el `docker-compose.yml` del proyecto.
- El `%` de `date` debe escaparse como `\%` dentro de una entrada de crontab (crontab le da un significado especial al `%` sin escapar) — sin el escape, el comando falla en silencio.

**Retención** (ejemplo, ajustar según el volumen real de diagnósticos): agregar una línea aparte que borre los respaldos con más de 7 días —

```
0 4 * * * find /ruta/de/respaldos -name 'diagmuni-*.sql.gz' -mtime +7 -delete
```

`[NO VERIFICADO]`: 7 días es un punto de partida razonable, no una cifra medida contra el tamaño real de la base de datos en producción — no hay ningún benchmark de espacio en disco documentado en este repositorio (`docs/runbook-despliegue.md` solo fija un piso de CPU/RAM, no de disco). Ajustar la retención al espacio disponible del servidor antes de confiar en este valor.

## Restaurar un respaldo

**Sin automatizar a propósito** — restaurar sobreescribe todos los gobiernos y usuarios activos del despliegue, sin ninguna confirmación intermedia ni posibilidad de deshacerlo. El comando queda documentado en texto plano, no en un script, para que quien lo ejecute lo revise línea por línea antes de correrlo (mismo criterio que ya usa este proyecto para otras operaciones irreversibles, ej. `docs/plan-implementacion-alta-gobierno.md`, la contraseña de arranque de un funcionario nunca se persiste a un archivo):

```
gunzip -c diagmuni-20260818-140000.sql.gz | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

Antes de correrlo: confirmar que es el archivo correcto, y que de verdad se quiere reemplazar el contenido actual de la base — no hay vuelta atrás una vez que corre.

**Prerrequisito real, no obvio** (verificado 2026-09-10 -- ver "Verificación" abajo):
el rol `diagmuni_app` debe existir en la base destino *antes* de restaurar, o la
restauración termina con una racha de `ERROR: role "diagmuni_app" does not
exist"` (los `GRANT`/`ALTER DEFAULT PRIVILEGES` que trae el dump le apuntan a
ese rol). En el flujo normal (`docker compose up -d db` sobre un volumen ya
inicializado, o uno nuevo -- `backend/db-init/01-app-role.sql` corre solo la
primera vez que el volumen de datos está vacío) esto nunca se nota porque el
rol ya existe para cuando se corre el `psql` de arriba. Sí importa en un
disaster-recovery real (servidor nuevo, volumen de Postgres vacío de verdad):
levantar `db` con `docker compose up -d db` primero (deja que el init script
cree el rol) y restaurar después, nunca restaurar contra un contenedor de
Postgres corrido a mano sin ese init script montado.

### Verificación (2026-09-10)

Ciclo completo probado de punta a punta contra la base real de este
despliegue, restaurando en una instancia de Postgres desechable (nunca sobre
la base viva): `pg_dump` → `gunzip -t` → restaurar en un contenedor limpio con
`db-init/01-app-role.sql` montado → comparar conteos. Resultado: 5 tenants,
27 trámites, 6 usuarios -- idéntico en la base viva y en la restaurada, sin un
solo `ERROR` en el log de restauración una vez resuelto el prerrequisito de
arriba. `[VERIFICADO]` -- primera vez que este ciclo se prueba de verdad
desde que existe este runbook.

## Riesgo a tener presente

El archivo `.sql.gz` que produce este mecanismo queda **sin cifrar** en el disco del servidor — contiene `password_hash` de todos los funcionarios y los datos reales de diagnóstico de cada gobierno. Cifrar el archivo (ej. `gpg`, o cifrado a nivel de disco/volumen) es responsabilidad del operador del despliegue si su política de datos lo exige; este runbook no lo resuelve.

## Qué este runbook NO cubre (alcance futuro, no construido)

- Automatizar la restauración o agregarle verificación/rollback.
- Backups incrementales o point-in-time recovery (WAL archiving) — este mecanismo es un dump completo cada vez, sin nada intermedio.
- Cifrado del archivo de respaldo en reposo.
- Subir el respaldo a almacenamiento externo (ej. S3/GCS) — el comando de arriba solo escribe al disco local del servidor.
