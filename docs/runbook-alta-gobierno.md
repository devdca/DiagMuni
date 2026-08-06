# Runbook — Alta de un gobierno nuevo

Guía operativa para quien opera el despliegue (la contraparte técnica designada, `docs/PRD.md` "Fuera de alcance": sin onboarding self-service). Referencia técnica completa en `docs/TRD.md`, sección "Alta de un gobierno nuevo"; diseño y justificación de cada decisión en `docs/plan-implementacion-alta-gobierno.md`.

## Requisito previo

Acceso de terminal (SSH o similar) al servidor donde corre `docker compose` — el mismo acceso que ya se necesita para levantar el stack, correr migraciones o (en desarrollo) `python -m app.seed`. No se necesita ninguna herramienta adicional ni variable de entorno nueva.

## Crear un gobierno nuevo

```
docker compose exec backend python -m app.bootstrap_tenant crear-gobierno \
  --nombre "Intendencia de Canelones" \
  --clave canelones \
  --pais uy \
  --email maria.perez@canelones.gub.uy \
  --nombre-funcionario "María Pérez"
```

- `--nombre`: nombre del gobierno tal como debe verse en la plataforma.
- `--clave`: identificador corto único que el funcionario escribe al iniciar sesión (solo minúsculas, números y guiones simples entre palabras — ej. `canelones`, `san-luis-potosi`). No puede repetirse: si ya existe un gobierno con esa clave, el comando no crea nada y lo avisa.
- `--pais`: `mx` o `uy` — determina el marco normativo (LNETB/ATDT en México, Agesic/leyes nacionales en Uruguay) que la plataforma le muestra a ese gobierno.
- `--email` / `--nombre-funcionario`: datos del primer funcionario que va a usar la plataforma.

Salida esperada:

```
====================================================================
ADVERTENCIA: esta contraseña no se vuelve a mostrar. Anótela ahora
y entréguela a la contraparte técnica por un canal seguro.
====================================================================
Gobierno: Intendencia de Canelones (clave: canelones)
Funcionario: María Pérez <maria.perez@canelones.gub.uy>
Contraseña de arranque: k7Ht-4mQs-2wZp-9bKf
====================================================================
```

**Anote esa contraseña ahora.** No queda guardada en ningún archivo ni log del propio comando — es responsabilidad de quien opera conservarla (captura de pantalla, gestor de contraseñas) hasta entregarla al funcionario por un canal seguro (nunca por el mismo canal que el resto de sus credenciales, ej. no en el mismo correo que contiene su usuario).

## Si el comando dice que la clave ya existe

```
Ya existe un gobierno con la clave 'canelones'. No se creó nada nuevo.
```

No se escribió nada en la base — es seguro volver a intentar con una `--clave` distinta si fue un error de tecleo, o usar `resetear-password` (abajo) si el gobierno ya existe y lo que hace falta es recuperar el acceso.

## Si se perdió la contraseña de un funcionario

```
docker compose exec backend python -m app.bootstrap_tenant resetear-password \
  --clave canelones \
  --email maria.perez@canelones.gub.uy
```

Genera una contraseña nueva para ese usuario (mismo formato, misma advertencia de "no se vuelve a mostrar") y sobrescribe la anterior — la anterior deja de funcionar de inmediato. Si la `clave` o el `email` no corresponden a un gobierno/usuario real, el comando lo avisa sin cambiar nada:

```
No se encontró el usuario 'maria.perez@canelones.gub.uy' en el gobierno con clave 'canelones'.
```

## Qué este runbook NO cubre (alcance futuro, no construido)

- Agregar un segundo funcionario a un gobierno que ya tiene uno — no existe ese comando todavía.
- Cualquier flujo donde el propio funcionario cambie su contraseña sin pasar por el operador — deliberadamente fuera de alcance (`docs/PRD.md`, onboarding self-service excluido).
