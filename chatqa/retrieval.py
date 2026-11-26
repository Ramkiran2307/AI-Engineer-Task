"""Tiny BM25 retriever, used only when a chat is too large to send whole."""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9ऀ-ॿ]+")
STOPWORDS = set("""
a an the is are was were be been am i you we he she it they me my our your his her their them this that these those
of to in on at for with by from and or but not no so do does did done what who whom which when where why how
is's has have had will would can could should shall may might must there here than then also just only very
hai hain ho tha thi the ka ki ke ko se ne me mein par pe bhi to toh aur ya kya kaun kab kahan kyun kaise hi na
""".split())


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.4, b: float = 0.75):
        self.docs = [tokenize(d) for d in docs]
        self.k1, self.b = k1, b
        self.avgdl = (sum(len(d) for d in self.docs) / len(self.docs)) if self.docs else 0
        df = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def _term_score(self, i: int, t: str) -> float:
        f = self.tf[i].get(t, 0)
        if not f:
            # cheap prefix match helps Hinglish/English inflections (payment ~ payments)
            f = sum(c for w, c in self.tf[i].items() if len(t) >= 4 and (w.startswith(t) or t.startswith(w)) and len(w) >= 4) * 0.5
            if not f:
                return 0.0
        dl = len(self.docs[i])
        idf = self.idf.get(t, math.log(1 + len(self.docs)))
        return idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1)))

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        return [sum(self._term_score(i, t) for t in q) for i in range(len(self.docs))]

    def top(self, query: str, k: int) -> list[int]:
        s = self.scores(query)
        ranked = sorted(range(len(s)), key=lambda i: -s[i])
        return [i for i in ranked[:k] if s[i] > 0]
