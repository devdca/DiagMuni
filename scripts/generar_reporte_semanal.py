"""Genera un borrador de reporte semanal consolidado a partir de las
bitácoras de sesión en sesiones/ (ver sesiones/README.md).

`sesiones/` está en .gitignore ("material interno, no producto") -- este
script y sus rutas son de código público, pero el contenido que lee y
escribe nunca se comitea.

No resume ni interpreta el contenido -- solo recopila las sesiones cuya
fecha cae en el rango pedido y arma el esqueleto del reporte (incluido el
contenido íntegro de cada sesión como referencia). Las secciones "Resumen
ejecutivo", "Avances por área" y "Pendientes para la próxima semana" se
completan después, a mano o pidiéndole a Claude Code que lo haga a partir
del borrador.

Uso:
  python scripts/generar_reporte_semanal.py
  # rango explícito (7 días terminando en --hasta, por default hoy):
  python scripts/generar_reporte_semanal.py --hasta 2026-09-13 --dias 7
"""

import argparse
import re
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_SESIONES = RAIZ / "sesiones"
DIR_REPORTES = RAIZ / "sesiones" / "reportes-semanales"

_RE_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.S)
_RE_NOMBRE_SESION = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")


def _parsear_frontmatter(texto: str) -> tuple[dict[str, str], str]:
    coincidencia = _RE_FRONTMATTER.match(texto)
    if not coincidencia:
        return {}, texto
    bloque, cuerpo = coincidencia.groups()
    campos = {}
    for linea in bloque.splitlines():
        clave, separador, valor = linea.partition(":")
        if separador:
            campos[clave.strip()] = valor.strip()
    return campos, cuerpo.strip()


def _cargar_sesiones(desde: date, hasta: date) -> list[tuple[date, Path, dict[str, str], str]]:
    sesiones = []
    if not DIR_SESIONES.exists():
        return sesiones
    for archivo in sorted(DIR_SESIONES.glob("*.md")):
        if not _RE_NOMBRE_SESION.match(archivo.name):
            continue
        campos, cuerpo = _parsear_frontmatter(archivo.read_text(encoding="utf-8"))
        fecha_str = campos.get("fecha", "")
        try:
            fecha = date.fromisoformat(fecha_str)
        except ValueError:
            print(f"Aviso: {archivo.name} no tiene un campo 'fecha' válido (YYYY-MM-DD); se omite.")
            continue
        if desde <= fecha <= hasta:
            sesiones.append((fecha, archivo, campos, cuerpo))
    sesiones.sort(key=lambda s: s[0])
    return sesiones


def generar_reporte(desde: date, hasta: date) -> tuple[Path, list]:
    sesiones = _cargar_sesiones(desde, hasta)
    anio, semana, _ = hasta.isocalendar()
    etiqueta = f"{anio}-W{semana:02d}"
    destino = DIR_REPORTES / f"{etiqueta}.md"

    lineas = [
        "---",
        f"semana: {etiqueta}",
        f"rango: {desde.isoformat()} a {hasta.isoformat()}",
        f"generado: {date.today().isoformat()}",
        "---",
        "",
        f"# Reporte semanal — {desde.isoformat()} a {hasta.isoformat()}",
        "",
        "## Resumen ejecutivo",
        "",
        "_(completar: 2-4 líneas con el avance más relevante de la semana)_",
        "",
        "## Sesiones incluidas",
        "",
    ]

    if sesiones:
        for fecha, archivo, campos, _ in sesiones:
            resumen = campos.get("resumen") or "(sin resumen)"
            autor = campos.get("autor") or "?"
            ruta = archivo.relative_to(RAIZ).as_posix()
            lineas.append(f"- **{fecha.isoformat()}** ({autor}) — {resumen} · `{ruta}`")
    else:
        lineas.append("_No se encontraron bitácoras de sesión en este rango._")

    lineas += [
        "",
        "## Avances por área",
        "",
        "_(completar: backend / frontend / seguridad / documentación)_",
        "",
        "## Pendientes para la próxima semana",
        "",
        "_(completar)_",
        "",
    ]

    if sesiones:
        lineas += ["## Detalle de las sesiones (contenido íntegro)", ""]
        for fecha, archivo, _campos, cuerpo in sesiones:
            lineas.append(f"<details>\n<summary>{fecha.isoformat()} — {archivo.name}</summary>\n")
            lineas.append(cuerpo)
            lineas.append("\n</details>\n")

    DIR_REPORTES.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino, sesiones


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un borrador de reporte semanal a partir de las bitácoras en docs/bitacora/sesiones/."
    )
    parser.add_argument("--hasta", help="Fecha final del rango, YYYY-MM-DD (default: hoy).")
    parser.add_argument("--dias", type=int, default=7, help="Tamaño del rango hacia atrás desde --hasta (default: 7).")
    args = parser.parse_args()

    hasta = date.fromisoformat(args.hasta) if args.hasta else date.today()
    desde = hasta - timedelta(days=args.dias - 1)

    destino, sesiones = generar_reporte(desde, hasta)
    print(f"Reporte generado en: {destino.relative_to(RAIZ).as_posix()}")
    print(f"Sesiones incluidas: {len(sesiones)}")
    if not sesiones:
        print(
            "Aviso: no se encontró ninguna bitácora de sesión en "
            "docs/bitacora/sesiones/ dentro del rango indicado."
        )


if __name__ == "__main__":
    main()
