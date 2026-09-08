from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent

core = types.ModuleType("engine_554_core")
core.VERSION = "1.1.0-beta5.5.4-clean-installer"

class Pipeline:
    pass

core.Pipeline = Pipeline
core.main_called = 0

def core_main():
    core.main_called += 1
    return 7

core.main = core_main
sys.modules["engine_554_core"] = core

# Load the real Visual writer first, exactly as the installed wrapper would.
spec_visual = importlib.util.spec_from_file_location("visual_srt_555", HERE / "visual_srt_555.py")
visual = importlib.util.module_from_spec(spec_visual)
spec_visual.loader.exec_module(visual)
sys.modules["visual_srt_555"] = visual

spec = importlib.util.spec_from_file_location("engine_555_wrapper", HERE / "engine.py")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)

assert core.VERSION == "1.1.0-beta5.5.5-visual-grounded"
assert core.Pipeline.creative_plan is wrapper._visual_grounded_plan
assert core.Pipeline.write_srt_script is wrapper._visual_grounded_writer

p = core.Pipeline()
plan = p.creative_plan({"setup": "start evidence", "ending": "end evidence"}, 90.0)
assert plan["version"] == "5.5.5-visual-grounded"
assert plan["topic_lane"] == "visual_grounded"
assert plan["beats"] == []
assert "start evidence" in plan["premise"]
assert "end evidence" in plan["verified_payoff"]

assert wrapper.main() == 7
assert core.main_called == 1
print("PASS engine wrapper integration")
