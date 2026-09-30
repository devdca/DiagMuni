"""Tests de validación de entrada de `app/aplicacion/gestion_usuarios.py::crear_usuario`
-- corren antes de tocar la sesión, sin Postgres (mismo criterio que
test_bootstrap_tenant.py sección 2). Los tests contra Postgres real (alta,
desactivar/reactivar, cambiar rol, el guard de "último administrador activo",
autoservicio) viven en test_gestion_usuarios_postgres.py."""

from uuid import uuid4

import pytest

from app.aplicacion import gestion_usuarios


class _SesionQueRevienta:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("crear_usuario no debía consultar la sesión: la validación debía rechazar antes")


def test_crear_usuario_rechaza_nombre_vacio():
    with pytest.raises(ValueError, match="nombre no puede"):
        gestion_usuarios.crear_usuario(
            _SesionQueRevienta(), tenant_id=uuid4(), email="func@prueba.mx", nombre="  ", rol="funcionario"
        )


def test_crear_usuario_rechaza_email_invalido():
    with pytest.raises(ValueError, match="formato válido"):
        gestion_usuarios.crear_usuario(
            _SesionQueRevienta(), tenant_id=uuid4(), email="no-es-un-email", nombre="Func", rol="funcionario"
        )


def test_crear_usuario_rechaza_rol_invalido():
    with pytest.raises(ValueError, match="no válido"):
        gestion_usuarios.crear_usuario(
            _SesionQueRevienta(), tenant_id=uuid4(), email="func@prueba.mx", nombre="Func", rol="superadmin"
        )
