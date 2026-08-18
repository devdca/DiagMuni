# Runbook — Despliegue inicial y operación básica

Guía operativa para quien instala y mantiene el stack completo (la contraparte técnica designada, `docs/PRD.md` "Fuera de alcance": sin onboarding self-service). Referencia técnica completa en `docs/TRD.md` y `docs/stack-tecnologico.md`. Una vez que el stack esté corriendo, el alta del primer gobierno se hace con `docs/runbook-alta-gobierno.md` — este documento no lo repite.

## Requisito previo

- Acceso de terminal (SSH o similar) al servidor donde va a correr el proyecto.
- Docker Engine y Docker Compose v2 instalados (el comando es `docker compose`, sin guion — si el servidor solo tiene la versión vieja `docker-compose`, con guion, hay que actualizar antes de seguir).
- Piso de hardware: sin benchmark propio en este documento (`[NO VERIFICADO]`), pero nginx + FastAPI + Postgres sin modelo de IA local corren cómodos en un VPS económico (2 vCPU / 2 GB RAM como piso práctico). Esto **no** aplica si además se activa un modelo de IA local (Ollama/phi3) en la misma máquina — para ese escenario ver `entregables/fase-2/dimensionamiento-costos.md` (8 vCPU / 16 GB recomendado).
- Ningún otro proceso usando el puerto 80/8090 del servidor (nginx del proyecto publica el puerto **8090** hacia afuera — ver `docker-compose.yml`).

## Requisito previo — instalar Docker en un equipo Windows local (sin servidor Linux)

Los pasos de arriba asumen que ya existe un servidor con Docker instalado. Para desplegar en un equipo Windows local (ej. una laptop, como piso mínimo de referencia — si el stack corre ahí, corre en cualquier VPS), instalar Docker Desktop primero. Verificado de punta a punta en un equipo Windows real, 2026-08-11:

1. **Habilitar WSL2** (backend requerido por Docker Desktop en Windows). Abrir PowerShell **como administrador**:
   ```
   wsl --install
   ```
   Instala WSL2 con Ubuntu como distro predeterminada. Reiniciar el equipo solo si el instalador lo pide explícitamente — no siempre es necesario, depende de la configuración previa del equipo (`[NO VERIFICADO]` si existe un caso donde no reiniciar cause un fallo silencioso; en la verificación de referencia no hizo falta reiniciar).

   Confirmar con una terminal normal (no necesita ser administrador):
   ```
   wsl --status
   ```
   Salida esperada (ejemplo real de la verificación de referencia):
   ```
   Distribución predeterminada: Ubuntu
   Versión predeterminada: 2
   ```

2. **Instalar Docker Desktop** desde `https://www.docker.com/products/docker-desktop/`. Durante la instalación, si pregunta por el backend, elegir **WSL2** (no Hyper-V) — es el que este runbook verifica. Abrir Docker Desktop después de instalar y esperar a que el ícono de la barra de tareas muestre que el motor ya está corriendo.

3. **Verificar la instalación** desde una terminal normal:
   ```
   docker --version
   docker compose version
   ```
   Salida esperada (versiones exactas de la verificación de referencia; versiones más nuevas también sirven — lo que importa es que `docker compose` responda, sin guion):
   ```
   Docker version 29.7.2, build a7dcaa6
   Docker Compose version v5.3.1
   ```

Con esto, continuar directo en el **Paso 1** de abajo — el resto del runbook (clonar, `.env`, `docker compose up -d`, migraciones) es idéntico en Windows, Linux o macOS; los comandos de Docker Compose son los mismos en cualquier terminal.

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
  - Con Python instalado (Linux/macOS: comando `python3`; en Windows normalmente es `python` — verificar antes con `python --version`):
    ```
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    ```
  - **Sin Python** (ej. equipo Windows recién instalado, sin ninguna dependencia adicional), en PowerShell:
    ```
    [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).Replace('+','-').Replace('/','_').Replace('=','')
    ```
    Mismo formato y entropía que la alternativa de Python (32 bytes aleatorios en base64 url-safe sin relleno). Verificado 2026-08-11, salida real de ejemplo: `ahuXgo7LG5sKxKxxwkVqVEhSaSWqLenRNEnTfFwNbA8` (no reutilizar este valor de ejemplo — generar uno propio por despliegue).

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

## IA local con Ollama (opcional)

Sin `DEEPSEEK_API_KEY`/`ANTHROPIC_API_KEY`/`OLLAMA_API_BASE` configuradas, el generador de planes usa una plantilla determinista — funciona igual, solo sin redacción asistida por IA. Si en cambio se quiere redacción por IA sin depender de una API de pago (principio de "Transferencia de capacidades" del README raíz: el producto no debe generar dependencia de un proveedor privativo), el stack incluye un perfil opcional de Docker Compose con Ollama:

```
docker compose --profile ia-local up -d
docker compose exec ollama ollama pull phi3
```

Editar `.env` y fijar `OLLAMA_API_BASE=http://ollama:11434`, luego recrear el backend para que tome el cambio:

```
docker compose up -d --force-recreate backend
```

**Requisito de hardware** (`docs/stack-tecnologico.md`): 8 vCPU / 16 GB recomendado — más pesado que el piso de 2 vCPU / 2 GB del despliegue sin IA local. El primer plan generado con `phi3` puede tardar 1-2 minutos (benchmark sin GPU: 76-123s, `docs/TRD.md`) — normal, el frontend muestra "Generando plan…" mientras espera.

Sin este perfil activo (el caso por defecto), `docker compose up -d` no levanta Ollama — el stack liviano sin IA local sigue funcionando exactamente igual que antes de esta sección.

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

## HTTPS/TLS

`nginx/nginx.conf` sirve por default solo HTTP plano (puerto 80 dentro del contenedor, expuesto como 8090). Para producción real, hay un segundo archivo de Compose que agrega Caddy delante de nginx y obtiene/renueva certificados Let's Encrypt solo — sin tocar la imagen de nginx.

**Requisito, sin el cual esto no sirve de nada:** un registro DNS `A`/`AAAA` real apuntando a este servidor. A diferencia del resto de las decisiones de este proyecto (pensadas para no depender de terceros), esto es una dependencia externa inevitable — sin ella, Let's Encrypt no puede validar el dominio y Caddy nunca emite el certificado.

1. En `.env`, fijar:
   ```
   TLS_DOMAIN=midiagmuni.ejemplo.gob
   TLS_EMAIL=contacto@ejemplo.gob
   COMPOSE_FILE=docker-compose.yml:docker-compose.tls.yml
   ```
   `COMPOSE_FILE` hace que todo comando `docker compose` futuro (`up`, `down`, `build`) incluya automáticamente `docker-compose.tls.yml` sin tener que recordar pasar `-f` dos veces cada vez.
2. Levantar de nuevo:
   ```
   docker compose up -d
   ```
3. Verificar que el override de puertos de `nginx` sí se aplicó (`docker-compose.tls.yml` cierra el 8090 público a loopback y agrega el servicio `caddy`):
   ```
   docker compose config | grep -A3 "nginx:"
   ```
   Debe mostrar `127.0.0.1:8090:80`, no `0.0.0.0:8090:80` ni una lista con ambos.

Si el reto ACME falla (ej. DNS mal configurado o no propagado todavía), Caddy reintenta con backoff — no cae en silencio a servir HTTP plano sin avisar. Ver `docker compose logs -f caddy`.

`[NO VERIFICADO]`: esta ruta no la ejercita ningún test automático de este repositorio — necesita un dominio público real y los puertos 80/443 accesibles desde internet, algo que CI no tiene.

## Respaldo (backup) de la base de datos

Procedimiento completo en `docs/runbook-backup.md` — no se repite aquí. En resumen: `pg_dump` programado por `cron`, sin ningún script nuevo en el repo (el pipeline es corto de sobra para vivir directo en ese runbook), sin automatización de restauración a propósito (operación irreversible, exige revisión manual cada vez).

## Rotar `JWT_SECRET` en un despliegue ya en uso

Cambiarlo invalida de inmediato **todas** las sesiones activas — los JWT ya emitidos dejan de validar en el momento en que el backend arranca con el secreto nuevo (`backend/tests/test_security_jwt.py::test_rotar_jwt_secret_invalida_tokens_ya_emitidos` deja esto como contrato probado, no solo documentado). No hay soporte de doble secreto (aceptar el viejo durante una ventana de gracia) **a propósito**: un secreto se rota casi siempre porque toca higiene calendarizada, o porque se sospecha/confirmó que se filtró — y en el segundo caso, un mecanismo de doble secreto sería activamente contraproducente: cualquier JWT que un atacante ya haya forjado con el secreto filtrado seguiría siendo válido durante toda la ventana de gracia, justo cuando rotar importa más. Con sesiones de 8 horas y sin refresh token (`docs/backend-schema.md`), el costo real de "todo o nada" es que cada funcionario reingresa sus credenciales una vez, dentro de la misma jornada.

1. Generar un secreto nuevo (mismo comando del Paso 2 de este runbook).
2. Actualizar `JWT_SECRET` en `.env`.
3. Recrear el backend para que tome el cambio:
   ```
   docker compose up -d --force-recreate backend
   ```

Dos notas operativas:

- Un `Job` de generación de plan que estuviera a medio proceso justo durante el `--force-recreate` se recupera solo vía el watchdog ya existente (`backend/app/jobs/plan_job.py`, hasta `job_umbral_obsoleto_minutos`, 15 minutos por default) — no requiere ninguna intervención manual.
- El guard de `backend/app/core/config.py` atrapa un `JWT_SECRET` vacío o igual al placeholder de `.env.example`, pero **no** un typo parcial (secreto copiado a medias al pegar). Si tras rotar nadie puede loguearse aunque las credenciales sean correctas, lo primero a revisar es que el valor de `JWT_SECRET` se copió completo.

## Despliegue multi-servidor / alta disponibilidad

El `docker-compose.yml` de este repositorio es para una sola máquina — no cubre balanceo de carga ni réplicas de la base de datos. Alcance futuro, no construido.
