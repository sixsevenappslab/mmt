"""Practice harness: verifiable exercises and a prediction ledger.

Each lesson may ship an `ejercicios.py` next to its `LECCION.md` defining EJERCICIOS,
a list of `Ejercicio`. This module runs them and records every answer in
`.progreso/predicciones.md`, so the learner's calibration is measurable over the course.

Design rules, in order of importance:

1. **An exercise never hardcodes the expected value.** It computes it from ground truth
   (`data/synthetic/*.truth.json`) or from stored model output (`experiments/*/results/
   */summary.json`). If a library version moves the numbers, the check moves with them.
2. **A failed check never leaks the answer.** It returns a hint that points at where to
   look. The tutor agent must not paraphrase the expected value either.
3. **Standard library only**, so it runs under any of the venvs in .venvs/.

Usage (from the repo root):

    python3 lecciones/practica.py 03 --listar
    python3 lecciones/practica.py 03 e1 --valor video
    python3 lecciones/practica.py 03 --estado
    python3 lecciones/practica.py --calibracion
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import importlib.util
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LECCIONES = ROOT / "lecciones"
PROGRESO = ROOT / ".progreso"
LEDGER = PROGRESO / "predicciones.md"

LEDGER_HEADER = """# Registro de predicciones

Una fila por respuesta a un ejercicio. Lo rellena `lecciones/practica.py`, no lo edites a
mano. Sirve para una sola cosa: medir tu calibración a lo largo del curso. Fallar aquí es
información, no una nota.

| fecha | lección | ejercicio | tu respuesta | acierto |
|---|---|---|---|---|
"""


# --------------------------------------------------------------------- modelo ----


@dataclass
class Resultado:
    """Outcome of one check. `mensaje` must never contain the expected value."""

    ok: bool
    mensaje: str = ""


@dataclass
class Ejercicio:
    id: str
    enunciado: str
    comprobar: Callable[[Any], Resultado]
    tipo: str = "texto"  # texto | numero | eleccion
    opciones: list[str] = field(default_factory=list)
    pista: str = ""
    requiere: str = ""  # human-readable precondition, shown when the check cannot run


class NoSePuedeComprobar(Exception):
    """Raised by a check when the inputs it needs are not there yet."""


# ------------------------------------------------------------------ ayudantes ----


def aprox(valor: float, esperado: float, tol_rel: float = 0.1, tol_abs: float = 0.0) -> Resultado:
    """Numeric comparison. Passes within max(tol_rel * |esperado|, tol_abs)."""
    margen = max(abs(esperado) * tol_rel, tol_abs)
    return Resultado(abs(valor - esperado) <= margen)


def igual(valor: str, esperado: str) -> Resultado:
    return Resultado(_norm(valor) == _norm(esperado))


def _norm(s: str) -> str:
    s = str(s).strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        s = s.replace(a, b)
    return s


def a_numero(valor: str) -> float:
    """Accept 0.78, 0,78 and '78 %' alike. Raises ValueError when it is not a number."""
    s = str(valor).strip().replace("%", "").replace(",", ".")
    return float(s)


def cargar_json(ruta: Path) -> dict:
    if not ruta.exists():
        raise NoSePuedeComprobar(f"falta {ruta.relative_to(ROOT) if ROOT in ruta.parents else ruta}")
    return json.loads(ruta.read_text())


def cargar_csv(ruta: Path) -> list[dict]:
    if not ruta.exists():
        raise NoSePuedeComprobar(f"falta {ruta}")
    with ruta.open() as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------- carga ----


def dir_leccion(nn: str) -> Path:
    nn = nn.zfill(2)
    candidatos = sorted(LECCIONES.glob(f"{nn}-*"))
    if not candidatos:
        raise SystemExit(f"no encuentro la lección {nn} en {LECCIONES}/")
    return candidatos[0]


def cargar_ejercicios(nn: str) -> tuple[Path, list[Ejercicio]]:
    d = dir_leccion(nn)
    fichero = d / "ejercicios.py"
    if not fichero.exists():
        raise SystemExit(f"la lección {d.name} todavía no tiene ejercicios.py")
    # so that ejercicios.py can do `from practica import ...`
    if str(LECCIONES) not in sys.path:
        sys.path.insert(0, str(LECCIONES))
    spec = importlib.util.spec_from_file_location(f"ejercicios_{nn}", fichero)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return d, list(mod.EJERCICIOS)


# --------------------------------------------------------------------- ledger ----


def anotar(nn: str, ejercicio: str, respuesta: str, ok: bool) -> None:
    PROGRESO.mkdir(exist_ok=True)
    if not LEDGER.exists():
        LEDGER.write_text(LEDGER_HEADER)
    fecha = _dt.datetime.now(tz=_dt.UTC).date().isoformat()
    limpia = str(respuesta).replace("|", "/").strip()
    with LEDGER.open("a") as fh:
        fh.write(f"| {fecha} | {nn.zfill(2)} | {ejercicio} | {limpia} | {'sí' if ok else 'no'} |\n")


def leer_ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    filas = []
    for linea in LEDGER.read_text().splitlines():
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) != 5 or celdas[0] in ("fecha", "---"):
            continue
        if not re.match(r"\d{4}-\d{2}-\d{2}$", celdas[0]):
            continue
        filas.append(
            {"fecha": celdas[0], "leccion": celdas[1], "ejercicio": celdas[2],
             "respuesta": celdas[3], "ok": celdas[4] == "sí"}
        )
    return filas


def estado_leccion(nn: str) -> dict[str, bool]:
    """Best result per exercise: an exercise counts as passed if it ever passed."""
    hecho: dict[str, bool] = {}
    for f in leer_ledger():
        if f["leccion"] == nn.zfill(2):
            hecho[f["ejercicio"]] = hecho.get(f["ejercicio"], False) or f["ok"]
    return hecho


# ------------------------------------------------------------------------ cli ----


def _listar(nn: str, ejercicios: list[Ejercicio]) -> None:
    hecho = estado_leccion(nn)
    print(f"Ejercicios de la lección {nn.zfill(2)}:\n")
    for e in ejercicios:
        marca = "✓" if hecho.get(e.id) else ("·" if e.id not in hecho else "✗")
        print(f"  {marca} {e.id}  {e.enunciado}")
        if e.opciones:
            print(f"      opciones: {', '.join(e.opciones)}")
        if e.requiere:
            print(f"      requiere: {e.requiere}")
    print(f"\nResponder:  python3 lecciones/practica.py {nn} <id> --valor <respuesta>")


def _estado(nn: str, ejercicios: list[Ejercicio]) -> int:
    hecho = estado_leccion(nn)
    ok = sum(1 for e in ejercicios if hecho.get(e.id))
    print(f"Lección {nn.zfill(2)}: {ok}/{len(ejercicios)} ejercicios superados")
    for e in ejercicios:
        print(f"  {'✓' if hecho.get(e.id) else '·'} {e.id}")
    return 0 if ok == len(ejercicios) else 1


def _calibracion() -> int:
    filas = leer_ledger()
    if not filas:
        print("Todavía no hay predicciones anotadas.")
        return 0
    print(f"Predicciones anotadas: {len(filas)}")
    aciertos = sum(1 for f in filas if f["ok"])
    print(f"Aciertos al primer o siguiente intento: {aciertos}/{len(filas)}")
    primeras: dict[tuple[str, str], bool] = {}
    for f in filas:
        clave = (f["leccion"], f["ejercicio"])
        primeras.setdefault(clave, f["ok"])
    ok1 = sum(1 for v in primeras.values() if v)
    print(f"Aciertos a la primera: {ok1}/{len(primeras)}  <- esta es tu calibración real")
    por_leccion: dict[str, list[bool]] = {}
    for (lec, _), v in primeras.items():
        por_leccion.setdefault(lec, []).append(v)
    print("\nPor lección (a la primera):")
    for lec in sorted(por_leccion):
        vs = por_leccion[lec]
        print(f"  {lec}: {sum(vs)}/{len(vs)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("leccion", nargs="?", help="número de lección, p. ej. 03")
    p.add_argument("ejercicio", nargs="?", help="id del ejercicio, p. ej. e1")
    p.add_argument("--valor", help="tu respuesta")
    p.add_argument("--listar", action="store_true", help="lista los ejercicios")
    p.add_argument("--estado", action="store_true", help="cuántos llevas superados")
    p.add_argument("--calibracion", action="store_true", help="tu acierto a la primera")
    args = p.parse_args()

    if args.calibracion:
        return _calibracion()
    if not args.leccion:
        p.error("indica una lección (o usa --calibracion)")

    _, ejercicios = cargar_ejercicios(args.leccion)

    if args.listar or (not args.ejercicio and not args.estado):
        _listar(args.leccion, ejercicios)
        return 0
    if args.estado:
        return _estado(args.leccion, ejercicios)

    elegido = next((e for e in ejercicios if e.id == args.ejercicio), None)
    if elegido is None:
        raise SystemExit(f"no existe el ejercicio {args.ejercicio}")
    if args.valor is None:
        p.error("falta --valor con tu respuesta")
    if elegido.opciones and _norm(args.valor) not in [_norm(o) for o in elegido.opciones]:
        print(f"Respuesta fuera de las opciones: {', '.join(elegido.opciones)}")
        return 2

    try:
        res = elegido.comprobar(args.valor)
    except NoSePuedeComprobar as exc:
        print(f"Todavía no puedo comprobarlo: {exc}")
        if elegido.requiere:
            print(f"Requiere: {elegido.requiere}")
        return 2
    except (ValueError, TypeError):
        print("No entiendo esa respuesta. Si el ejercicio pide un número, escribe solo el número.")
        return 2

    anotar(args.leccion, elegido.id, args.valor, res.ok)
    if res.ok:
        print(f"✓ correcto ({elegido.id})")
        if res.mensaje:
            print(f"  {res.mensaje}")
    else:
        print(f"✗ no es eso ({elegido.id})")
        print(f"  pista: {res.mensaje or elegido.pista}")
        print("  vuelve a intentarlo cuando lo hayas mirado; queda anotado igual")
    return 0 if res.ok else 1


if __name__ == "__main__":
    # Lessons import `practica`, so running this file as a script would create a second
    # copy of the module: the exception classes raised in ejercicios.py would not be the
    # ones caught here. Re-enter through the canonical import so identities match.
    if "practica" not in sys.modules:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import practica

        sys.exit(practica.main())
    sys.exit(main())
