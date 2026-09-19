#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LECCIONES = ROOT / "lecciones"
SECTIONS = (
    "## 1 · Explicar",
    "## 2 · Practicar",
    "## 3 · Comprobar",
    "## 4 · Registrar",
)
NOTICE = "Comprobar con el tutor; la referencia no está en este notebook"
FENCE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)
DETAILS = re.compile(r"<details>.*?</details>", re.DOTALL | re.IGNORECASE)
DETAILS_TAG = re.compile(r"</?details\b", re.IGNORECASE)
# The lessons are written for a local shell with per-family venvs; Colab has one environment
# and installs into it, so the venv path has to go or the cell cannot run.
VENV_PYTHON = re.compile(r"\.venvs/[A-Za-z0-9_-]+/bin/python")
CONTINUATION = re.compile(r"\\\n\s*")
SHELL_LANGS = {"bash", "sh", "shell", "console"}
PYTHON_LANGS = {"python", "py"}
# A bare fence is a shell command only if every line starts like one. Anything else — a
# formula, pseudocode — stays Markdown: a command left as prose is visible, a formula turned
# into a code cell is a SyntaxError on "Run all".
SHELL_START = re.compile(r"^(\.venvs/[^\s]+/bin/python|python3?|uv|uvx|pip|git|bash|sh|cd|ls|cat)\b")
PRACTICA = re.compile(r"`(python3?\s+lecciones/practica\.py[^`]*)`")
# What each lesson's Colab runtime installs. A lesson absent here gets no runtime or sync
# cells: its notebook is read-only until someone lists the packages it needs, pinned to
# the version its LECCION.md quotes.
RUNTIME_PACKAGES = {
    "03": ["pymc-marketing==1.1.0", "nutpie", "h5netcdf", "h5py"],
    "04": ["google-meridian==2.0.0", "h5netcdf", "h5py"],
}


def badge_for(markdown: Path) -> str:
    try:
        rel = markdown.relative_to(ROOT).as_posix().replace("LECCION.md", "LECCION.ipynb")
    except ValueError:
        rel = f"lecciones/{markdown.parent.name}/LECCION.ipynb"
    return (
        "[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
        f"(https://colab.research.google.com/github/sixsevenappslab/mmt/blob/main/{rel})"
    )


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.strip()}


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.strip(),
    }


def looks_like_shell(body: str) -> bool:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return bool(lines) and all(SHELL_START.match(line) for line in lines)


def shell_cell(body: str) -> dict:
    """A shell block as Colab runs it: one bang line, venv paths stripped, continuations joined."""
    joined = CONTINUATION.sub(" ", VENV_PYTHON.sub("python", body).strip())
    return code_cell("\n".join(f"!{line}" for line in joined.splitlines() if line.strip()))


def fence_cell(language: str, body: str) -> dict:
    """Decide what a fenced block becomes, by its info string and then by its content."""
    language = language.strip().lower()
    body = textwrap.dedent(body).strip("\n")
    if language in PYTHON_LANGS:
        return code_cell(body)
    if language in SHELL_LANGS or (not language and looks_like_shell(body)):
        return shell_cell(body)
    # Formulas and pseudocode keep their fence and stay prose.
    return markdown_cell(f"```{language}\n{body}\n```")


def practica_cells(prose: str) -> list[dict]:
    """Turn every inline `practica.py ...` into a cell the learner can actually run."""
    return [
        code_cell(f"!{VENV_PYTHON.sub('python', command).strip()}")
        for command in PRACTICA.findall(prose)
    ]


def cells_from_markdown(source: str) -> list[dict]:
    cells: list[dict] = []
    cursor = 0
    for match in FENCE.finditer(source):
        prose = source[cursor:match.start()].strip()
        if prose:
            cells.append(markdown_cell(prose))
            cells.extend(practica_cells(prose))
        cells.append(fence_cell(match.group(1), match.group(2)))
        cursor = match.end()
    prose = source[cursor:].strip()
    if prose:
        cells.append(markdown_cell(prose))
        cells.extend(practica_cells(prose))
    return cells


def split_sections(source: str, path: Path) -> tuple[str, list[tuple[str, str]]]:
    positions = []
    for heading in SECTIONS:
        match = re.search(rf"^{re.escape(heading)}\s*$", source, re.MULTILINE)
        if not match:
            raise SystemExit(f"{path}: falta el encabezado obligatorio {heading!r}")
        positions.append((heading, match.start(), match.end()))
    if [start for _, start, _ in positions] != sorted(start for _, start, _ in positions):
        raise SystemExit(f"{path}: los encabezados de lección no están en orden")
    intro = source[:positions[0][1]].strip()
    sections = []
    for index, (heading, _, end) in enumerate(positions):
        next_start = positions[index + 1][1] if index + 1 < len(positions) else len(source)
        sections.append((heading, source[end:next_start].strip()))
    return intro, sections


def lesson_packages(lesson: Path) -> list[str]:
    return RUNTIME_PACKAGES.get(lesson.name[:2], [])


def runtime_cells(lesson: Path) -> list[dict]:
    packages = lesson_packages(lesson)
    if not packages:
        return []
    quoted = ", ".join(f'"{package}"' for package in packages)
    return [
        markdown_cell(
            "## Runtime Colab\n\n"
            "Deja `FORK_URL` vacío para practicar en esta sesión de Colab sin sincronizar. "
            "Un fork propio permite guardar únicamente `.progreso/`."
        ),
        code_cell(
            "import os\n"
            "import subprocess\n"
            "from pathlib import Path\n\n"
            'FORK_URL = ""\n'
            'CANONICAL_URL = "https://github.com/sixsevenappslab/mmt.git"\n'
            'CLONE_DIR = Path("mmt")\n\n'
            "source_url = FORK_URL.strip() or CANONICAL_URL\n"
            "# Re-running this cell must not nest a clone inside the clone.\n"
            "if Path.cwd().name == CLONE_DIR.name:\n"
            "    print(f\"Ya estás dentro de {CLONE_DIR.name}; no vuelvo a clonar.\")\n"
            "elif CLONE_DIR.exists():\n"
            "    os.chdir(CLONE_DIR)\n"
            "    print(f\"{CLONE_DIR.name} ya estaba clonado; entro sin volver a descargarlo.\")\n"
            "else:\n"
            "    subprocess.run([\"git\", \"clone\", source_url, str(CLONE_DIR)], check=True)\n"
            "    os.chdir(CLONE_DIR)"
        ),
        code_cell(
            "import sys\n\n"
            "subprocess.run([\n"
            "    sys.executable, \"-m\", \"pip\", \"install\", \"-q\",\n"
            f"    {quoted},\n"
            "], check=True)"
        ),
    ]


def sync_cells(lesson: Path) -> list[dict]:
    if not lesson_packages(lesson):
        return []
    return [
        markdown_cell(
            "## Registrar en el fork\n\n"
            "Esta celda conserva el progreso local aunque no haya fork, Secret o push disponible."
        ),
        code_cell(
            "import base64\n"
            "import os\n"
            "import subprocess\n"
            "from pathlib import Path\n\n"
            "# This cell may be run before the runtime cell; say so instead of raising NameError.\n"
            "FORK_URL = globals().get(\"FORK_URL\", \"\")\n"
            "progress = Path(\".progreso\")\n"
            "if not progress.exists():\n"
            "    print(\"Aún no hay .progreso/ para sincronizar; sigue practicando localmente.\")\n"
            "elif not FORK_URL.strip():\n"
            "    print(\"Progreso guardado localmente: configura un fork para sincronizarlo con tu tutor.\")\n"
            "else:\n"
            "    subprocess.run([\"git\", \"add\", \"-f\", \".progreso\"], check=True)\n"
            "    changed = subprocess.run(\n"
            "        [\"git\", \"diff\", \"--cached\", \"--quiet\"], check=False\n"
            "    ).returncode != 0\n"
            "    if changed:\n"
            "        subprocess.run([\"git\", \"config\", \"user.name\", \"MMT learner\"], check=True)\n"
            "        subprocess.run([\"git\", \"config\", \"user.email\", \"learner@users.noreply.github.com\"], check=True)\n"
            "        subprocess.run([\"git\", \"commit\", \"-m\", \"Save lesson progress\"], check=True)\n"
            "    try:\n"
            "        from google.colab import userdata\n"
            "        token = userdata.get(\"GITHUB_TOKEN\")\n"
            "    except (ImportError, KeyError):\n"
            "        token = None\n"
            "    if not token:\n"
            "        print(\"Progreso guardado localmente; falta el Secret para sincronizarlo con tu tutor.\")\n"
            "    else:\n"
            "        basic = base64.b64encode(f\"x-access-token:{token}\".encode()).decode()\n"
            "        push_env = os.environ.copy()\n"
            "        push_env[\"GIT_CONFIG_COUNT\"] = \"1\"\n"
            "        push_env[\"GIT_CONFIG_KEY_0\"] = \"http.extraheader\"\n"
            "        push_env[\"GIT_CONFIG_VALUE_0\"] = f\"Authorization: Basic {basic}\"\n"
            "        result = subprocess.run(\n"
            "            [\"git\", \"push\"], env=push_env, capture_output=True, text=True, check=False\n"
            "        )\n"
            "        if result.returncode:\n"
            "            print(\"No se pudo sincronizar; tu progreso local se conserva. Revisa el fork y el Secret.\")\n"
            "        else:\n"
            "            print(\"Progreso sincronizado con tu fork.\")"
        ),
    ]


def build_notebook(lesson: Path) -> dict:
    markdown = lesson / "LECCION.md"
    source = markdown.read_text(encoding="utf-8")
    badge = badge_for(markdown)
    if badge not in source:
        raise SystemExit(f"{markdown}: falta el badge Open in Colab generado")
    intro, sections = split_sections(source, markdown)
    cells = runtime_cells(lesson)
    cells.extend(cells_from_markdown(intro))
    for heading, content in sections:
        cells.append(markdown_cell(heading))
        if heading == "## 3 · Comprobar":
            content = DETAILS.sub("", content).strip()
            if DETAILS_TAG.search(content):
                raise SystemExit(
                    f"{markdown}: hay un <details> sin cerrar en Comprobar. Sin los dos tags la "
                    "respuesta se copiaria al notebook; cierralo antes de generar."
                )
        cells.extend(cells_from_markdown(content))
        if heading == "## 3 · Comprobar":
            cells.append(markdown_cell(NOTICE))
    cells.extend(sync_cells(lesson))
    return {"cells": cells, "metadata": {}, "nbformat": 4, "nbformat_minor": 5}


def serialized_notebook(lesson: Path) -> bytes:
    return (json.dumps(build_notebook(lesson), ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode()


def discover_lessons(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("[0-9][0-9]-*") if (path / "LECCION.md").is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic notebooks from lesson Markdown.")
    parser.add_argument("--check", action="store_true", help="fail if a generated notebook differs")
    parser.add_argument("--lesson", help="two-digit lesson number")
    parser.add_argument("--list", action="store_true", help="print the lessons found, one per line")
    args = parser.parse_args(argv)
    lessons = discover_lessons(LECCIONES)
    if args.lesson:
        lesson_number = args.lesson.zfill(2)
        lessons = [lesson for lesson in lessons if lesson.name.startswith(f"{lesson_number}-")]
        if not lessons:
            raise SystemExit(f"no encuentro la lección {lesson_number}")
    if args.list:
        for lesson in lessons:
            print(lesson.name)
        return 0
    failures = []
    for lesson in lessons:
        target = lesson / "LECCION.ipynb"
        expected = serialized_notebook(lesson)
        if args.check:
            if not target.is_file() or target.read_bytes() != expected:
                failures.append(str(target.relative_to(ROOT)))
        else:
            target.write_bytes(expected)
    if failures:
        print("notebooks desincronizados: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
