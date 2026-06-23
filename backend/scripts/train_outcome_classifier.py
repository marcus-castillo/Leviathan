"""Fine-tune a HuggingFace sequence classifier for opinion outcome prediction.

This is an optional upgrade over the rule-based fallback in ``app/nlp/outcome.py``. Provide a labeled
JSONL with records ``{"text": ..., "label": "plaintiff|defendant|mixed|unknown"}`` and point
``OUTCOME_MODEL_PATH`` at the resulting directory.

Usage:
    python -m scripts.train_outcome_classifier --data labels.jsonl --out artifacts/outcome-model

Designed to run on CPU for a smoke test; use a GPU for real training.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LABELS = ["plaintiff", "defendant", "mixed", "unknown"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}


def load_jsonl(path: str):
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="labeled JSONL")
    ap.add_argument("--out", default="artifacts/outcome-model")
    ap.add_argument("--base", default="distilbert-base-uncased")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=512)
    args = ap.parse_args()

    import numpy as np
    from datasets import Dataset
    from sklearn.metrics import accuracy_score, f1_score
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    rows = load_jsonl(args.data)
    texts = [r["text"][: args.max_len * 4] for r in rows]
    labels = [LABEL2ID[r["label"]] for r in rows]
    ds = Dataset.from_dict({"text": texts, "label": labels}).train_test_split(test_size=0.2, seed=42)

    tok = AutoTokenizer.from_pretrained(args.base)

    def tokenize(batch):
        return tok(batch["text"], truncation=True, max_length=args.max_len)

    ds = ds.map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.base, num_labels=len(LABELS),
        id2label={i: l for l, i in LABEL2ID.items()}, label2id=LABEL2ID,
    )

    def metrics(eval_pred):
        logits, y = eval_pred
        pred = np.argmax(logits, axis=-1)
        return {"accuracy": accuracy_score(y, pred),
                "f1_macro": f1_score(y, pred, average="macro")}

    targs = TrainingArguments(
        output_dir=args.out, num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch, per_device_eval_batch_size=args.batch,
        eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
        metric_for_best_model="f1_macro", logging_steps=20,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=ds["train"],
                      eval_dataset=ds["test"], compute_metrics=metrics)
    trainer.train()
    trainer.save_model(args.out)
    tok.save_pretrained(args.out)
    print(f"Saved model to {args.out}. Set OUTCOME_MODEL_PATH={args.out} to use it.")


if __name__ == "__main__":
    main()
