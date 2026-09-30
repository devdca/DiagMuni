"""PDF combinado del plan (ejecutivo + técnico) -- mismo contenido y orden que
Plan.tsx, sin ningún LLM, puramente formato sobre datos ya generados.
"""

from datetime import UTC, datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.schemas.plan import PlanOut

_REEMPLAZOS_LATIN1 = {
    "–": "-",
    "—": "--",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "→": "->",
    "…": "...",
}


def _sanitizar_para_pdf(texto: str) -> str:
    """Las fuentes core de fpdf2 (Helvetica) solo soportan Latin-1 y lanzan una
    excepción ante cualquier carácter fuera de rango -- el texto libre de LLM
    (narrativa, sugerencia_libre, estimacion_recursos) puede traer comillas
    curvas, em-dash, flechas, etc. Se reemplazan los casos conocidos y, como red
    de seguridad final, cualquier otro carácter fuera de Latin-1 se degrada a
    "?" en vez de tumbar la generación del PDF."""
    for original, reemplazo in _REEMPLAZOS_LATIN1.items():
        texto = texto.replace(original, reemplazo)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def _monto(valor: str | None, moneda: str) -> str:
    return f"{valor} {moneda}" if valor is not None else "Sin dato verificado"


class _PlanPDF(FPDF):
    def _linea(self, texto: str, h: float) -> None:
        # new_x=LMARGIN explícito: sin esto multi_cell no resetea la x al margen
        # y la siguiente llamada revienta por falta de ancho.
        self.multi_cell(0, h, _sanitizar_para_pdf(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def titulo_seccion(self, texto: str) -> None:
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(0, 0, 0)
        self._linea(texto, 9)
        self.ln(2)

    def subtitulo(self, texto: str) -> None:
        self.set_font("Helvetica", "B", 12)
        self._linea(texto, 7)
        self.ln(1)

    def parrafo(self, texto: str) -> None:
        self.set_font("Helvetica", "", 10)
        self._linea(texto, 5.5)
        self.ln(2)

    def etiqueta_valor(self, etiqueta: str, valor: str) -> None:
        self.set_font("Helvetica", "B", 10)
        self._linea(f"{etiqueta}:", 5.5)
        self.set_font("Helvetica", "", 10)
        self._linea(valor, 5.5)
        self.ln(1)

    def aviso(self, texto: str) -> None:
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(140, 90, 0)
        self._linea(texto, 5)
        self.set_text_color(0, 0, 0)
        self.ln(2)


def _seccion_ejecutiva(pdf: _PlanPDF, plan: PlanOut) -> None:
    contenido = plan.contenido
    pdf.titulo_seccion("Resumen ejecutivo")

    if plan.indice_madurez is not None:
        pdf.etiqueta_valor("Índice de madurez actual", str(plan.indice_madurez))
    pdf.parrafo(contenido["resumen_narrativo"])

    if plan.progreso_historico is not None:
        progreso = plan.progreso_historico
        pdf.subtitulo("Progreso desde el diagnóstico anterior")
        if progreso["brechas_resueltas"]:
            pdf.etiqueta_valor("Brechas resueltas", ", ".join(progreso["brechas_resueltas"]))
        if progreso["brechas_nuevas"]:
            pdf.etiqueta_valor("Brechas nuevas", ", ".join(progreso["brechas_nuevas"]))
        pdf.ln(2)

    inversion = contenido["resumen_inversion"]
    pdf.subtitulo("Presupuesto estimado")
    pdf.etiqueta_valor(
        "Inversión única estimada",
        _monto(inversion["inversion_unica_estimada"]["moneda_local"], inversion["moneda_local_codigo"]),
    )
    pdf.etiqueta_valor(
        "Costo recurrente mensual estimado",
        _monto(inversion["costo_recurrente_mensual_estimado"]["moneda_local"], inversion["moneda_local_codigo"]),
    )
    for componente in inversion["componentes"]:
        pdf.etiqueta_valor(
            f"Componente: {componente['nombre_componente']}",
            f"licencia {componente['licencia']}, licenciamiento "
            f"{componente['costo_licenciamiento']['moneda_local']}, infraestructura "
            f"{componente['costo_infraestructura']['moneda_local']}, implementación "
            f"{componente['costo_implementacion']['moneda_local']}",
        )
    pdf.parrafo(inversion["nota_cobertura"])

    personal = contenido["resumen_personal"]
    pdf.subtitulo("Personal y capacitación")
    pdf.etiqueta_valor(
        "Personal actual del área de TI",
        str(personal["personal_ti_actual"]) if personal["personal_ti_actual"] is not None else "No capturado",
    )
    if personal["costo_referencia_personal_ti"] is not None:
        ref = personal["costo_referencia_personal_ti"]
        valor = (
            "Sin fuente oficial verificada"
            if ref["salario_mensual_promedio"] == "[NO VERIFICADO]"
            else f"{ref['salario_mensual_promedio']} {ref['moneda']}/mes ({ref['puesto_referencia']})"
        )
        pdf.etiqueta_valor("Costo de referencia de 1 puesto de TI", valor)
    for accion in personal["acciones_organizacionales"]:
        pdf.parrafo(f"- {accion}")

    if contenido["estimacion_recursos"] is not None:
        estimacion = contenido["estimacion_recursos"]
        pdf.subtitulo("Estimación aproximada de personal y presupuesto")
        pdf.parrafo(estimacion["texto"])
        pdf.aviso(estimacion["advertencia"])

    if contenido["sugerencia_libre"] is not None:
        sugerencia = contenido["sugerencia_libre"]
        pdf.subtitulo("Sugerencia a partir de la descripción del trámite")
        pdf.parrafo(sugerencia["texto"])
        pdf.aviso(sugerencia["advertencia"])

    brechas = contenido["brechas"]
    if brechas:
        pdf.subtitulo(f"Brechas detectadas ({len(brechas)})")
        for brecha in brechas:
            pdf.parrafo(f"[{brecha['categoria_catalogo']}] {brecha['narrativa']}")
    else:
        pdf.parrafo("No hay brechas pendientes: todas las variables evaluadas ya cumplen el nivel máximo.")


def _seccion_tecnica(pdf: _PlanPDF, plan: PlanOut) -> None:
    pdf.add_page()
    pdf.titulo_seccion("Detalle técnico")

    for brecha in plan.contenido["brechas"]:
        pdf.subtitulo(brecha["variable"])
        pdf.etiqueta_valor("Paso administrativo", brecha["paso_administrativo"])
        pdf.etiqueta_valor("Paso técnico", brecha["paso_tecnico"])
        pdf.etiqueta_valor("Paso organizacional", brecha["paso_organizacional"])
        if brecha["prerrequisitos"]:
            pdf.etiqueta_valor("Prerrequisitos", ", ".join(brecha["prerrequisitos"]))
        pdf.etiqueta_valor("Fuente normativa", brecha["fuente_normativa"])

        componente = brecha.get("componente_recomendado")
        if componente is not None:
            pdf.etiqueta_valor(
                "Componente recomendado",
                f"{componente['nombre_componente']} ({componente['licencia']}) -- "
                f"{componente['url_repositorio']}",
            )
        pdf.ln(3)


def generar_pdf_plan(plan: PlanOut, nombre_gobierno: str) -> bytes:
    pdf = _PlanPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf._linea("Plan de modernización", 10)
    pdf.set_font("Helvetica", "", 11)
    pdf._linea(nombre_gobierno, 6)
    fecha = datetime.now(UTC).strftime("%d/%m/%Y")
    pdf._linea(f"Generado el {fecha} -- versión {plan.version} ({plan.modo})", 6)
    pdf.ln(4)

    _seccion_ejecutiva(pdf, plan)
    _seccion_tecnica(pdf, plan)

    return bytes(pdf.output())
