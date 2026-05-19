from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoTokenizer

from .modeling import PhoBertWithCoAttentionPooling
from .preprocess import segment_text


class ClickbaitPredictor:
    def __init__(self, model_path: Path | None = None, max_length: int = 256):
        repo_root = Path(__file__).resolve().parents[2]
        self.model_path = str(
            model_path
            or repo_root / "result" / "results_phoBERT" / "phobert_base_improve" / "best_model"
        )
        self.max_length = max_length
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, local_files_only=True)
        self.model = PhoBertWithCoAttentionPooling.from_pretrained(
            self.model_path,
            num_labels=2,
            local_files_only=True,
        )
        self.model.to(self.device)
        self.model.eval()

    def predict(self, title: str, lead_paragraph: str) -> float:
        title_segmented = segment_text(title)
        lead_segmented = segment_text(lead_paragraph)
        encoded = self.tokenizer(
            title_segmented,
            lead_segmented,
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        with torch.no_grad():
            outputs = self.model(**encoded)
            probabilities = torch.softmax(outputs.logits, dim=-1)
        return float(probabilities[0, 1].detach().cpu().item())


@lru_cache(maxsize=1)
def get_predictor() -> ClickbaitPredictor:
    return ClickbaitPredictor()
