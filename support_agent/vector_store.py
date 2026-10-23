"""轻量级向量库。

- 默认使用「本地哈希向量」(numpy 实现，无需外部 embedding 服务)，开箱即用。
- 若在后台配置了 OpenAI 兼容 embedding，则自动升级为语义向量。
- 支持 save/load 持久化到 data/vectors.json，满足「知识库向量库」需求。
"""
import hashlib
import json
import os
import re

import numpy as np

from config import VECTOR_PATH
from llm import embed_texts, get_llm_config


def hash_embed(text, dim=512):
    """字符 n-gram + 词元哈希，生成归一化向量（中文可用）。"""
    text = (text or "").lower()
    vec = np.zeros(dim, dtype=np.float32)
    for n in (2, 3):
        for i in range(len(text) - n + 1):
            gram = text[i:i + n]
            h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16) % dim
            vec[h] += 1.0
    for w in re.findall(r"[a-z0-9\u4e00-\u9fff]+", text):
        h = int(hashlib.md5(("w:" + w).encode("utf-8")).hexdigest(), 16) % dim
        vec[h] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


class VectorStore:
    def __init__(self, name, path=VECTOR_PATH):
        self.name = name
        self.path = path
        cfg = get_llm_config()
        self.dim = int(cfg.get("vector_dim", 512) or 512)
        self.ids = []
        self.metadata = []
        self.vectors = np.empty((0, self.dim), dtype=np.float32)

    # ---------- 向量化 ----------
    def _embed(self, texts):
        vecs = embed_texts(texts)
        if vecs is not None:
            arr = np.asarray(vecs, dtype=np.float32)
            if arr.shape[1] != self.dim:
                self.dim = arr.shape[1]
                self.vectors = np.empty((0, self.dim), dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1
            return arr / norms
        return np.stack([hash_embed(t, self.dim) for t in texts])

    # ---------- 增删查 ----------
    def add(self, doc_id, text, metadata=None):
        vec = self._embed([text])[0]
        self.ids.append(str(doc_id))
        self.metadata.append(metadata or {})
        self.vectors = np.vstack([self.vectors, vec])

    def remove(self, doc_id):
        doc_id = str(doc_id)
        idx = [i for i, x in enumerate(self.ids) if x == doc_id]
        if idx:
            keep = [i for i in range(len(self.ids)) if i not in idx]
            self.ids = [self.ids[i] for i in keep]
            self.metadata = [self.metadata[i] for i in keep]
            self.vectors = self.vectors[keep]

    def clear(self):
        self.ids, self.metadata = [], []
        self.vectors = np.empty((0, self.dim), dtype=np.float32)

    def search(self, query, k=5):
        if len(self.ids) == 0:
            return []
        q = self._embed([query])[0]
        sims = self.vectors @ q
        order = np.argsort(-sims)[:k]
        results = []
        for i in order:
            results.append({
                "id": self.ids[i],
                "score": float(sims[i]),
                "metadata": self.metadata[i],
            })
        return results

    # ---------- 持久化 ----------
    def save(self):
        payload = {
            "name": self.name,
            "dim": self.dim,
            "ids": self.ids,
            "metadata": self.metadata,
            "vectors": self.vectors.tolist(),
        }
        data = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[self.name] = payload
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self):
        if not os.path.exists(self.path):
            return False
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False
        if self.name not in data:
            return False
        p = data[self.name]
        self.dim = int(p["dim"])
        self.ids = p["ids"]
        self.metadata = p["metadata"]
        self.vectors = np.asarray(p["vectors"], dtype=np.float32)
        return True
