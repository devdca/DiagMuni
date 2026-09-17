FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

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
