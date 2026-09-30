"""Tests HTTP (TestClient) de PUT/GET /api/gobierno/logo
(app/adaptadores/http/gobierno_logo.py). Mismo enfoque que
test_api_gobierno_contexto.py: `TestClient` real sobre `app.main.app` con
`dependency_overrides` de `get_current_token`/`get_db`, sin Postgres real -- el
router solo hace `db.get(Tenant, ...)`/`db.commit()`. El storage de disco SÍ es
real, apuntando a un directorio temporal (mismo criterio que
test_gestion_logo.py) -- lo único mockeado es la base de datos, no el
filesystem, para que un test de idempotencia/aislamiento ejerza el camino
completo igual que en producción."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.adaptadores.http.deps import TokenData, get_current_token, get_db
from app.core.config import settings
from app.main import app
from app.models import Tenant

client = TestClient(app)


class _SesionFalsaTenant:
    """Doble de `Session` -- un solo `Tenant` en memoria, suficiente para
    ejercitar `db.get(Tenant, tenant_id)`/`db.commit()` sin Postgres."""

    def __init__(self, tenant: Tenant) -> None:
        self.tenant = tenant
        self.commits = 0

    def get(self, _modelo: object, pk: object) -> Tenant | None:
        return self.tenant if pk == self.tenant.id else None

    def commit(self) -> None:
        self.commits += 1


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _storage_en_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "logo_storage_dir", str(tmp_path))


def _autenticar(tenant_id, rol: str = "admin_gobierno") -> None:
    app.dependency_overrides[get_current_token] = lambda: TokenData(
        usuario_id=uuid4(), tenant_id=tenant_id, rol=rol
    )


def _con_sesion(tenant: Tenant) -> _SesionFalsaTenant:
    sesion = _SesionFalsaTenant(tenant)
    app.dependency_overrides[get_db] = lambda: sesion
    return sesion


def _tenant_de_prueba(**overrides: object) -> Tenant:
    base: dict[object, object] = {
        "id": uuid4(),
        "nombre": "Gobierno de prueba",
        "clave": f"prueba-logo-{uuid4()}",
        "pais": "mx",
    }
    base.update(overrides)
    return Tenant(**base)


_PNG_FALSO = b"\x89PNG-contenido-de-prueba"


# === PUT =============================================================================


def test_put_requiere_sesion() -> None:
    respuesta = client.put("/api/gobierno/logo", files={"archivo": ("logo.png", _PNG_FALSO, "image/png")})
    assert respuesta.status_code in (401, 403)


def test_put_rechaza_rol_funcionario() -> None:
    tenant = _tenant_de_prueba()
    _autenticar(tenant.id, rol="funcionario")
    _con_sesion(tenant)

    respuesta = client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.png", _PNG_FALSO, "image/png")},
    )
    assert respuesta.status_code == 403


def test_put_rechaza_tipo_no_permitido() -> None:
    tenant = _tenant_de_prueba()
    _autenticar(tenant.id)
    _con_sesion(tenant)

    respuesta = client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.pdf", b"%PDF-falso", "application/pdf")},
    )
    assert respuesta.status_code == 422
    assert tenant.logo_content_type is None


def test_put_rechaza_archivo_que_supera_el_limite(monkeypatch) -> None:
    monkeypatch.setattr(settings, "logo_max_bytes", 10)
    tenant = _tenant_de_prueba()
    _autenticar(tenant.id)
    _con_sesion(tenant)

    respuesta = client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.png", b"x" * 11, "image/png")},
    )
    assert respuesta.status_code == 413
    assert tenant.logo_content_type is None


def test_put_guarda_logo_y_permite_descargarlo_despues() -> None:
    tenant = _tenant_de_prueba()
    _autenticar(tenant.id)
    sesion = _con_sesion(tenant)

    respuesta_put = client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.png", _PNG_FALSO, "image/png")},
    )
    assert respuesta_put.status_code == 204
    assert sesion.commits == 1
    assert tenant.logo_content_type == "image/png"
    assert tenant.logo_actualizado_en is not None

    respuesta_get = client.get("/api/gobierno/logo", headers={"Authorization": "Bearer x"})
    assert respuesta_get.status_code == 200
    assert respuesta_get.content == _PNG_FALSO
    assert respuesta_get.headers["content-type"] == "image/png"


def test_put_reemplaza_logo_ya_subido() -> None:
    tenant = _tenant_de_prueba()
    _autenticar(tenant.id)
    _con_sesion(tenant)

    client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.png", b"version-1", "image/png")},
    )
    respuesta = client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.jpg", b"version-2", "image/jpeg")},
    )
    assert respuesta.status_code == 204
    assert tenant.logo_content_type == "image/jpeg"

    respuesta_get = client.get("/api/gobierno/logo", headers={"Authorization": "Bearer x"})
    assert respuesta_get.content == b"version-2"
    assert respuesta_get.headers["content-type"] == "image/jpeg"


# === GET =============================================================================


def test_get_requiere_sesion() -> None:
    respuesta = client.get("/api/gobierno/logo")
    assert respuesta.status_code in (401, 403)


def test_get_sin_logo_subido_responde_404() -> None:
    tenant = _tenant_de_prueba()
    _autenticar(tenant.id)
    _con_sesion(tenant)

    respuesta = client.get("/api/gobierno/logo", headers={"Authorization": "Bearer x"})
    assert respuesta.status_code == 404


def test_get_permite_rol_funcionario() -> None:
    """A diferencia de PUT, GET no exige admin_gobierno -- cualquier funcionario
    autenticado del tenant necesita poder cargar el logo en su propia UI."""
    tenant = _tenant_de_prueba(logo_content_type="image/png")
    from app.adaptadores.almacenamiento import logo_storage

    logo_storage.guardar_logo(tenant.id, _PNG_FALSO)

    _autenticar(tenant.id, rol="funcionario")
    _con_sesion(tenant)

    respuesta = client.get("/api/gobierno/logo", headers={"Authorization": "Bearer x"})
    assert respuesta.status_code == 200
    assert respuesta.content == _PNG_FALSO


# === Aislamiento entre tenants =======================================================


def test_logo_de_un_tenant_no_es_visible_para_otro() -> None:
    tenant_a = _tenant_de_prueba()
    tenant_b = _tenant_de_prueba()

    _autenticar(tenant_a.id)
    _con_sesion(tenant_a)
    client.put(
        "/api/gobierno/logo",
        headers={"Authorization": "Bearer x"},
        files={"archivo": ("logo.png", _PNG_FALSO, "image/png")},
    )

    # Mismo cliente, ahora autenticado (y con sesión) como el tenant B -- ningún
    # parámetro de la request identifica al tenant salvo el token, así que esto
    # ejercita exactamente el mismo perímetro que un atacante tendría que cruzar.
    _autenticar(tenant_b.id)
    _con_sesion(tenant_b)
    respuesta = client.get("/api/gobierno/logo", headers={"Authorization": "Bearer x"})
    assert respuesta.status_code == 404
