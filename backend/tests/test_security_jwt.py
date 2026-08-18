"""Cubre `create_access_token`/`decode_access_token` (app/core/security.py):
firma/verificación correctas, y que un token forjado con otra clave, sin los
claims registrados exigidos, o con otro emisor/audiencia, se rechace -- la
defensa de firma que hace inútil adivinar/filtrar el secreto sin además poder
firmar con él. El bypass real encontrado por Strix dependía de que el secreto
fuera público/adivinable (app/core/config.py ya lo cierra, ver test_config.py) y
de que app/api/deps.py confiara en los claims sin verificar contra la base de
datos (ver test_deps_auth.py) -- este archivo cubre la capa de firma en sí."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core import security
from app.core.security import create_access_token, decode_access_token


@pytest.fixture(autouse=True)
def _secreto_de_prueba(monkeypatch):
    monkeypatch.setattr(security.settings, "jwt_secret", "secreto-de-prueba-no-real")


def _token_valido() -> tuple[str, dict]:
    usuario_id, tenant_id = uuid4(), uuid4()
    token = create_access_token(usuario_id, tenant_id, "funcionario", "Intendencia de prueba", "uy")
    return token, {"usuario_id": usuario_id, "tenant_id": tenant_id}


def test_roundtrip_token_valido_decodifica_los_mismos_datos():
    token, datos = _token_valido()

    payload = decode_access_token(token)

    assert payload["sub"] == str(datos["usuario_id"])
    assert payload["tenant_id"] == str(datos["tenant_id"])
    assert payload["rol"] == "funcionario"


def test_token_firmado_con_otro_secreto_se_rechaza():
    token, _ = _token_valido()

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            token,
            "un-secreto-distinto",
            algorithms=["HS256"],
            issuer=security._JWT_ISSUER,
            audience=security._JWT_AUDIENCE,
        )


def test_token_sin_audience_se_rechaza():
    """Regresión directa contra el patrón de bypass: un token forjado con el
    secreto correcto pero sin `aud` (p. ej. emitido por otro servicio que
    comparte el secreto por error) no debe alcanzar app/api/deps.py."""
    payload_sin_aud = {
        "sub": str(uuid4()),
        "tenant_id": str(uuid4()),
        "rol": "funcionario",
        "iss": security._JWT_ISSUER,
        # sin "aud" a propósito
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token_sin_aud = jwt.encode(payload_sin_aud, "secreto-de-prueba-no-real", algorithm="HS256")

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token_sin_aud)


def test_token_de_otro_issuer_se_rechaza():
    token, _ = _token_valido()
    payload = jwt.decode(token, "secreto-de-prueba-no-real", algorithms=["HS256"], options={"verify_aud": False})
    payload["iss"] = "otro-servicio"
    token_otro_issuer = jwt.encode(payload, "secreto-de-prueba-no-real", algorithm="HS256")

    with pytest.raises(jwt.InvalidIssuerError):
        decode_access_token(token_otro_issuer)


def test_rotar_jwt_secret_invalida_tokens_ya_emitidos(monkeypatch):
    """Contrato de docs/runbook-despliegue.md ("Rotar JWT_SECRET"): cambiar el
    secreto invalida de inmediato todo lo emitido antes, sin ventana de gracia --
    a propósito, no hay soporte de doble secreto (ver esa sección para el porqué).
    Esta prueba es la red de seguridad si alguien intenta agregarlo sin leerla."""
    token, _ = _token_valido()

    monkeypatch.setattr(security.settings, "jwt_secret", "secreto-nuevo-tras-rotar")

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)
