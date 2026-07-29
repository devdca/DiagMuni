"""Cálculo del índice de madurez (F2), puro y determinista — docs/PRD.md define los
5 niveles: 0 presencial en papel, 1 informativo, 2 transaccional parcial,
3 transaccional completo, 4 proactivo e interoperable.

Regla de versionado (docs/TRD.md): cambiar esta lógica exige subir VERSION_MOTOR;
un diagnóstico ya persistido nunca se recalcula con una versión distinta a la que
lo produjo (docs/backend-schema.md, campo version_motor).
"""

VERSION_MOTOR = "1.0"


def calcular_indice_madurez(respuestas: dict) -> int:
    """Deriva el índice a partir de las 4 variables que la matriz brecha->acción liga
    a un nivel específico (ver "por qué importa" en cada YAML de engine/reglas/):

    - documentos_digitalizados en false bloquea todo (índice 0) — es prerrequisito
      de cualquier transaccionalidad (documentos_papel_digital.yaml).
    - motor_pagos y firma_electronica_habilitada bloquean, cada una, el paso a
      índice 3 (transaccional completo) — con solo una de las dos, queda en
      "transaccional parcial" (índice 2), no en 0/1.
    - interoperabilidad y mecanismo_identidad (distinto de "ninguno") son requisito
      de índice 4 (proactivo e interoperable), solo alcanzable habiendo llegado a 3.

    proteccion_datos_incompleta NO participa aquí: es transversal (datos_personales.yaml),
    no gatilla un nivel específico del índice.
    """
    if not respuestas.get("documentos_digitalizados", False):
        return 0

    tiene_pagos = bool(respuestas.get("motor_pagos", False))
    tiene_firma = bool(respuestas.get("firma_electronica_habilitada", False))

    if tiene_pagos and tiene_firma:
        indice = 3
    elif tiene_pagos or tiene_firma:
        indice = 2
    else:
        indice = 1

    if indice == 3:
        tiene_interop = bool(respuestas.get("interoperabilidad", False))
        tiene_identidad = respuestas.get("mecanismo_identidad", "ninguno") != "ninguno"
        if tiene_interop and tiene_identidad:
            indice = 4

    return indice
