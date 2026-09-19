from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("perfil", ROOT / "lecciones" / "perfil.py")
assert SPEC and SPEC.loader
perfil = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(perfil)


def answers(**changes: object) -> dict:
    value = {
        "experience": "principiante",
        "interests": ["mmm"],
        "goal": "fundamentos",
        "availability": {"minutes_per_session": 20, "sessions_per_week": 2},
        "learning_preferences": ["visual"],
        "pace": "suave",
    }
    value.update(changes)
    return value


def make_root(base: Path, formation: str = "| 0 | Mapa | pendiente | | |\n") -> Path:
    (base / "lecciones" / "03-mmm-pymc-marketing").mkdir(parents=True)
    (base / "lecciones" / "03-mmm-pymc-marketing" / "LECCION.md").write_text("# 03\n")
    (base / "FORMACION.md").write_text(formation)
    return base


class ProfileTests(unittest.TestCase):
    def test_profile_is_versioned_and_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            profile = perfil.profile_from_answers(answers())
            perfil.save_profile(profile, root)
            saved = root / ".mmt" / "perfil.json"
            self.assertTrue(saved.exists())
            self.assertFalse((root / ".progreso" / "perfil.json").exists())
            self.assertEqual(perfil.load_profile(root)["interests"], ["mmm"])
            self.assertEqual(json.loads(saved.read_text())["schema_version"], 1)

    def test_invalid_answers_do_not_write_a_partial_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            with self.assertRaisesRegex(perfil.ProfileError, "minutes_per_session"):
                perfil.profile_from_answers(answers(availability={"minutes_per_session": 0, "sessions_per_week": 2}))
            self.assertFalse((root / ".mmt" / "perfil.json").exists())

    def test_corrupt_profile_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            path = root / ".mmt" / "perfil.json"
            path.parent.mkdir()
            path.write_text("not json")
            with self.assertRaisesRegex(perfil.ProfileError, "no se ha sobrescrito"):
                perfil.load_profile(root)
            self.assertEqual(path.read_text(), "not json")

    def test_unknown_schema_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            path = root / ".mmt" / "perfil.json"
            path.parent.mkdir()
            path.write_text(json.dumps({"schema_version": 99}))
            with self.assertRaisesRegex(perfil.ProfileError, "schema_version"):
                perfil.load_profile(root)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 99)

    def test_recommendation_respects_prerequisites_and_existing_lessons(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            profile = perfil.profile_from_answers(answers(interests=["mmm"]))
            recommendation = perfil.recommend(profile, root)
            self.assertEqual(recommendation["recommended_module"], 0)
            self.assertIsNone(recommendation["guided_lesson_available"])
            self.assertIn("Aún no existe", recommendation["next_action"])

    def test_in_progress_module_wins_over_interest(self) -> None:
        formation = "| 0 | Mapa | hecho | | |\n| 1 | Datos | hecho | | |\n| 2 | Encuestas | en curso | | |\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), formation)
            profile = perfil.profile_from_answers(answers(interests=["mmm"], learning_preferences=["conversacional"]))
            recommendation = perfil.recommend(profile, root)
            self.assertEqual(recommendation["recommended_module"], 2)
            self.assertEqual(recommendation["presentation"]["style"], "pregunta socrática")

    def test_video_preference_never_invents_a_resource(self) -> None:
        """Both video preferences must point at the catalogue, never at a resource we lack."""
        for preference in ("video_corto", "video_largo"):
            with self.subTest(preference=preference), tempfile.TemporaryDirectory() as tmp:
                root = make_root(Path(tmp))
                profile = perfil.profile_from_answers(
                    answers(learning_preferences=[preference])
                )
                recommendation = perfil.recommend(profile, root)
                note = recommendation["presentation"]["note"]
                self.assertIn("libs/videos.md", note)
                self.assertIn("no produce vídeo propio", note)

    def test_omitted_categories_persist_and_degrade_to_a_safe_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            profile = perfil.profile_from_answers(
                answers(
                    experience="no_se",
                    interests=[],
                    goal="no_se",
                    availability={"minutes_per_session": None, "sessions_per_week": None},
                    learning_preferences=[],
                    pace="no_se",
                )
            )
            perfil.save_profile(profile, root)
            recommendation = perfil.recommend(perfil.load_profile(root), root)
            self.assertEqual(recommendation["recommended_module"], 0)
            self.assertEqual(recommendation["presentation"]["style"], "pregunta socrática")

    def test_persona_routes_keep_method_value_and_style_separate(self) -> None:
        cases = [
            ("experimentos", "conversacional", "experimentos de incrementalidad", "pregunta socrática"),
            ("encuestas", "video_corto", "encuestas de impacto", "bloques breves"),
            ("atribucion", "video_largo", "atribución", "bloques extensos"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            for interest, preference, family, style in cases:
                profile = perfil.profile_from_answers(
                    answers(interests=[interest], learning_preferences=[preference])
                )
                recommendation = perfil.recommend(profile, root)
                self.assertEqual(recommendation["method"]["family"], family)
                self.assertEqual(recommendation["presentation"]["style"], style)
                self.assertEqual(recommendation["recommended_module"], 0)

    def test_preference_order_and_goal_change_the_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp))
            video_first = perfil.profile_from_answers(
                answers(learning_preferences=["video_corto", "visual"], goal="incrementalidad")
            )
            visual_first = perfil.profile_from_answers(
                answers(learning_preferences=["visual", "video_corto"], goal="incrementalidad")
            )
            short_plan = perfil.profile_from_answers(
                answers(availability={"minutes_per_session": 10, "sessions_per_week": 1}, pace="suave")
            )
            self.assertEqual(perfil.recommend(video_first, root)["presentation"]["style"], "bloques breves")
            self.assertEqual(perfil.recommend(visual_first, root)["presentation"]["style"], "esquema textual")
            self.assertEqual(perfil.recommend(short_plan, root)["plan"]["weeks"], 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(Path(tmp), "| 0 | Mapa | hecho | | |\n| 1 | Datos | hecho | | |\n")
            goal_route = perfil.profile_from_answers(answers(interests=["atribucion"], goal="incrementalidad"))
            self.assertEqual(perfil.recommend(goal_route, root)["recommended_module"], 5)

    def test_no_profile_has_a_backwards_compatible_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recommendation = perfil.recommend(None, Path(tmp))
            self.assertEqual(recommendation["status"], "sin_perfil")
            self.assertEqual(recommendation["recommended_module"], 0)


class ReviewRegressionTests(unittest.TestCase):
    """Los dos bugs rojos del gate y el contrato sin traceback a nivel de CLI."""

    def test_unhashable_list_item_is_a_profile_error_not_a_typeerror(self) -> None:
        profile = perfil.profile_from_answers(answers())
        with self.assertRaises(perfil.ProfileError):
            perfil.validate_profile({**profile, "interests": [{"a": 1}]})

    def test_goal_and_interest_from_different_families_do_not_contradict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_root(
                Path(tmp), formation="| 0 | Mapa | hecho | | |\n| 1 | Datos | hecho | | |\n"
            )
            profile = perfil.profile_from_answers(
                answers(goal="evaluar_campanas", interests=["encuestas"])
            )
            result = perfil.recommend(profile, root)
        self.assertEqual(result["recommended_module"], 3)
        self.assertEqual(result["method"]["family"], "MMM")
        self.assertIn("encuestas de impacto", result["reason"])
        self.assertIn("más adelante", result["reason"])

    def test_cli_rejects_bad_json_without_a_traceback(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "lecciones" / "perfil.py"), "--save-json", "{no es json"],
            text=True, capture_output=True, check=False, cwd=ROOT,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)
