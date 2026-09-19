from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lecciones" / "build_notebooks.py"
SPEC = importlib.util.spec_from_file_location("build_notebooks", SCRIPT)
assert SPEC and SPEC.loader
build_notebooks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_notebooks)


class NotebookBuilderTests(unittest.TestCase):
    def test_generation_is_deterministic_and_hides_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lesson = Path(tmp) / "03-fixture"
            lesson.mkdir()
            markdown = lesson / "LECCION.md"
            markdown.write_text(
                "# 03 · Fixture\n\n"
                f"{build_notebooks.badge_for(markdown)}\n\n"
                "## 1 · Explicar\ntexto\n\n```python\nprint('hola')\n```\n\n"
                "## 2 · Practicar\npráctica\n\n"
                "## 3 · Comprobar\nPregunta\n"
                "<details><summary>Referencia</summary>respuesta-secreta</details>\n\n"
                "## 4 · Registrar\nregistro\n",
                encoding="utf-8",
            )
            (lesson / "fixture.truth.json").write_text('{"secret": "verdad-centinela"}', encoding="utf-8")
            first = build_notebooks.serialized_notebook(lesson)
            self.assertEqual(first, build_notebooks.serialized_notebook(lesson))
            rendered = first.decode()
            self.assertIn("print('hola')", rendered)
            self.assertNotIn("respuesta-secreta", rendered)
            self.assertNotIn("verdad-centinela", rendered)
            self.assertIn(build_notebooks.NOTICE, rendered)

    def test_missing_heading_is_a_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lesson = Path(tmp) / "03-fixture"
            lesson.mkdir()
            markdown = lesson / "LECCION.md"
            markdown.write_text(
                f"# 03 · Fixture\n\n{build_notebooks.badge_for(markdown)}\n\n"
                "## 1 · Explicar\ntexto\n## 2 · Practicar\ntexto\n## 4 · Registrar\ntexto\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "falta el encabezado"):
                build_notebooks.serialized_notebook(lesson)

    def test_check_detects_a_drifted_notebook(self) -> None:
        target = ROOT / "lecciones" / "03-mmm-pymc-marketing" / "LECCION.ipynb"
        self.assertEqual(build_notebooks.main(["--lesson", "03"]), 0)
        original = target.read_bytes() if target.exists() else None
        try:
            target.write_text("drift", encoding="utf-8")
            self.assertEqual(build_notebooks.main(["--check", "--lesson", "03"]), 1)
        finally:
            if original is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(original)


class NotebookLesson03Tests(unittest.TestCase):
    def test_lesson_03_hides_truth_and_checking_details(self) -> None:
        self.assertEqual(build_notebooks.main(["--lesson", "03"]), 0)
        notebook = json.loads(
            (ROOT / "lecciones" / "03-mmm-pymc-marketing" / "LECCION.ipynb").read_text(encoding="utf-8")
        )
        sources = "\n".join(cell["source"] for cell in notebook["cells"])
        self.assertIn("lecciones/practica.py", sources)
        self.assertIn('"add", "-f", ".progreso"', sources)
        self.assertIn(".progreso", sources)
        self.assertIn("pymc-marketing==1.1.0", sources)
        self.assertIn("userdata.get(\"GITHUB_TOKEN\")", sources)
        self.assertNotIn("<details>", sources)
        self.assertNotIn("Referencia", sources)

    def test_lesson_version_is_consistent_with_setup_and_source(self) -> None:
        source = (ROOT / "lecciones" / "03-mmm-pymc-marketing" / "LECCION.md").read_text(encoding="utf-8")
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        notebook = (ROOT / "lecciones" / "03-mmm-pymc-marketing" / "LECCION.ipynb").read_text(encoding="utf-8")
        for text in (source, setup, notebook):
            self.assertIn("pymc-marketing", text)
            self.assertIn("1.1.0", text)

    def test_notebook_is_stable_after_regeneration(self) -> None:
        target = ROOT / "lecciones" / "03-mmm-pymc-marketing" / "LECCION.ipynb"
        build_notebooks.main(["--lesson", "03"])
        first = hashlib.sha256(target.read_bytes()).hexdigest()
        build_notebooks.main(["--lesson", "03"])
        self.assertEqual(first, hashlib.sha256(target.read_bytes()).hexdigest())

    def test_sync_without_a_fork_keeps_progress_local(self) -> None:
        notebook = build_notebooks.build_notebook(ROOT / "lecciones" / "03-mmm-pymc-marketing")
        sync_source = next(
            cell["source"] for cell in notebook["cells"] if "progress = Path" in cell["source"]
        )
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                Path(".progreso").mkdir()
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exec(sync_source, {"FORK_URL": ""})
                self.assertTrue(Path(".progreso").is_dir())
                self.assertIn("guardado localmente", output.getvalue())
            finally:
                os.chdir(previous)


class NotebookLesson04Tests(unittest.TestCase):
    LESSON = ROOT / "lecciones" / "04-mmm-meridian"

    def test_lesson_04_hides_truth_and_checking_details(self) -> None:
        self.assertEqual(build_notebooks.main(["--lesson", "04"]), 0)
        notebook = json.loads((self.LESSON / "LECCION.ipynb").read_text(encoding="utf-8"))
        sources = "\n".join(cell["source"] for cell in notebook["cells"])
        self.assertIn("lecciones/practica.py 04", sources)
        self.assertIn('"add", "-f", ".progreso"', sources)
        self.assertIn("google-meridian==2.0.0", sources)
        self.assertNotIn("pymc-marketing", sources)
        self.assertNotIn("<details>", sources)
        self.assertNotIn("Referencia", sources)

    def test_lesson_version_is_consistent_with_setup_and_source(self) -> None:
        source = (self.LESSON / "LECCION.md").read_text(encoding="utf-8")
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")
        notebook = (self.LESSON / "LECCION.ipynb").read_text(encoding="utf-8")
        for text in (source, setup, notebook):
            self.assertIn("google-meridian", text)
            self.assertIn("2.0.0", text)

    def test_every_code_cell_is_runnable(self) -> None:
        """Shell cells are bang lines; Python cells compile. The 03 pilot shipped 7 broken."""
        notebook = build_notebooks.build_notebook(self.LESSON)
        code = [cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertGreater(len(code), 5)
        for source in code:
            with self.subTest(source=source[:60]):
                if source.startswith("!"):
                    self.assertTrue(all(line.startswith("!") for line in source.splitlines()))
                    self.assertNotIn(".venvs/", source)
                else:
                    compile(source, "<cell>", "exec")

    def test_lesson_without_runtime_packages_gets_no_runtime_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lesson = Path(tmp) / "99-fixture"
            lesson.mkdir()
            markdown = lesson / "LECCION.md"
            markdown.write_text(
                f"# 99 · Fixture\n\n{build_notebooks.badge_for(markdown)}\n\n"
                "## 1 · Explicar\ntexto\n## 2 · Practicar\ntexto\n"
                "## 3 · Comprobar\ntexto\n## 4 · Registrar\ntexto\n",
                encoding="utf-8",
            )
            sources = "\n".join(c["source"] for c in build_notebooks.build_notebook(lesson)["cells"])
            self.assertNotIn("pip", sources)
            self.assertNotIn("git clone", sources)


class NotebookBuildValidationTests(unittest.TestCase):
    """E-01: un LECCION.md roto falla con un mensaje que dice dónde, y no escribe nada."""

    def _lesson(self, tmp: str, body: str) -> Path:
        lesson = Path(tmp) / "03-fixture"
        lesson.mkdir()
        markdown = lesson / "LECCION.md"
        markdown.write_text(body.format(badge=build_notebooks.badge_for(markdown)), encoding="utf-8")
        return lesson

    def test_empty_markdown_is_a_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lesson = self._lesson(tmp, "")
            with self.assertRaises(SystemExit) as caught:
                build_notebooks.build_notebook(lesson)
            self.assertIn(str(lesson / "LECCION.md"), str(caught.exception))
            self.assertFalse((lesson / "LECCION.ipynb").exists())

    def test_missing_section_names_the_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lesson = self._lesson(
                tmp,
                "# 03 · Fixture\n\n{badge}\n\n## 1 · Explicar\nTexto\n\n## 2 · Practicar\nTexto\n",
            )
            with self.assertRaises(SystemExit) as caught:
                build_notebooks.build_notebook(lesson)
            self.assertIn("## 3 · Comprobar", str(caught.exception))
            self.assertFalse((lesson / "LECCION.ipynb").exists())

    def test_unclosed_details_stops_instead_of_leaking_the_answer(self) -> None:
        """El Never de §3: la respuesta no puede llegar al notebook por una etiqueta mal cerrada."""
        with tempfile.TemporaryDirectory() as tmp:
            lesson = self._lesson(
                tmp,
                "# 03 · Fixture\n\n{badge}\n\n## 1 · Explicar\nTexto\n\n## 2 · Practicar\nTexto\n\n"
                "## 3 · Comprobar\n<details>\nRESPUESTA-SECRETA\n\n## 4 · Registrar\nTexto\n",
            )
            with self.assertRaises(SystemExit) as caught:
                build_notebooks.build_notebook(lesson)
            self.assertIn("sin cerrar", str(caught.exception))
            self.assertNotIn("RESPUESTA-SECRETA", str(caught.exception))


class TokenSafetyTests(unittest.TestCase):
    """E-03: el token solo existe en memoria durante el push, y no aparece en ningún sitio."""

    SENTINEL = "ghp_CENTINELA_QUE_NO_DEBE_APARECER_0123456789"

    def _sync_source(self) -> str:
        notebook = build_notebooks.build_notebook(ROOT / "lecciones" / "03-mmm-pymc-marketing")
        return next(
            cell["source"] for cell in notebook["cells"] if "progress = Path" in cell["source"]
        )

    def test_no_token_material_is_committed_anywhere(self) -> None:
        for path in sorted(ROOT.glob("lecciones/**/*.ipynb")) + [SCRIPT]:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("ghp_", text)
                self.assertNotIn("github_pat_", text)
                self.assertNotIn("GITHUB_TOKEN=", text)

    def test_sentinel_token_never_reaches_disk_or_output(self) -> None:
        source = self._sync_source()
        calls: list[list[str]] = []

        class Result:
            returncode = 1
            stdout = f"remote: rejected {self.SENTINEL}"
            stderr = f"fatal: auth failed with {self.SENTINEL}"

        def fake_run(args, **kwargs):
            calls.append(list(args))
            # The token must travel in the environment, never in the argv of git.
            self.assertNotIn(self.SENTINEL, " ".join(str(a) for a in args))
            return Result()

        class FakeUserdata:
            @staticmethod
            def get(_name: str) -> str:
                return TokenSafetyTests.SENTINEL

        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                Path(".progreso").mkdir()
                output = io.StringIO()
                namespace = {
                    "FORK_URL": "https://github.com/alumno/mmt.git",
                    "__fake_userdata": FakeUserdata,
                }
                patched = source.replace(
                    "from google.colab import userdata",
                    "userdata = __fake_userdata",
                ).replace("subprocess.run(", "__fake_run(")
                namespace["__fake_run"] = fake_run
                with contextlib.redirect_stdout(output):
                    exec(patched, namespace)
                printed = output.getvalue()
                self.assertNotIn(self.SENTINEL, printed)
                self.assertIn("No se pudo sincronizar", printed)
                for created in Path(tmp).rglob("*"):
                    if created.is_file():
                        self.assertNotIn(
                            self.SENTINEL, created.read_text(encoding="utf-8", errors="ignore")
                        )
            finally:
                os.chdir(previous)
        self.assertTrue(any(call[:2] == ["git", "push"] for call in calls), calls)
