"""Formatea el contexto institucional del gobierno (perfil, no por trámite) para
usarlo en dos lugares de la capa de IA que deben ver EXACTAMENTE el mismo texto:
el prompt de redacción (generador_plan.py) y el texto de referencia contra el que
se verifica que no se inventen cifras (verificador.py, verificador_citas.py). Si
no fueran el mismo texto, una cifra real del contexto (ej. presupuesto) se
rechazaría como inventada solo por no estar en los 5 campos fijos de la brecha.
"""

_ETIQUETAS_MONEDA = {"mx": "MXN", "uy": "UYU"}

# Solo las variables puramente descriptivas -- las que ya generan su propia
# brecha (autoridad_gobernanza_digital y las 5 agregadas después) no necesitan
# repetirse aquí, ya llegan a la narrativa a través de su propia acción.
_CAMPOS_CONTEXTO: tuple[tuple[str, str], ...] = (
    ("poblacion_total", "Población total"),
    ("personal_total_gobierno", "Personal total del gobierno"),
    ("presupuesto_tic_anual", "Presupuesto anual de TIC"),
    ("presupuesto_total_anual", "Presupuesto total anual del gobierno"),
    ("area_tic_existe", "¿Existe área de TIC formal?"),
    ("conectividad", "Conectividad de las oficinas"),
    ("normativa_local_emitida", "¿Normativa local de simplificación/digitalización emitida?"),
    ("numero_tramites_totales", "Número total de trámites que ofrece el gobierno"),
    ("ingresos_propios_porcentaje", "% de ingresos propios (vs. participaciones/transferencias)"),
    ("numero_oficinas_atencion", "Número de oficinas de atención al público"),
    ("personal_area_ti", "Personal del área de TI"),
    ("infraestructura_firma_electronica", "Infraestructura de firma electrónica avanzada"),
    # Migración 0009 -- madurez digital transversal, interoperabilidad,
    # ciberseguridad, capital humano de TI, medición, financiamiento, accesibilidad.
    ("portal_tramites_tipo", "Portal de trámites"),
    ("pagos_electronicos_generalizados", "¿Acepta pagos electrónicos de forma general?"),
    ("mecanismo_identidad_estandar", "Mecanismo de identidad digital estándar"),
    ("interoperabilidad_entre_areas", "¿Las áreas comparten información de forma automatizada?"),
    ("inventario_sistemas_existe", "¿Existe inventario de sistemas de información?"),
    ("politica_gobierno_datos_existe", "¿Existe política de gobierno de datos?"),
    ("respaldos_periodicos_existen", "¿Se realizan respaldos periódicos de información crítica?"),
    ("incidente_ciberseguridad_24meses", "¿Incidente de ciberseguridad en los últimos 24 meses?"),
    ("certificacion_seguridad_externa", "¿Cuenta con certificación/auditoría externa de seguridad?"),
    ("rotacion_personal_ti", "Rotación anual del personal de TI"),
    ("dependencia_outsourcing_ti", "¿Depende de outsourcing para sistemas críticos?"),
    ("mide_tiempos_resolucion", "¿Mide los tiempos de resolución de sus trámites?"),
    ("mide_satisfaccion_ciudadana", "¿Mide la satisfacción ciudadana?"),
    ("tablero_indicadores_existe", "¿Existe un tablero/reporte de indicadores de desempeño?"),
    ("fondos_digitalizacion_recibidos", "¿Ha recibido fondos etiquetados para digitalización (últimos 3 años)?"),
    ("fondos_digitalizacion_detalle", "Detalle de fondos de digitalización (monto/fuente)"),
    ("accesibilidad_sistemas_discapacidad", "¿Los sistemas cumplen estándares de accesibilidad?"),
    ("catalogo_tramites_propio_existe", "¿Cuenta con Registro/Catálogo de Trámites propio actualizado?"),
)

# Los 2 pares "porcentaje + no_se_mide" no encajan en el recorrido genérico de
# arriba: si el booleano es true, la línea debe decir "No se mide"/"No se tiene
# el dato" en vez del número -- una respuesta explícita, no la ausencia de una.
_CAMPOS_PORCENTAJE_CON_BANDERA: tuple[tuple[str, str, str, str], ...] = (
    (
        "porcentaje_tramites_en_linea",
        "porcentaje_tramites_en_linea_no_se_mide",
        "% del catálogo de trámites 100% en línea",
        "No se mide",
    ),
    (
        "porcentaje_poblacion_acceso_internet",
        "porcentaje_poblacion_acceso_internet_no_se_tiene_dato",
        "% de la población con acceso a internet/smartphone",
        "No se tiene el dato",
    ),
)

_CAMPOS_MONEDA = frozenset({"presupuesto_tic_anual", "presupuesto_total_anual"})


def _formatear_valor(clave: str, valor: object, pais: str) -> str:
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if clave in _CAMPOS_MONEDA:
        moneda = _ETIQUETAS_MONEDA.get(pais, "")
        return f"{valor} {moneda}".strip()
    if clave == "ingresos_propios_porcentaje":
        return f"{valor}%"
    return str(valor)


def formatear_contexto_gobierno(respuestas: dict, pais: str) -> str:
    """Un renglón por cada campo que el tenant ya llenó -- nunca inventa "no
    disponible" para el resto, simplemente los omite. Devuelve "" si ninguno está
    disponible (caso más común hoy: la mayoría de gobiernos reales apenas están
    llenando su perfil) -- en ese caso no se agrega ninguna sección ni al prompt
    ni a la referencia de verificación."""
    lineas = [
        f"- {etiqueta}: {_formatear_valor(clave, respuestas[clave], pais)}"
        for clave, etiqueta in _CAMPOS_CONTEXTO
        if respuestas.get(clave) is not None
    ]
    for clave_valor, clave_bandera, etiqueta, texto_no_medido in _CAMPOS_PORCENTAJE_CON_BANDERA:
        if respuestas.get(clave_bandera):
            lineas.append(f"- {etiqueta}: {texto_no_medido}")
        elif respuestas.get(clave_valor) is not None:
            lineas.append(f"- {etiqueta}: {respuestas[clave_valor]}%")
    return "\n".join(lineas)
