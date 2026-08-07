"""Tests HTTP (TestClient) del rate-limiting de POST /api/auth/login (hallazgo de
Strix vuln-0001, "Missing brute-force protection on /api/auth/login"). Monkeypatch
de `abrir_sesion_tenant` para no depender de Postgres real -- estos tests
verifican el límite de intentos, no la resolución de credenciales en sí (ya
cubierta por la ausencia de fix real anterior; el 401 por credenciales
incorrectas es incidental aquí). Cada test usa una IP (`X-Real-Ip`) propia para
no compartir cupo con los demás, ya que `_limitador` es una instancia a nivel de
módulo que persiste entre tests del mismo proceso."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import auth as auth_api
from app.main import app

client = TestClient(app)


class _SesionFalsaSinUsuario:
    """Doble de `Session` -- nunca encuentra usuario ni tenant, suficiente para
    ejercitar el rate-limiter sin tocar la base de datos."""

    def execute(self, _stmt: object) -> "_ResultadoFalso":
        return _ResultadoFalso(None)

    def get(self, _modelo: object, _id: object) -> None:
        return None

    def close(self) -> None:
        pass


class _ResultadoFalso:
    def __init__(self, valor: object) -> None:
        self._valor = valor

    def scalar_one_or_none(self) -> object:
        return self._valor


def _cuerpo_login() -> dict[str, str]:
    return {"tenant_id": str(uuid4()), "email": "nadie@example.com", "password": "loquesea"}


def test_intentos_dentro_del_limite_llegan_a_verificar_credenciales(monkeypatch):
    monkeypatch.setattr(auth_api, "abrir_sesion_tenant", lambda _tenant_id: _SesionFalsaSinUsuario())
    headers = {"x-real-ip": "203.0.113.10"}

    for _ in range(auth_api.INTENTOS_MAXIMOS_POR_VENTANA):
        respuesta = client.post("/api/auth/login", json=_cuerpo_login(), headers=headers)
        assert respuesta.status_code == 401


def test_excede_el_limite_responde_429_sin_tocar_la_base_de_datos(monkeypatch):
    llamadas = {"n": 0}

    def _sesion_falsa_contando(_tenant_id: object) -> _SesionFalsaSinUsuario:
        llamadas["n"] += 1
        return _SesionFalsaSinUsuario()

    monkeypatch.setattr(auth_api, "abrir_sesion_tenant", _sesion_falsa_contando)
    headers = {"x-real-ip": "203.0.113.11"}

    for _ in range(auth_api.INTENTOS_MAXIMOS_POR_VENTANA):
        client.post("/api/auth/login", json=_cuerpo_login(), headers=headers)

    respuesta = client.post("/api/auth/login", json=_cuerpo_login(), headers=headers)

    assert respuesta.status_code == 429
    assert llamadas["n"] == auth_api.INTENTOS_MAXIMOS_POR_VENTANA


def test_ips_distintas_no_comparten_cupo(monkeypatch):
    monkeypatch.setattr(auth_api, "abrir_sesion_tenant", lambda _tenant_id: _SesionFalsaSinUsuario())

    for _ in range(auth_api.INTENTOS_MAXIMOS_POR_VENTANA):
        client.post("/api/auth/login", json=_cuerpo_login(), headers={"x-real-ip": "203.0.113.12"})

    respuesta_otra_ip = client.post(
        "/api/auth/login", json=_cuerpo_login(), headers={"x-real-ip": "203.0.113.13"}
    )

    assert respuesta_otra_ip.status_code == 401
