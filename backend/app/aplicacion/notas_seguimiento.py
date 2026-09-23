"""Notas colaborativas sobre una acción de seguimiento (migración 0014) -- ver
docstring de esa migración."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NotaSeguimiento, Usuario


def crear_nota(
    db: Session, *, tenant_id: UUID, accion_seguimiento_id: UUID, usuario_id: UUID, texto: str
) -> NotaSeguimiento:
    nota = NotaSeguimiento(
        tenant_id=tenant_id, accion_seguimiento_id=accion_seguimiento_id, usuario_id=usuario_id, texto=texto.strip()
    )
    db.add(nota)
    db.flush()
    return nota


def listar_notas(db: Session, *, tenant_id: UUID, accion_seguimiento_id: UUID) -> list[tuple[NotaSeguimiento, str]]:
    """Devuelve `(nota, nombre_del_autor)` -- `NotaSeguimiento` no tiene relación
    ORM declarada con `Usuario` (mismo criterio del resto del proyecto, ej.
    `_tramite_de_plan` en app/adaptadores/http/seguimiento.py), así que el nombre
    se resuelve con un join explícito en vez de agregar una relación nueva."""
    filas = db.execute(
        select(NotaSeguimiento, Usuario.nombre)
        .join(Usuario, NotaSeguimiento.usuario_id == Usuario.id)
        .where(
            NotaSeguimiento.tenant_id == tenant_id,
            NotaSeguimiento.accion_seguimiento_id == accion_seguimiento_id,
        )
        .order_by(NotaSeguimiento.creado_en.asc())
    ).all()
    return [(nota, nombre) for nota, nombre in filas]
