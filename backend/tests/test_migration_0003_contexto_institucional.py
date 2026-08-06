"""Tests de la migración 0003 (backend/alembic/versions/0003_contexto_institucional.py).

Dos niveles, mismo criterio que el resto de esta suite para código que depende de
Postgres real:

1. Estructural, sin Postgres: carga el módulo de la migración por ruta de archivo
   (el nombre del archivo empieza con un dígito, no es un identificador de import
   válido) y sustituye `op`/`postgresql.ENUM` por dobles que solo registran las
   llamadas -- verifica el ORDEN exacto de `upgrade()`/`downgrade()` exigido por
   el diseño (create_table -> create_unique_constraint -> 3x
   create_check_constraint -> ENABLE -> FORCE -> CREATE POLICY), sin ejecutar SQL
   real. Corre siempre, incluso en CI sin Postgres.
2. Contra Postgres real (`docker compose up db`): aplica y revierte la migración
   de verdad, con el mismo `_postgres_real_disponible()` que
   test_plan_job.py/test_api_seguimiento.py -- se salta limpio si no hay Postgres
   alcanzable.
"""

import importlib.util
import socket
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from app.core.config import settings
from app.db.rls import abrir_sesion_tenant

MIGRACION_PATH = Path(__file__).parents[1] / "alembic" / "versions" / "0003_contexto_institucional.py"


def _cargar_modulo_migracion():
    spec = importlib.util.spec_from_file_location("migracion_0003_test", MIGRACION_PATH)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


def _neutralizar_create_drop_de_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    """`postgresql.ENUM` debe seguir siendo un `TypeEngine` real (lo usa
    `sa.Column("conectividad", conectividad_enum, ...)` como tipo de columna) --
    solo se neutraliza `.create()`/`.drop()`, que son los únicos métodos que
    intentarían hablar con Postgres de verdad vía `op.get_bind()`."""
    monkeypatch.setattr(postgresql.ENUM, "create", lambda self, bind=None, checkfirst=True: None)
    monkeypatch.setattr(postgresql.ENUM, "drop", lambda self, bind=None, checkfirst=True: None)


class _OpEspia:
    """Doble de `alembic.op` -- registra cada llamada en orden, sin tocar Postgres."""

    def __init__(self) -> None:
        self.llamadas: list[tuple] = []

    def get_bind(self) -> str:
        return "bind-fake"

    def create_table(self, nombre: str, *columnas: object) -> None:
        self.llamadas.append(("create_table", nombre, [c.name for c in columnas]))

    def create_unique_constraint(self, nombre: str, tabla: str, columnas: list[str]) -> None:
        self.llamadas.append(("create_unique_constraint", nombre, tabla, tuple(columnas)))

    def create_check_constraint(self, nombre: str, tabla: str, condicion: str) -> None:
        self.llamadas.append(("create_check_constraint", nombre, tabla, condicion))

    def execute(self, sql: object) -> None:
        self.llamadas.append(("execute", str(sql).strip()))

    def drop_constraint(self, nombre: str, tabla: str) -> None:
        self.llamadas.append(("drop_constraint", nombre, tabla))

    def drop_table(self, nombre: str) -> None:
        self.llamadas.append(("drop_table", nombre))


# --- (1) estructural, sin Postgres -----------------------------------------------


def test_upgrade_sigue_el_orden_exacto_del_diseno(monkeypatch: pytest.MonkeyPatch) -> None:
    modulo = _cargar_modulo_migracion()
    _neutralizar_create_drop_de_enum(monkeypatch)
    espia = _OpEspia()
    modulo.op = espia

    modulo.upgrade()

    tipos = [llamada[0] for llamada in espia.llamadas]
    assert tipos == [
        "create_table",
        "create_unique_constraint",
        "create_check_constraint",
        "create_check_constraint",
        "create_check_constraint",
        "execute",
        "execute",
        "execute",
    ]


def test_upgrade_crea_la_tabla_con_las_10_columnas_en_orden(monkeypatch: pytest.MonkeyPatch) -> None:
    modulo = _cargar_modulo_migracion()
    _neutralizar_create_drop_de_enum(monkeypatch)
    espia = _OpEspia()
    modulo.op = espia

    modulo.upgrade()

    _, nombre_tabla, columnas = espia.llamadas[0]
    assert nombre_tabla == "contexto_institucional"
    assert columnas == [
        "id",
        "tenant_id",
        "poblacion_total",
        "personal_total_gobierno",
        "presupuesto_tic_anual",
        "area_tic_existe",
        "conectividad",
        "normativa_local_emitida",
        "autoridad_gobernanza_digital",
        "actualizado_en",
        "created_at",
    ]


def test_upgrade_unique_constraint_es_sobre_tenant_id(monkeypatch: pytest.MonkeyPatch) -> None:
    modulo = _cargar_modulo_migracion()
    _neutralizar_create_drop_de_enum(monkeypatch)
    espia = _OpEspia()
    modulo.op = espia

    modulo.upgrade()

    llamada = next(ll for ll in espia.llamadas if ll[0] == "create_unique_constraint")
    assert llamada == (
        "create_unique_constraint",
        "uq_contexto_institucional_tenant",
        "contexto_institucional",
        ("tenant_id",),
    )


def test_upgrade_los_3_check_constraints_permiten_null_o_no_negativo(monkeypatch: pytest.MonkeyPatch) -> None:
    modulo = _cargar_modulo_migracion()
    _neutralizar_create_drop_de_enum(monkeypatch)
    espia = _OpEspia()
    modulo.op = espia

    modulo.upgrade()

    checks = [ll for ll in espia.llamadas if ll[0] == "create_check_constraint"]
    condiciones = {nombre: condicion for _tipo, nombre, _tabla, condicion in checks}
    assert (
        condiciones["ck_contexto_institucional_poblacion_no_negativa"]
        == "poblacion_total IS NULL OR poblacion_total >= 0"
    )
    assert (
        condiciones["ck_contexto_institucional_personal_no_negativo"]
        == "personal_total_gobierno IS NULL OR personal_total_gobierno >= 0"
    )
    assert (
        condiciones["ck_contexto_institucional_presupuesto_no_negativo"]
        == "presupuesto_tic_anual IS NULL OR presupuesto_tic_anual >= 0"
    )


def test_upgrade_rls_en_orden_enable_force_create_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    modulo = _cargar_modulo_migracion()
    _neutralizar_create_drop_de_enum(monkeypatch)
    espia = _OpEspia()
    modulo.op = espia

    modulo.upgrade()

    ejecuciones = [ll[1] for ll in espia.llamadas if ll[0] == "execute"]
    assert "ENABLE ROW LEVEL SECURITY" in ejecuciones[0]
    assert "FORCE ROW LEVEL SECURITY" in ejecuciones[1]
    assert "CREATE POLICY tenant_isolation" in ejecuciones[2]
    assert "current_setting('app.tenant_id')::uuid" in ejecuciones[2]


def test_downgrade_es_simetrico_y_en_orden_inverso(monkeypatch: pytest.MonkeyPatch) -> None:
    modulo = _cargar_modulo_migracion()
    _neutralizar_create_drop_de_enum(monkeypatch)
    espia = _OpEspia()
    modulo.op = espia

    modulo.downgrade()

    tipos = [ll[0] for ll in espia.llamadas]
    assert tipos == [
        "execute",
        "drop_constraint",
        "drop_constraint",
        "drop_constraint",
        "drop_constraint",
        "drop_table",
    ]
    assert "DROP POLICY IF EXISTS tenant_isolation" in espia.llamadas[0][1]

    nombres_constraints = [ll[1] for ll in espia.llamadas if ll[0] == "drop_constraint"]
    assert nombres_constraints == [
        "ck_contexto_institucional_presupuesto_no_negativo",
        "ck_contexto_institucional_personal_no_negativo",
        "ck_contexto_institucional_poblacion_no_negativa",
        "uq_contexto_institucional_tenant",
    ]
    assert espia.llamadas[-1] == ("drop_table", "contexto_institucional")


def test_revision_ids_encadenan_con_0002() -> None:
    modulo = _cargar_modulo_migracion()
    assert modulo.revision == "0003"
    assert modulo.down_revision == "0002"


# --- (2) contra Postgres real -----------------------------------------------------


def _postgres_real_disponible() -> bool:
    url = urlparse(settings.database_url.replace("postgresql+psycopg", "postgresql", 1))
    try:
        with socket.create_connection((url.hostname or "localhost", url.port or 5432), timeout=2):
            pass
    except OSError:
        return False
    try:
        db = abrir_sesion_tenant(uuid4())
    except Exception:
        return False
    db.close()
    return True


def _alembic_config():
    from alembic.config import Config

    backend_dir = Path(__file__).parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.migrations_database_url)
    return cfg


@pytest.mark.skipif(
    not _postgres_real_disponible(),
    reason="Requiere Postgres real alcanzable con el DATABASE_URL configurado (docker compose up db)",
)
def test_upgrade_y_downgrade_contra_postgres_real() -> None:
    from alembic import command

    cfg = _alembic_config()
    command.upgrade(cfg, "0003")

    db = abrir_sesion_tenant(uuid4())
    try:
        resultado = db.execute(text("SELECT count(*) FROM contexto_institucional")).scalar_one()
        assert resultado == 0
    finally:
        db.close()

    command.downgrade(cfg, "0002")

    db2 = abrir_sesion_tenant(uuid4())
    try:
        with pytest.raises(Exception):
            db2.execute(text("SELECT count(*) FROM contexto_institucional"))
    finally:
        db2.rollback()
        db2.close()
