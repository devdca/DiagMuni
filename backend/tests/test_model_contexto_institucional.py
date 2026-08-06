"""Tests del modelo ORM `ContextoInstitucional` (backend/app/models/
contexto_institucional.py) -- sin sesión de DB real, solo verifica la forma del
mapeo (nombre de tabla, columnas, nullabilidad) construyendo instancias en
memoria, mismo criterio que otros modelos de este repo (ej. `_tenant_de_prueba`
en test_plan_job.py)."""

from uuid import uuid4

from app.models import ContextoInstitucional

CAMPOS_DE_NEGOCIO = (
    "poblacion_total",
    "personal_total_gobierno",
    "presupuesto_tic_anual",
    "area_tic_existe",
    "conectividad",
    "normativa_local_emitida",
    "autoridad_gobernanza_digital",
)


def test_tablename_es_contexto_institucional():
    assert ContextoInstitucional.__tablename__ == "contexto_institucional"


def test_tenant_id_es_columna_unica_y_no_nula():
    columna = ContextoInstitucional.__table__.c.tenant_id
    assert columna.nullable is False
    assert columna.unique is True


def test_todas_las_columnas_de_negocio_son_nullable():
    for nombre in CAMPOS_DE_NEGOCIO:
        columna = ContextoInstitucional.__table__.c[nombre]
        assert columna.nullable is True, f"{nombre} debería ser nullable"


def test_actualizado_en_es_nullable_created_at_no():
    # `Mapped[datetime]` (no `| None`) infiere `nullable=False` -- mismo patrón que
    # `tenant.created_at` (backend/app/models/tenant.py).
    assert ContextoInstitucional.__table__.c.actualizado_en.nullable is True
    assert ContextoInstitucional.__table__.c.created_at.nullable is False


def test_conectividad_acepta_los_3_valores_del_diseno():
    tenant_id = uuid4()
    for valor in ("estable", "intermitente", "sin_conexion"):
        instancia = ContextoInstitucional(tenant_id=tenant_id, conectividad=valor)
        assert instancia.conectividad == valor


def test_instancia_sin_ningun_campo_de_negocio_queda_en_none():
    instancia = ContextoInstitucional(tenant_id=uuid4())
    for nombre in CAMPOS_DE_NEGOCIO:
        assert getattr(instancia, nombre) is None
