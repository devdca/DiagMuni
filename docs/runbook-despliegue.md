# Runbook — Despliegue inicial y operación básica

Guía operativa para quien instala y mantiene el stack completo (la contraparte técnica designada, `docs/PRD.md` "Fuera de alcance": sin onboarding self-service). Referencia técnica completa en `docs/TRD.md` y `docs/stack-tecnologico.md`. Una vez que el stack esté corriendo, el alta del primer gobierno se hace con `docs/runbook-alta-gobierno.md` — este documento no lo repite.

## Requisito previo

- Acceso de terminal (SSH o similar) al servidor donde va a correr el proyecto.
- Docker Engine y Docker Compose v2 instalados (el comando es `docker compose`, sin guion — si el servidor solo tiene la versión vieja `docker-compose`, con guion, hay que actualizar antes de seguir).
- Piso de hardware: sin benchmark propio en este documento (`[NO VERIFICADO]`), pero nginx + FastAPI + Postgres sin modelo de IA local corren cómodos en un VPS económico (2 vCPU / 2 GB RAM como piso práctico). Esto **no** aplica si además se activa un modelo de IA local (Ollama/phi3) en la misma máquina — para ese escenario ver `entregables/fase-2/dimensionamiento-costos.md` (8 vCPU / 16 GB recomendado).
- Ningún otro proceso usando el puerto 80/8090 del servidor (nginx del proyecto publica el puerto **8090** hacia afuera — ver `docker-compose.yml`).

## Paso 1 — Obtener el código

```
git clone https://github.com/devdca/DiagMuni.git
cd DiagMuni
```

## Paso 2 — Configurar `.env`

```
cp .env.example .env
```

Editar `.env` con cualquier editor de texto. Cada variable ya está comentada en el propio archivo; las dos que **siempre** hay que revisar antes de un despliegue real (no de prueba):

- **`JWT_SECRET`**: el valor de `.env.example` es un placeholder público (está en el repositorio). Generar uno real:
  ```
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  Pegar el resultado como valor de `JWT_SECRET`.
- **`ENVIRONMENT`**: dejarlo en `development` mientras se está probando; cambiarlo a `production` antes de dar acceso real a un gobierno. Si se pone `ENVIRONMENT=production` sin haber cambiado `JWT_SECRET` del placeholder, el contenedor `backend` **no arranca** — ver la sección de errores más abajo, es un comportamiento intencional, no un bug.

Las demás variables (`DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_API_BASE`, `LLM_PROVIDER`) son opcionales — vacías, el generador de planes degrada a una plantilla determinista en vez de redacción por IA. No hace falta ninguna para que el resto de la plataforma funcione.

## Paso 3 — Levantar el stack

```
docker compose up -d
```

La primera vez construye las imágenes (puede tardar unos minutos); las siguientes veces solo arranca los contenedores ya construidos. Verificar que los tres servicios están arriba:

```
docker compose ps
```

Salida esperada — los tres en estado `Up`/`healthy` (puede tardar unos segundos en pasar de `starting` a `healthy`):

```
NAME                 STATUS
diagmuni-db-1        Up (healthy)
diagmuni-backend-1   Up (healthy)
diagmuni-nginx-1     Up
```

## Paso 4 — Correr las migraciones (obligatorio, una sola vez por base de datos nueva)

**Este paso no ocurre solo.** Levantar el stack (paso 3) no crea las tablas de la base de datos — hay que correr las migraciones de Alembic explícitamente:

```
docker compose exec backend alembic upgrade head
```

Salida esperada (tres migraciones aplicadas en una base de datos nueva):

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, esquema inicial: 7 tablas + RLS
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, tenant.clave...
INFO  [alembic.runtime.migration] Running upgrade 0002 -> 0003, contexto_institucional...
```

Si se vuelve a correr el mismo comando después (ej. tras actualizar a una versión nueva del código), Alembic solo aplica las migraciones que falten — es seguro correrlo de nuevo, no duplica nada.

## Paso 5 — Verificar que la plataforma responde

```
curl http://localhost:8090/health
```

Debe responder `{"status":"ok"}`. Si el servidor es remoto, cambiar `localhost` por la IP/dominio del servidor.

## Siguiente paso

Con el stack arriba y las migraciones aplicadas, dar de alta el primer gobierno siguiendo `docs/runbook-alta-gobierno.md`.

## Errores comunes

### El puerto 8090 ya está en uso

```
Error starting userland proxy: listen tcp4 0.0.0.0:8090: bind: address already in use
```

Otro proceso del servidor ya usa ese puerto. O se libera ese puerto, o se cambia el mapeo en `docker-compose.yml` (servicio `nginx`, línea `"8090:80"`) por otro puerto libre, ej. `"8091:80"`.

### El contenedor `backend` no arranca / se reinicia solo

```
docker compose logs backend
```

Si el log termina en algo como:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
  Value error, JWT_SECRET no puede quedar vacío ni con el valor de ejemplo de .env.example cuando ENVIRONMENT=production...
```

Es el guard de seguridad descrito en el Paso 2 — falta cambiar `JWT_SECRET` en `.env` por uno generado de verdad. Después de editar `.env`:

```
docker compose up -d --force-recreate backend
```

### Los endpoints devuelven error 500 / "relation ... does not exist"

```
docker compose logs backend
```

Si aparece algo como `relation "tenant" does not exist`, faltó el Paso 4 (migraciones) — correrlo ahora no rompe nada, aunque el stack ya lleve tiempo arriba.

### Ver logs de un servicio en vivo

```
docker compose logs -f backend
```

(`-f` sigue el log en tiempo real; `Ctrl+C` para salir de la vista, no detiene el contenedor). Cambiar `backend` por `db` o `nginx` según el servicio.

### Detener, reiniciar, actualizar

- **Detener sin borrar datos:** `docker compose down` — los contenedores se eliminan, pero la base de datos persiste en un volumen aparte.
- **Reiniciar:** `docker compose up -d` de nuevo (mismo comando del Paso 3) — reutiliza el volumen existente, no vuelve a pedir migraciones si ya están aplicadas.
- **Actualizar a una versión nueva del código:**
  ```
  git pull
  docker compose up -d --build
  docker compose exec backend alembic upgrade head
  ```
  (el último paso es un no-op seguro si no hay migraciones nuevas que aplicar, ver Paso 4).

**Advertencia — nunca correr en un despliegue con datos reales:** `docker compose down -v`. El flag `-v` borra también el volumen de la base de datos — todos los gobiernos, diagnósticos y planes ya creados se pierden sin posibilidad de recuperación. Solo es aceptable en un entorno de prueba descartable.

## Qué este runbook NO cubre (alcance futuro, no construido)

- **HTTPS/TLS.** `nginx/nginx.conf` sirve hoy solo HTTP plano (puerto 80 dentro del contenedor, expuesto como 8090). Para producción real, terminar TLS con un proxy adicional por delante (ej. Caddy, o el balanceador del proveedor de VPS) o agregar certificados a este mismo nginx — no construido ni documentado en este repositorio todavía.
- **Respaldo (backup) de la base de datos.** No hay ningún mecanismo de backup automático del volumen de Postgres — es responsabilidad del operador del despliegue (ej. `pg_dump` programado, snapshot del volumen a nivel de infraestructura).
- **Despliegue multi-servidor / alta disponibilidad.** El `docker-compose.yml` de este repositorio es para una sola máquina — no cubre balanceo de carga ni réplicas de la base de datos.
- **Rotar `JWT_SECRET` en un despliegue ya en uso.** Cambiarlo invalida de inmediato todas las sesiones activas (los JWT ya emitidos dejan de validar) — no hay un mecanismo de rotación sin downtime documentado aquí.
