"""Tiny TF-IDF + cosine concept search (pure Python) used by the 'Ask the course' tab."""
import math, re
from collections import Counter

def _tok(t): return [w for w in re.findall(r"[a-z0-9$/]+", t.lower()) if len(w) > 1]

class Index:
    def __init__(self, docs):  # docs: list of (title, text)
        self.docs = docs; toks = [Counter(_tok(a + " " + b)) for a, b in docs]; n = len(docs)
        df = Counter(w for c in toks for w in c)
        self.idf = {w: math.log((n + 1) / (d + 1)) + 1 for w, d in df.items()}
        self.vec = [self._v(c) for c in toks]
    def _v(self, c):
        v = {w: f * self.idf.get(w, 0) for w, f in c.items()}; n = math.sqrt(sum(x * x for x in v.values())) or 1
        return {w: x / n for w, x in v.items()}
    def search(self, q, k=3):
        qv = self._v(Counter(_tok(q)))
        sc = sorted(((sum(x * d.get(w, 0) for w, x in qv.items()), i) for i, d in enumerate(self.vec)), reverse=True)
        return [(self.docs[i], s) for s, i in sc[:k] if s > 0]
