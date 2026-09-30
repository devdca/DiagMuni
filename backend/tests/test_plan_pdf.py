import io
from datetime import UTC, datetime
from uuid import uuid4

from pypdf import PdfReader

from app.adaptadores.pdf.plan_pdf import _sanitizar_para_pdf, generar_pdf_plan
from app.schemas.plan import PlanOut

_COMPONENTE = {
    "nombre_componente": "Mayan EDMS",
    "licencia": "Apache-2.0",
    "url_repositorio": "https://github.com/mayan-edms/Mayan-EDMS",
    "moneda_local_codigo": "MXN",
    "costo_licenciamiento": {"moneda_local": "0", "usd": "0"},
    "costo_infraestructura": {"moneda_local": "114.55/mes", "usd": "6.60/mes"},
    "costo_implementacion": {"moneda_local": "[NO VERIFICADO]", "usd": "[NO VERIFICADO]"},
    "nota_advertencia": None,
    "fuente_licencia": "https://example.org/licencia",
    "fuente_actividad": "https://example.org/actividad",
    "fuente_costo": "https://example.org/costo",
    "fecha_verificacion": "2026-08-03",
}

_BRECHA = {
    "variable": "documentos_digitalizados",
    "narrativa": "Digitalizar el expediente del trámite conforme a la normativa vigente.",
    "paso_administrativo": "Digitalizar el expediente completo",
    "paso_tecnico": "Implementar un gestor de expediente electrónico",
    "paso_organizacional": "Capacitar al personal de archivo",
    "prerrequisitos": [],
    "por_que_importa": "Es el primer paso de digitalización",
    "fuente_normativa": "LNETB art. 16",
    "categoria_catalogo": "gestor_expediente_electronico",
    "componente_recomendado": _COMPONENTE,
}

_BRECHA_SIN_COMPONENTE = {
    "variable": "gobernanza_institucional",
    "narrativa": "Constituir la Autoridad Local de Simplificación y Digitalización.",
    "paso_administrativo": "Constituir la Autoridad",
    "paso_tecnico": "No aplica un componente tecnológico específico",
    "paso_organizacional": "Formalizar el mandato",
    "prerrequisitos": ["Documentos digitalizados"],
    "por_que_importa": "Es el interlocutor institucional",
    "fuente_normativa": "LNETB art. 11",
    "categoria_catalogo": "gobernanza_institucional",
    "componente_recomendado": None,
}


def _contenido(brechas: list[dict], **overrides: object) -> dict:
    base = {
        "resumen_narrativo": "Se detectaron 2 brecha(s) de modernización.",
        "brechas": brechas,
        "sugerencia_libre": None,
        "resumen_inversion": {
            "moneda_local_codigo": "MXN",
            "inversion_unica_estimada": {"moneda_local": "0", "usd": "0"},
            "costo_recurrente_mensual_estimado": {"moneda_local": "114.55", "usd": "6.60"},
            "componentes": [_COMPONENTE] if brechas else [],
            "brechas_totales": len(brechas),
            "brechas_con_componente_software": sum(1 for b in brechas if b.get("componente_recomendado")),
            "nota_cobertura": "Solo se suman montos verificados.",
        },
        "resumen_personal": {
            "acciones_organizacionales": ["Capacitar al personal de archivo"],
            "personal_ti_actual": 3,
            "personal_total_gobierno": 40,
            "capacitacion_anual_vigente": True,
            "costo_referencia_personal_ti": {
                "puesto_referencia": "Especialista en sistemas computacionales",
                "salario_mensual_promedio": "21318",
                "moneda": "MXN",
                "fuente": "Data México",
                "fecha_consulta": "2026-09-08",
            },
        },
        "orden_sugerido": {"sin_prerrequisitos": ["documentos_digitalizados"], "con_prerrequisitos": []},
        "estimacion_recursos": None,
    }
    base.update(overrides)
    return base


def _plan_de_prueba(contenido: dict, **overrides: object) -> PlanOut:
    base: dict[str, object] = {
        "id": uuid4(),
        "diagnostico_tramite_id": uuid4(),
        "version": 1,
        "modo": "degradado",
        "contenido": contenido,
        "verificado": True,
        "generado_en": datetime.now(UTC),
        "indice_madurez": 2,
        "progreso_historico": None,
    }
    base.update(overrides)
    return PlanOut(**base)


def _extraer_texto(pdf_bytes: bytes) -> str:
    lector = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(pagina.extract_text() for pagina in lector.pages)


def test_pdf_incluye_ambas_secciones_y_contenido_clave():
    plan = _plan_de_prueba(_contenido([_BRECHA, _BRECHA_SIN_COMPONENTE]))

    pdf_bytes = generar_pdf_plan(plan, "Alcaldía de Prueba")

    assert pdf_bytes.startswith(b"%PDF")
    texto = _extraer_texto(pdf_bytes)
    assert "Alcaldía de Prueba" in texto
    assert "Resumen ejecutivo" in texto
    assert "Detalle técnico" in texto
    assert "Se detectaron 2 brecha(s)" in texto
    assert "Digitalizar el expediente completo" in texto
    assert "Mayan EDMS" in texto


def test_pdf_sin_brechas_no_falla():
    plan = _plan_de_prueba(_contenido([]))

    pdf_bytes = generar_pdf_plan(plan, "Alcaldía de Prueba")

    assert pdf_bytes.startswith(b"%PDF")
    assert "No hay brechas pendientes" in _extraer_texto(pdf_bytes)


def test_pdf_incluye_estimacion_recursos_y_progreso_historico():
    contenido = _contenido(
        [_BRECHA],
        estimacion_recursos={"texto": "Estimación aproximada de prueba.", "advertencia": "No verificado."},
    )
    plan = _plan_de_prueba(
        contenido,
        version=2,
        progreso_historico={
            "brechas_resueltas": ["motor_pagos"],
            "brechas_nuevas": ["version_accesible"],
            "brechas_persistentes": [],
        },
    )

    texto = _extraer_texto(generar_pdf_plan(plan, "Alcaldía de Prueba"))

    assert "Estimación aproximada de prueba." in texto
    assert "motor_pagos" in texto
    assert "version_accesible" in texto


def test_sanitizar_para_pdf_reemplaza_caracteres_conocidos():
    resultado = _sanitizar_para_pdf("texto—con “comillas” y flecha → fin…")

    assert resultado == 'texto--con "comillas" y flecha -> fin...'


def test_sanitizar_para_pdf_degrada_caracter_desconocido_sin_lanzar():
    resultado = _sanitizar_para_pdf("emoji \U0001f600 fin")

    assert "?" in resultado
    assert "fin" in resultado
