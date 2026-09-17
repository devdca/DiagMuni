# Runbook — Respaldo (backup) de la base de datos

Guía operativa para quien opera el despliegue (la contraparte técnica designada, `docs/PRD.md` "Fuera de alcance": sin onboarding self-service). No hay ningún script de backup en este repositorio a propósito — el pipeline completo son dos comandos encadenados, documentados aquí en texto plano en vez de vivir en un archivo `.sh` nuevo.

## Requisito previo

El stack ya arriba (`docs/runbook-despliegue.md`), con el servicio `db` corriendo. Además de `docker compose`, este runbook ahora requiere `gpg` (GNU Privacy Guard) instalado en el servidor que genera el backup -- viene preinstalado en la mayoría de las distribuciones Linux server; si no, `apt install gnupg` / `dnf install gnupg2`.

### Generar el par de claves (una sola vez, antes del primer backup cifrado)

**`[PENDIENTE -- no ejecutado todavía]`**: el mecanismo de cifrado de este runbook está documentado y listo, pero **no protege nada hasta que exista una clave real**. Quien opere el despliegue debe decidir primero quién va a resguardar la clave *privada* (la única forma de abrir un backup ya cifrado) -- perderla vuelve irrecuperables todos los backups cifrados con ella, así que es una decisión operativa real, no solo técnica.

Generar el par (en tu propia máquina, **nunca en el servidor de producción** -- la privada no debe tocar la misma máquina que va a estar cifrando con la pública):

```
gpg --batch --full-generate-key <<'EOF'
%no-protection
Key-Type: RSA
Key-Length: 4096
Name-Real: DiagMuni Backups
Name-Email: backups@TU-DOMINIO-REAL
Expire-Date: 0
%commit
EOF
```

Reemplazar `Name-Email` por algo real (no tiene que recibir correo, solo identifica la clave). `%no-protection` evita pedir una contraseña a la clave -- si prefieres proteger la privada con una, quita esa línea. `Expire-Date: 0` = sin vencimiento; ajustar si la política de rotación de claves del operador exige uno.

Exportar la clave **pública** (esta sí va al servidor, no es secreta) y subirla:

```
gpg --export --armor "DiagMuni Backups" > diagmuni-backups-pub.asc
scp diagmuni-backups-pub.asc servidor:/ruta/segura/
ssh servidor 'gpg --import /ruta/segura/diagmuni-backups-pub.asc'
```

La clave **privada** (`gpg --export-secret-keys --armor "DiagMuni Backups"`) se resguarda donde decida el operador (gestor de contraseñas del equipo, USB cifrado offline, etc.) -- fuera de alcance de este runbook, es la decisión pendiente de arriba.

`GPG_RECIPIENT` en los comandos de abajo es el `Name-Email` que uses arriba, o el fingerprint de la clave (`gpg --fingerprint`).

## Hacer un respaldo

```
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip | gpg --encrypt --recipient "$GPG_RECIPIENT" --trust-model always -o diagmuni-$(date +%Y%m%d-%H%M%S).sql.gz.gpg
```

`$POSTGRES_USER`/`$POSTGRES_DB` deben coincidir con los valores de `.env` (por default, `diagmuni`). Usa ese rol superusuario a propósito, no `diagmuni_app` — `diagmuni_app` queda sujeto a Row-Level Security, y un dump corrido con ese rol saldría filtrado por el `tenant_id` de la sesión en vez de contener todos los gobiernos.

`--trust-model always`: sin esto, `gpg` puede negarse a cifrar contra una clave que el llavero local no marcó como "de confianza" explícitamente (un paso extra de gestión de confianza que no aporta nada aquí -- la clave pública se importó a propósito en el paso anterior, ya se confía en ella por diseño).

**Verificar que el archivo no quedó vacío ni corrupto** -- limitado, a propósito: sin la clave *privada* en este servidor (que es justo el punto de cifrar así) no se puede verificar el contenido descifrado, solo que `gpg` terminó sin error y el archivo tiene un tamaño razonable:

```
gpg --list-packets diagmuni-20260818-140000.sql.gz.gpg > /dev/null && echo "OK (formato válido, contenido sin verificar -- ver nota arriba)"
```

## Programarlo (crontab)

```
0 3 * * * cd /ruta/al/repo && docker compose exec -T db pg_dump -U diagmuni diagmuni | gzip | gpg --encrypt --recipient "$GPG_RECIPIENT" --trust-model always -o /ruta/de/respaldos/diagmuni-$(date +\%Y\%m\%d).sql.gz.gpg
```

`$GPG_RECIPIENT` debe estar definida en el entorno de quien programa el cron (ej. en `/etc/environment`, o resuelta inline reemplazando la variable por el valor real) -- cron no hereda el entorno interactivo de una sesión de shell.

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
gpg --decrypt diagmuni-20260818-140000.sql.gz.gpg | gunzip -c | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

`gpg --decrypt` necesita la clave **privada** importada en la máquina donde se corre este comando -- normalmente NO es el servidor de producción (esa es justo la protección: el servidor que respalda no puede leer sus propios backups). En la práctica, esto significa restaurar desde la máquina de quien resguarda la clave privada, o importarla temporalmente donde se vaya a restaurar y borrarla del llavero después.

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
desde que existe este runbook. **Nota (2026-09-14): esta verificación es del
ciclo original sin cifrar.** El paso de `gpg --encrypt`/`--decrypt` se agregó
después -- la sintaxis del comando sí está `[VERIFICADO]` (probada de punta a
punta con una clave GPG desechable: comprimir → cifrar → descifrar →
descomprimir devuelve el contenido idéntico), pero **no contra la clave real
de producción**, porque todavía no existe ninguna (ver "Generar el par de
claves" arriba). Repetir el ciclo completo de restauración (no solo el
cifrado) con la clave real antes de confiar en este flujo para un despliegue
con datos de gobiernos reales.

## Riesgo a tener presente

**`[PARCIALMENTE MITIGADO -- mecanismo listo, sin activar]`**: el mecanismo de cifrado (`gpg`, arriba) ya está documentado y listo para usarse, pero **el riesgo real sigue vigente hoy** porque no existe todavía ninguna clave generada ni una decisión tomada sobre quién resguarda la privada (ver "Generar el par de claves"). Hasta que eso pase, cualquier backup que se genere con el comando viejo (sin `| gpg --encrypt`) sigue quedando **sin cifrar** en el disco del servidor — con `password_hash` de todos los funcionarios y los datos reales de diagnóstico de cada gobierno. Este es el hallazgo que hay que cerrar antes de un despliegue real con datos de gobiernos: generar la clave, decidir su custodia, y adoptar el comando cifrado de este runbook como el único que se usa de aquí en adelante.

## Qué este runbook NO cubre (alcance futuro, no construido)

- Automatizar la restauración o agregarle verificación/rollback.
- Backups incrementales o point-in-time recovery (WAL archiving) — este mecanismo es un dump completo cada vez, sin nada intermedio.
- Generar la clave GPG real y decidir su custodia (ver "Generar el par de claves" -- es lo único que falta para que el cifrado esté realmente activo, no solo documentado).
- Rotación de la clave GPG si se compromete o si la política de seguridad del operador la exige periódicamente.
- Subir el respaldo a almacenamiento externo (ej. S3/GCS) — el comando de arriba solo escribe al disco local del servidor.
