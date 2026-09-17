"""Menjalankan evaluasi RAGAS

install: pip install "ragas<0.2" langchain-anthropic langchain-huggingface datasets

(kolom question/answer/contexts/ground_truth di bawah ini pakai skema ragas 0.1.x;
ragas>=0.2 ganti skema jadi user_input/response/retrieved_contexts/reference —
kalau upgrade, sesuaikan nama kolom di build_ragas_dataset()).

Jalankan: python eval/run_ragas_eval.py

Kalau ada error seperti ini: ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'

Jalankan: pip install "langchain-community<0.4.2" --force-reinstall

"""

from __future__ import annotations
 
import json
import os
import sys
from pathlib import Path
 
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
 
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall
 
from src.llm import answer_question
from src.vectorstore import RegulasiStore
 
EVAL_DIR = Path(__file__).resolve().parent
EVAL_SET_PATH = EVAL_DIR / "eval_dataset.json"
SEED_CORPUS_PATH = EVAL_DIR / "eval_corpus.json"
 
# Konteks spasial kosong: eval ini murni menguji jalur tekstual regulasi,
# bukan integrasi spasial (itu bagian Orang 2 + tahap integrasi Orang 4).
EMPTY_SPATIAL_CTX = {"query": {}, "concessions_at_point": []}
 
 
def _ensure_corpus(store: RegulasiStore) -> None:
    if store.count() > 0:
        return
    print(
        "[!] Vectorstore kosong (chunk asli dari Orang 1 belum ada). "
        "Mengindeks eval_corpus.json — SEMENTARA, khusus eval. "
        "Ganti dengan data pasal.id asli begitu tersedia."
    )
    chunks = json.loads(SEED_CORPUS_PATH.read_text(encoding="utf-8"))
    store.add_chunks(chunks)
 
 
def build_ragas_dataset(store: RegulasiStore) -> EvaluationDataset:
    items = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    samples: list[SingleTurnSample] = []
    for item in items:
        question = item["question"]
        hits = store.query(question, n_results=5)
        contexts = [h["text"] for h in hits]
        answer = answer_question(question, hits, EMPTY_SPATIAL_CTX)
        print(f"[eval] Q: {question}\n       A: {answer[:120]}...\n")
        samples.append(
            SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=contexts,
                reference=item["ground_truth"],
            )
        )
    return EvaluationDataset(samples=samples)
 
 
def main() -> None:
    store = RegulasiStore()
    _ensure_corpus(store)
 
    dataset = build_ragas_dataset(store)
 
    judge_llm = LangchainLLMWrapper(
        ChatAnthropic(model="claude-sonnet-4-6", api_key=os.getenv("ANTHROPIC_API_KEY"))
    )
    judge_emb = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
    )
 
    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(llm=judge_llm),
            LLMContextPrecisionWithReference(llm=judge_llm),
            LLMContextRecall(llm=judge_llm),
        ],
        llm=judge_llm,
        embeddings=judge_emb,
    )
 
    print("\n=== Hasil RAGAS (jalur regulasi) ===")
    print(result)
 
    out_path = EVAL_DIR / "ragas_result.json"
    result.to_pandas().to_json(out_path, orient="records", indent=2, force_ascii=False)
    print(f"\nDetail per-pertanyaan tersimpan di {out_path}")
 
 
if __name__ == "__main__":
    main()