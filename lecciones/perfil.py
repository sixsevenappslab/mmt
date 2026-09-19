from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = Path(".mmt/perfil.json")
SCHEMA_VERSION = 1
EXPERIENCES = {"principiante", "marketing", "analitica", "investigacion", "no_se"}
INTERESTS = {"mmm", "experimentos", "encuestas", "atribucion", "bibliotecas"}
GOALS = {"fundamentos", "evaluar_campanas", "repartir_presupuesto", "incrementalidad", "explorar_librerias", "no_se"}
PREFERENCES = {"visual", "conversacional", "video_corto", "video_largo"}
PACES = {"suave", "sostenido", "intensivo", "no_se"}
TARGET_MODULE = {
    "mmm": 3,
    "experimentos": 5,
    "encuestas": 2,
    "atribucion": 10,
    "bibliotecas": 0,
}
GOAL_TARGET = {
    "fundamentos": 0,
    "evaluar_campanas": 3,
    "repartir_presupuesto": 3,
    "incrementalidad": 5,
    "explorar_librerias": 0,
    "no_se": 0,
}
GOAL_METHOD = {
    "fundamentos": "bibliotecas",
    "evaluar_campanas": "mmm",
    "repartir_presupuesto": "mmm",
    "incrementalidad": "experimentos",
    "explorar_librerias": "bibliotecas",
    "no_se": "bibliotecas",
}
METHOD_MAP = {
    "mmm": {
        "family": "MMM",
        "value": "estima cómo se repartió la contribución histórica entre canales",
        "limit": "no convierte por sí solo una correlación en un efecto causal",
    },
    "experimentos": {
        "family": "experimentos de incrementalidad",
        "value": "miden el efecto causal de cambiar una inversión o exposición",
        "limit": "necesitan diseño, grupo de comparación y una ventana suficiente",
    },
    "encuestas": {
        "family": "encuestas de impacto",
        "value": "miden cambios como recuerdo, consideración o intención",
        "limit": "no sustituyen una medida de ventas incrementales",
    },
    "atribucion": {
        "family": "atribución",
        "value": "describe recorridos y asigna crédito operativo entre contactos",
        "limit": "no demuestra por sí sola que cada contacto causó la conversión",
    },
    "bibliotecas": {
        "family": "mapa del terreno",
        "value": "permite comparar qué asume y dónde falla cada herramienta",
        "limit": "leer una biblioteca no valida todavía una decisión de negocio",
    },
}
MODULE_NAMES = {
    0: "Mapa del terreno",
    1: "Datos sintéticos y verdad conocida",
    2: "Encuestas de impacto",
    3: "MMM I: mecánica y PyMC-Marketing",
    4: "MMM II: Meridian, la misma tabla",
    5: "Experimentos geo e incrementalidad",
    6: "Calibración: experimento → prior → MMM",
    7: "Causalidad general y uplift",
    8: "Robyn: la escuela no bayesiana",
    9: "Conjoint y MaxDiff",
    10: "Medición unificada e IA aplicada",
}
PREREQUISITES = {2: [0], 3: [0, 1], 4: [0, 1, 3], 5: [0, 1], 6: [0, 1, 3], 7: [0, 1], 8: [0, 1, 3], 9: [0, 1], 10: [0, 1, 2, 3, 5]}


class ProfileError(ValueError):
    pass


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_set(value: Any, name: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ProfileError(f"{name} debe ser uno de: {choices}")
    return value


def _require_list(value: Any, name: str, allowed: set[str]) -> list[str]:
    if not isinstance(value, list):
        raise ProfileError(f"{name} debe ser una lista")
    # Item types first: an unhashable item would turn the duplicate check into a TypeError.
    items = [_require_set(item, name, allowed) for item in value]
    if len(items) != len(set(items)):
        raise ProfileError(f"{name} no puede repetir opciones")
    return items


def validate_profile(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError("el perfil debe ser un objeto JSON")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ProfileError(f"schema_version debe ser {SCHEMA_VERSION}")
    availability = value.get("availability")
    if not isinstance(availability, dict):
        raise ProfileError("availability debe ser un objeto")
    minutes = availability.get("minutes_per_session")
    sessions = availability.get("sessions_per_week")
    if minutes is not None and (not isinstance(minutes, int) or not 10 <= minutes <= 240):
        raise ProfileError("availability.minutes_per_session debe estar entre 10 y 240")
    if sessions is not None and (not isinstance(sessions, int) or not 1 <= sessions <= 7):
        raise ProfileError("availability.sessions_per_week debe estar entre 1 y 7")
    if (minutes is None) != (sessions is None):
        raise ProfileError("availability debe indicar ambos valores o permitir omitirlos")
    created = value.get("created_at")
    updated = value.get("updated_at")
    if not isinstance(created, str) or not isinstance(updated, str):
        raise ProfileError("created_at y updated_at son obligatorios")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": created,
        "updated_at": updated,
        "experience": _require_set(value.get("experience"), "experience", EXPERIENCES),
        "interests": _require_list(value.get("interests"), "interests", INTERESTS),
        "goal": _require_set(value.get("goal"), "goal", GOALS),
        "availability": {"minutes_per_session": minutes, "sessions_per_week": sessions},
        "learning_preferences": _require_list(value.get("learning_preferences"), "learning_preferences", PREFERENCES),
        "pace": _require_set(value.get("pace"), "pace", PACES),
    }


def profile_file(root: Path = ROOT) -> Path:
    return root / PROFILE_PATH


def load_profile(root: Path = ROOT) -> dict[str, Any] | None:
    path = profile_file(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileError(f"perfil corrupto en {PROFILE_PATH}; no se ha sobrescrito") from exc
    return validate_profile(raw)


def save_profile(value: Any, root: Path = ROOT) -> dict[str, Any]:
    profile = validate_profile(value)
    path = profile_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a sibling and rename, so a kill mid-write cannot leave a truncated profile
    # that load_profile would then rightly refuse to overwrite.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return profile


def profile_from_answers(value: Any, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileError("las respuestas deben ser un objeto JSON")
    now = _now()
    profile = dict(value)
    profile["schema_version"] = SCHEMA_VERSION
    profile["created_at"] = existing["created_at"] if existing else now
    profile["updated_at"] = now
    return validate_profile(profile)


def _module_states(root: Path) -> dict[int, str]:
    states = {number: "pendiente" for number in MODULE_NAMES}
    formation = root / "FORMACION.md"
    if formation.exists():
        for line in formation.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\|\s*(\d+)\s*\|.*?\|\s*(pendiente|en curso|hecho|saltado)\s*\|", line)
            if match:
                states[int(match.group(1))] = match.group(2)
    progress = root / ".progreso"
    if progress.exists():
        for path in progress.glob("[0-9][0-9].md"):
            match = re.match(r"(\d{2})\.md", path.name)
            state = re.search(r"^- estado:\s*(hecho|a medias|repetir)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
            if match and state:
                states[int(match.group(1))] = {"hecho": "hecho", "a medias": "en curso", "repetir": "en curso"}[state.group(1)]
    return states


def _available_lessons(root: Path) -> set[int]:
    available = set()
    for path in (root / "lecciones").glob("[0-9][0-9]-*/LECCION.md"):
        available.add(int(path.parent.name[:2]))
    return available


def _presentation(preferences: list[str]) -> dict[str, str]:
    preference = preferences[0] if preferences else "conversacional"
    if preference == "visual":
        return {"style": "esquema textual", "note": "Abriremos cada bloque con un diagrama en texto."}
    if preference == "conversacional":
        return {"style": "pregunta socrática", "note": "Pararemos para contrastar tu hipótesis antes de cada paso."}
    if preference == "video_corto":
        return {"style": "bloques breves", "note": "MMT no produce vídeo propio; te ofreceré los cortos oficiales de libs/videos.md junto a bloques textuales de 10–15 minutos."}
    if preference == "video_largo":
        return {"style": "bloques extensos", "note": "MMT no produce vídeo propio; hay sesiones largas de terceros en libs/videos.md y agruparemos lectura y práctica en un bloque."}
    return {"style": "pregunta socrática", "note": "Empezaremos con una conversación flexible y ajustaremos el formato contigo."}


def recommend(profile: dict[str, Any] | None, root: Path = ROOT) -> dict[str, Any]:
    if profile is None:
        return {
            "status": "sin_perfil",
            "recommended_module": 0,
            "module_name": MODULE_NAMES[0],
            "reason": "Todavía no hay perfil: empieza por el mapa común antes de elegir una librería.",
            "guided_lesson_available": None,
            "next_action": "Di “quiero empezar MMT” para construir una ruta personal.",
        }
    states = _module_states(root)
    in_progress = [number for number, state in states.items() if state == "en curso"]
    desired = GOAL_TARGET[profile["goal"]]
    if profile["goal"] == "no_se":
        desired = min((TARGET_MODULE[interest] for interest in profile["interests"]), default=0)
    candidate = in_progress[0] if in_progress else desired
    missing = [number for number in PREREQUISITES.get(candidate, []) if states[number] not in {"hecho", "saltado"}]
    if missing:
        candidate = min(missing)
    available = _available_lessons(root)
    lesson = candidate if candidate in available else None
    # The route follows the goal, so the family the tutor narrates must follow it too. Only a
    # neutral goal (one that maps to "bibliotecas") lets the declared interest lead. When both
    # disagree, the reason says so instead of claiming they agree.
    goal_method = GOAL_METHOD[profile["goal"]]
    interest = profile["interests"][0] if profile["interests"] else None
    primary = interest if (goal_method == "bibliotecas" and interest) else goal_method
    method = METHOD_MAP[primary]
    interest_family = METHOD_MAP[interest]["family"] if interest else None
    if interest_family and interest_family != method["family"]:
        reason = (
            f"Tu objetivo marca la ruta, y esa ruta es {method['family']}; tu interés apunta a "
            f"{interest_family}, que llega más adelante en el itinerario. La ruta respeta los "
            "prerrequisitos actuales."
        )
    else:
        reason = (
            f"Tu objetivo marca la ruta y tu interés apunta a {method['family']}; la ruta "
            "respeta los prerrequisitos actuales."
        )
    minutes = profile["availability"]["minutes_per_session"] or 30
    sessions = profile["availability"]["sessions_per_week"] or 1
    weeks = 1 if profile["pace"] == "intensivo" or sessions >= 3 else 2
    presentation = _presentation(profile["learning_preferences"])
    action = f"Reserva {min(minutes, 30)} minutos para {MODULE_NAMES[candidate]} y formula una predicción antes de practicar."
    if lesson is None:
        action += " Aún no existe una lección guiada para este módulo; la lección disponible es 03 cuando completes sus prerrequisitos."
    return {
        "status": "perfil_activo",
        "method": method,
        "recommended_module": candidate,
        "module_name": MODULE_NAMES[candidate],
        "reason": reason,
        "availability": profile["availability"],
        "plan": {"weeks": weeks, "sessions_per_week": sessions, "minutes_per_session": minutes},
        "presentation": presentation,
        "guided_lesson_available": lesson,
        "next_action": action,
    }


def _print_recommendation(value: dict[str, Any]) -> None:
    if value["status"] == "sin_perfil":
        print(value["reason"])
        print(value["next_action"])
        return
    method = value["method"]
    print(f"Familia provisional: {method['family']}. {method['value'].capitalize()}; {method['limit']}.")
    print(f"Ruta: módulo {value['recommended_module']} — {value['module_name']}.")
    print(f"Formato: {value['presentation']['style']}. {value['presentation']['note']}")
    print(value["next_action"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage a local MMT learner profile.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="show the saved profile status")
    group.add_argument("--recommend", action="store_true", help="recommend the next MMT step")
    group.add_argument("--save-json", metavar="JSON", help="save confirmed structured answers")
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)
    try:
        existing = load_profile()
        if args.save_json is not None:
            try:
                answers = json.loads(args.save_json)
            except json.JSONDecodeError as exc:
                raise ProfileError("--save-json debe contener JSON válido") from exc
            profile = profile_from_answers(answers, existing)
            save_profile(profile)
            result: Any = {"status": "guardado", "profile": profile, "recommendation": recommend(profile)}
        elif args.status:
            result = {"status": "sin_perfil"} if existing is None else {"status": "perfil_activo", "profile": existing}
        else:
            result = recommend(existing)
    except ProfileError as exc:
        print(f"Perfil: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.recommend:
        _print_recommendation(result)
    elif result["status"] == "sin_perfil":
        print("No hay perfil local. Di “quiero empezar MMT” para crearlo con el tutor.")
    else:
        print("Perfil local activo. Usa --recommend para ver la siguiente ruta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
