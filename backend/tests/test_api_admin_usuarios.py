"""Tests de `requerir_admin` (app/adaptadores/http/deps.py) -- dependencia pura,
solo mira `token.rol`, sin tocar la base de datos. Los tests de los endpoints de
`app/adaptadores/http/admin_usuarios.py` contra Postgres real viven en
test_api_admin_usuarios_postgres.py."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.adaptadores.http.deps import TokenData, requerir_admin


def test_requerir_admin_rechaza_rol_funcionario():
    token = TokenData(usuario_id=uuid4(), tenant_id=uuid4(), rol="funcionario")
    with pytest.raises(HTTPException) as exc_info:
        requerir_admin(token)
    assert exc_info.value.status_code == 403


def test_requerir_admin_acepta_rol_admin_gobierno():
    token = TokenData(usuario_id=uuid4(), tenant_id=uuid4(), rol="admin_gobierno")
    assert requerir_admin(token) is token
