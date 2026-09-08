"""Exercise the actual final gate without model downloads or GPU inference."""
import ast
import copy
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "app/engine.py").read_text()
spec = importlib.util.spec_from_file_location("engine554", ROOT / "app/engine.py")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
tree = ast.parse(SOURCE)
method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "write_srt_script")
gate = next(n for n in method.body if isinstance(n, ast.If) and isinstance(n.test, ast.Name) and n.test.id == "unresolved_after_final_gate")
gate_code = compile(ast.Module(body=[gate], type_ignores=[]), "actual_final_gate", "exec")


class FinalGateTests(unittest.TestCase):
    def exercise(self, unresolved):
        rows = [
            {"start": 0., "end": 4.08, "text": "A person constructs a circular stone barrier in the river."},
            {"start": 4.18, "end": 8.26, "text": "A person constructs a circular stone barrier in the river."},
        ]
        original = copy.deepcopy(rows)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            events = []
            env = dict(engine.__dict__, self=types.SimpleNamespace(out=out),
                       unresolved_after_final_gate=unresolved,
                       factual_similarity_warnings=[], result=rows,
                       emit=lambda *args: events.append(args))
            exec(gate_code, env)
            report = engine.direct_srt(rows, 8.26, out / "EN.srt", "en")
            self.assertEqual(rows, original)
            self.assertEqual(report["cues"], 2)
            self.assertTrue((out / "EN.srt").is_file())
            self.assertEqual((out / "Repeat_QA_REVIEW.json").exists(), bool(unresolved))
            self.assertEqual(bool(events), bool(unresolved))

    def test_one_failed_caption_still_exports(self):
        self.exercise([{"caption": 2, "issue": "exact duplicate"}])

    def test_multiple_failed_captions_still_export(self):
        self.exercise([{"caption": 1}, {"caption": 2}])

    def test_clean_gate_has_no_review_warning(self):
        self.exercise([])

    def test_invalid_timeline_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                engine.direct_srt([{"start": 1., "end": 4.08,
                    "text": "A person constructs a circular stone barrier in the river."}],
                    4.08, Path(tmp) / "bad.srt", "en")
            self.assertFalse((Path(tmp) / "bad.srt").exists())

    def test_required_features_remain(self):
        self.assertEqual(engine.VISION_MODEL, "qwen3-vl:4b-instruct-q4_K_M")
        for feature in ["StoryFlow", "GoldStyle", "write_vietnamese_translation", '"num_gpu": -1']:
            self.assertIn(feature, SOURCE)
        self.assertIn('requires_repeat_review', SOURCE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
