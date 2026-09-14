import pytest
from pydantic import ValidationError

from app.schemas.tramite import TramiteCreate


def test_tipo_default_es_generico():
    tramite = TramiteCreate(nombre="Trámite de prueba")
    assert tramite.tipo == "generico"


def test_tipo_valido_se_acepta():
    tramite = TramiteCreate(nombre="Trámite de prueba", tipo="registro_civil")
    assert tramite.tipo == "registro_civil"


def test_tipo_inexistente_se_rechaza():
    with pytest.raises(ValidationError, match="no está en el catálogo"):
        TramiteCreate(nombre="Trámite de prueba", tipo="no-existe")
