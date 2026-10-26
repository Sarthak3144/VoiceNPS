"""Matching spoken names by how they SOUND, so speech-recognition spellings still find the right
contact: "Seeta" ~ Sita, "Rommesh" ~ Ramesh, "Bhatrai" ~ Bhattarai, "Quarala" ~ Koirala.
Devanagari input is converted to Latin first, so सीता, सिता and Seeta all match "Sita Koirala"."""
import re
from difflib import SequenceMatcher

from .nepali import roman


def _norm(w: str) -> str:
    """Rough phonetic form so 'Seeta'~'Sita', 'Bhatarai'~'Bhattarai', 'Rameesh'~'Ramesh'."""
    w = w.lower()
    for a, b in (("ee", "i"), ("oo", "u"), ("aa", "a"), ("ii", "i"), ("bh", "b"), ("dh", "d"), ("gh", "g"),
                 ("kh", "k"), ("th", "t"), ("ph", "f"), ("sh", "s"), ("w", "v"), ("z", "j")):
        w = w.replace(a, b)
    out = []
    for ch in w:
        if not out or out[-1] != ch:
            out.append(ch)
    return "".join(out)


def skeleton(word: str) -> str:
    """Consonant skeleton: Sita/Seeta/Sheeta/Citta -> 'st', Koirala/Quarala -> 'krl', Bhattarai/Bhatrai -> 'btr'."""
    w = re.sub(r"[^a-z]", "", roman(word))
    for a, b in (("ch", "C"), ("bh", "b"), ("dh", "d"), ("gh", "g"), ("kh", "k"), ("th", "t"), ("ph", "p"),
                 ("jh", "j"), ("sh", "s"), ("ck", "k"), ("qu", "k"), ("q", "k"), ("x", "ks"), ("w", "v"),
                 ("z", "j")):
        w = w.replace(a, b)
    w = re.sub(r"c(?=[eiy])", "s", w).replace("c", "k")
    w = w.lower()
    w = re.sub(r"[aeiouy]", "", w)
    w = w[:1] + w[1:].replace("h", "")
    return re.sub(r"(.)\1+", r"\1", w)


def tok_score(a: str, b: str) -> float:
    sa, sb = skeleton(a), skeleton(b)
    ratio_norm = SequenceMatcher(None, _norm(roman(a)), _norm(roman(b))).ratio()
    if len(sa) >= 2 and sb:
        ratio_skel = 0.95 if sa == sb else SequenceMatcher(None, sa, sb).ratio() * 0.9
    else:
        ratio_skel = 0.0
    return max(ratio_norm, ratio_skel)


def phonetic_match(spoken: str, full_name: str) -> bool:
    """Every spoken word must sound like some word of the saved name."""
    stoks, ctoks = spoken.split(), full_name.split()
    return bool(stoks) and all(any(tok_score(s, c) >= 0.8 for c in ctoks) for s in stoks)


def best_suggestion(spoken: str, contacts):
    """Closest contact when nothing matched; None if nothing is close or two different people tie."""
    stoks = spoken.split()
    if not stoks:
        return None
    scored = []
    for c in contacts:
        ctoks = c.name.split()
        per = [max((tok_score(s, ct) for ct in ctoks if skeleton(s)[:1] == skeleton(ct)[:1]), default=0.0)
               for s in stoks]                       # each spoken word must start with the same sound
        scored.append((sum(per) / len(per), c))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < 0.7:
        return None
    if len(scored) > 1 and scored[1][0] >= scored[0][0] - 0.05 and scored[1][1].name != scored[0][1].name:
        return None
    return scored[0][1]
