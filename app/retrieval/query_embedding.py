"""Create local query embeddings using the verified mean-pooling settings."""

from math import isfinite
from threading import Lock
from typing import Any

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
MODEL_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
EMBEDDING_DIMENSION = 1024
MAX_LENGTH = 512

_cached_components: tuple[Any, Any] | None = None
_load_lock = Lock()


def _get_local_components() -> tuple[Any, Any]:
    """Load the tokenizer and CPU model once per process, without downloads."""
    global _cached_components

    with _load_lock:
        if _cached_components is None:
            import torch
            from transformers import AutoModel, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME,
                revision=MODEL_REVISION,
                local_files_only=True,
                trust_remote_code=False,
                token=False,
            )
            tokenizer.padding_side = "right"
            tokenizer.truncation_side = "right"

            model = AutoModel.from_pretrained(
                MODEL_NAME,
                revision=MODEL_REVISION,
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
                token=False,
            ).to(device="cpu", dtype=torch.float32)
            model.eval()
            _cached_components = (tokenizer, model)

        return _cached_components


def embed_query_local(text: str) -> list[float]:
    """Embed the original query; return 1024 finite, L2-normalized floats.

    Empty or non-string inputs raise ValueError before model loading.
    Loading and inference errors propagate to the caller.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text는 공백이 아닌 문자를 포함한 문자열이어야 합니다.")

    tokenizer, model = _get_local_components()
    import torch

    inputs = tokenizer(
        [text],
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    inputs = {key: value.to("cpu") for key, value in inputs.items()}

    with torch.no_grad():
        token_embeddings = model(**inputs).last_hidden_state
        expanded_mask = (
            inputs["attention_mask"]
            .unsqueeze(-1)
            .expand(token_embeddings.size())
            .float()
        )
        pooled = (token_embeddings * expanded_mask).sum(1) / (
            expanded_mask.sum(1).clamp(min=1e-9)
        )
        normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
        vector = normalized[0].cpu().tolist()

    if len(vector) != EMBEDDING_DIMENSION or not all(
        isinstance(value, float) and isfinite(value) for value in vector
    ):
        raise RuntimeError("질문 임베딩은 유한한 실수 1024개여야 합니다.")

    return vector
