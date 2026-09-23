FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS build
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend ./
# VITE_SENTRY_DSN: variable de BUILD de Vite (import.meta.env), no de runtime --
# tiene que existir en el entorno de ESTE `RUN npm run build`, nunca en el
# contenedor de nginx ya construido (ver docker-compose.yml, build.args del
# servicio `nginx`, y .env.example). Vacía por default: el build resultante no
# inicializa Sentry (frontend/src/lib/sentry.ts), mismo comportamiento de hoy.
ARG VITE_SENTRY_DSN=""
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN
RUN npm run build

FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
