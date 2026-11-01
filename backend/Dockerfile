FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

WORKDIR /app

# Contexto de build = raíz del repo (ver docker-compose.yml: context: ., dockerfile: backend/Dockerfile)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini .

# Directorio del volumen `diagmuni_logos_data` (docker-compose.yml) -- se crea acá,
# antes del chown de abajo, para que cuando Docker monte el volumen por primera vez
# copie el contenido/permisos de ESTE directorio (vacío, dueño appuser) en vez de
# quedar con el dueño root por defecto de un volumen nombrado nuevo -- appuser
# (sin privilegios de superusuario, ver USER abajo) no podría escribir el logo si
# el volumen quedara con permisos de root.
RUN mkdir -p /app/data/logos

RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
