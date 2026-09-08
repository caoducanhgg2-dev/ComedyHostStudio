from __future__ import annotations
import importlib.util, pathlib, json
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("engine553e", ROOT/"engine.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

checks=[]
def ok(name, cond, detail=""):
    checks.append((name,bool(cond),detail))
    if not cond:
        raise AssertionError(name+": "+detail)

ok("version", m.VERSION=="1.1.0-beta5.5.4-clean-installer", m.VERSION)

# Real 5.5.3d failure examples: factual similarity must not be fatal.
a="A person in dark clothing wades through shallow water."
b="A person in dark clothing wades through a river."
sim=m.caption_similarity(a,b,"en")
ok("real factual pair similarity around old fail band", .82 <= sim < .95, str(sim))
ok("real factual pair no longer hard fail", not m.export_repeat_issue(b,[a],"en"), m.export_repeat_issue(b,[a],"en"))
ok("real factual pair remains QA warning", bool(m.export_repeat_warning(b,[a],"en")), m.export_repeat_warning(b,[a],"en"))

# Exact/catchphrase/reviewer loops must still be hard.
x="Look at that, hands are doing the heavy lifting here."
ok("exact duplicate still hard", m.export_repeat_issue(x,[x],"en")=="exact duplicate", m.export_repeat_issue(x,[x],"en"))
ok("reused reviewer opener still hard",
   "reused reviewer opening" in m.export_repeat_issue(
      "Look at that, this stone circle is getting much tighter.", [x], "en"),
   m.export_repeat_issue("Look at that, this stone circle is getting much tighter.", [x], "en"))
ok("catchphrase family still hard",
   "reused reviewer phrase family" in m.export_repeat_issue(
      "That mesh becomes the secret weapon for this entire build.",
      ["The secret weapon finally appears beside the river stones."], "en"),
   m.export_repeat_issue("That mesh becomes the secret weapon for this entire build.",
                         ["The secret weapon finally appears beside the river stones."], "en"))

# Conservative word-fit cases from the actual failure pattern.
cases=[
("A person constructs a circular stone barrier in a flowing river.",10),
("A person in dark clothing wades through shallow water.",10),
("A person in dark clothing wades through a river.",10),
]
for i,(line,target) in enumerate(cases,1):
    fixed=m.fit_en_exact_target(line,target)
    ok(f"word fit {i} -> 10", m.caption_units(fixed,"en")==10, f"{m.caption_units(fixed,'en')}: {fixed}")
    ok(f"word fit {i} complete", not m.caption_fragment_issue(fixed,"en"), fixed)

# Old 40-caption loop must still be detected aggressively.
fixture=[
"Okay, why is our DIY wizard building this right here?",
"That concrete layer says this build is basically a tank.",
"Secret weapon time, and suddenly this weird setup makes sense.",
"Boom, that fish just turned patience into a proper payoff.",
"Look at that, hands are doing the heavy lifting here.",
"This is where the real magic starts happening.",
"Wait, is that a fish or is that a trick of the light?",
"Look at that, hands are doing the heavy lifting here.",
"This is where the real magic starts happening.",
"Wait, is that a fish or is that a trick of the light?",
]
h=[]; hard=[]
for i,line in enumerate(fixture,1):
    issue=m.export_repeat_issue(line,h,"en")
    if issue: hard.append((i,issue))
    h.append(line)
ok("old loop catches caption 8", any(i==8 for i,_ in hard), str(hard))
ok("old loop catches caption 9", any(i==9 for i,_ in hard), str(hard))
ok("old loop catches caption 10", any(i==10 for i,_ in hard), str(hard))

# Gold rhythm unchanged.
target,hardmax=m.caption_budget("en",4.08,"story_review")
ok("Gold Rhythm target unchanged", target==10 and hardmax==12, f"{target}/{hardmax}")
slots=m.continuous_caption_slots(275.808867,"en")
ok("66 slots unchanged", len(slots)==66, str(len(slots)))
ok("0.10 gap unchanged", all(abs(slots[i][0]-slots[i-1][1]-.10)<2e-6 for i in range(1,len(slots))))

source=(ROOT/"engine.py").read_text(encoding="utf-8")
ok("per-caption final gate present", "FINAL ANTI-REPEAT V3" in source and "for attempt in range(1, 4)" in source)
ok("batch validator structural only", "Structural validator only" in source)
ok("nonfatal factual QA present", "nonfatal_factual_similarity" in source)
ok("GPU recovery preserved", '"num_gpu": -1' in source and "GPU_PREFLIGHT_5.5.3b.json" in source)

for name,state,detail in checks:
    print(("PASS" if state else "FAIL"), name, detail)
print(f"PASS_TOTAL={sum(x[1] for x in checks)}/{len(checks)}")
