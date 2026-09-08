"""Standalone sentence-completeness rules for 5.5.6.
Kept separate so the release can regression-test grammar rules independently.
"""
from __future__ import annotations

import re

FINITE = {
    "is","are","was","were","has","have","had","shows","show","remains","remain","appears","appear",
    "walks","walk","approaches","approach","enters","enter","exits","exit","opens","open","closes","close",
    "carries","carry","pulls","pull","holds","hold","lifts","lift","steps","step","climbs","climb",
    "ascends","ascend","descends","descend","passes","pass","moves","move","stands","stand","sits","sit",
    "turns","turn","faces","face","reaches","reach","uses","use","cuts","cut","clears","clear","trims","trim",
    "removes","remove","places","place","adds","add","installs","install","stacks","stack","builds","build",
    "crosses","cross","continues","continue","leads","lead","extends","extend","contains","contain","includes","include",
    "surrounds","surround","covers","cover","indicates","indicate","describes","describe","reveals","reveal",
    "looks","look","sweeps","sweep","travels","travel","follows","follow","heads","head","leaves","leave",
    "wears","wear","pulls","pull","pushes","push","raises","raise","lowers","lower","holds","hold"
}
BAD_STARTS = {"with","then","and","but","which","because","while","although","though","unless","as","surrounded"}
GERUND_STARTS = {
    "approaching","walking","moving","showing","revealing","carrying","holding","placing","adding","cutting",
    "building","stacking","opening","closing","entering","leaving","standing","sitting","kneeling","arranging",
    "cleaning","removing","installing","crossing","following","trimming","clearing","pulling","lifting"
}
BAD_ENDS = {
    "than","what","which","who","whom","whose","because","while","although","though","until","if","and","but","or",
    "to","of","with","for","from","is","are","was","were","be","been","being","how","a","an","the",
    "surrounded","toward","through","along","beside"
}
INCOMPLETE_ADJECTIVE_END = {"wooden","painted","broken","unfinished","overgrown","traditional","large","small","open","closed"}


def words(text):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text or "").lower().replace("’", "'"))


def fragment_issue(text, language="en"):
    value = " ".join(str(text or "").strip().split())
    if not value:
        return "empty"
    if language == "ja":
        compact = re.sub(r"\s+", "", value).rstrip("。！？")
        if compact.endswith(("けど", "ので", "から", "ながら", "そして", "でも")):
            return "dangling Japanese connective"
        return ""

    plain = value.lstrip('"\'“‘(')
    if plain and plain[0].isalpha() and plain[0].islower():
        return "starts lowercase like a carried-over clause"
    ws = words(value)
    if not ws:
        return "empty"
    first, last = ws[0], ws[-1]
    if first in BAD_STARTS:
        return "starts with dependent/linking phrase"
    if first in GERUND_STARTS:
        return "starts like a visual-log fragment"
    if last in BAD_ENDS:
        return "ends with dangling/incomplete word"
    # Material nouns like glass/stone/brick/metal are valid sentence endings.
    # Flag adjective endings only when they are grammatically stranded.
    if last in INCOMPLETE_ADJECTIVE_END and len(ws) >= 2 and ws[-2] in {"a","an","the","from","toward","of"}:
        return "ends with stranded adjective"
    if not any(w in FINITE for w in ws):
        return "no finite visual verb"
    return ""
