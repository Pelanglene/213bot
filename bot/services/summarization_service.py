"""Summarization service using local Hugging Face causal model (Vikhr-Llama-3.2-1B-Instruct).

Loads the model lazily on first use and performs summarization on provided
text content. Designed for on-device inference.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
)


logger = logging.getLogger(__name__)


class SummarizationService:
    """Wrap Hugging Face text-generation pipeline for Vikhr-Llama-3.2-1B-Instruct."""

    def __init__(self, model_name: str = "Vikhrmodels/Vikhr-Llama-3.2-1B-Instruct"):
        self.model_name = model_name
        self._pipe = None  # type: ignore[var-annotated]
        self._tokenizer = None  # type: ignore[var-annotated]

    def _ensure_pipeline(self) -> None:
        if self._pipe is not None:
            return
        try:
            # Allow user to control device placement via env.
            # Auto device selection: use GPU if available; else CPU.
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if getattr(tokenizer, "pad_token", None) is None and getattr(tokenizer, "eos_token", None) is not None:
                tokenizer.pad_token = tokenizer.eos_token  # type: ignore[attr-defined]
            model = AutoModelForCausalLM.from_pretrained(self.model_name)
            device = 0 if os.getenv("CUDA_AVAILABLE", "").lower() == "true" else -1
            self._pipe = pipeline(
                task="text-generation",
                model=model,
                tokenizer=tokenizer,
                device=device,
            )
            self._tokenizer = tokenizer
            logger.info(
                f"Initialized summarization pipeline for {self.model_name} (device={device})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize summarization pipeline: {e}")
            raise

    def summarize_text(
        self,
        text: str,
        min_length: int = 48,
        max_length: int = 320,
        *,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        num_beams: int = 4,
        no_repeat_ngram_size: int = 4,
        repetition_penalty: float = 1.15,
        early_stopping: bool = True,
        do_sample: bool = True,
    ) -> str:
        """Summarize input text.

        Args:
            text: Raw input text to summarize.
            min_length: Minimum tokens for summary.
            max_length: Maximum tokens for summary.
        """
        self._ensure_pipeline()
        assert self._pipe is not None

        # Русская few-shot инструкция с примерами и явной меткой "Сводка:"
        prompt = (
            "Ты аналитик групповых чатов. Составь краткую сводку за сегодняшний день. "
            "Формат: маркированный список (каждый пункт начинается с '- '). Пиши по делу, без повторов, 3–8 пунктов. "
            "Если сообщений мало — 1–3 пункта. Не цитируй дословно, обобщай. Язык: русский.\n\n"
            "Пример 1:\n"
            "Диалог:\n"
            "[09:10] Привет всем! Давайте созвонимся вечером.\n"
            "[09:15] Ок, 19:00 подходит.\n"
            "[09:16] Да, согласен.\n"
            "Сводка:\n"
            "- Договорились созвониться в 19:00.\n\n"
            "Пример 2:\n"
            "Диалог:\n"
            "[12:05] Нашёл баг в форме оплаты.\n"
            "[12:07] Создам тикет и пофиксим к вечеру.\n"
            "[12:20] Я возьму на себя проверку.\n"
            "Сводка:\n"
            "- Выявлен баг в оплате; завели тикет; фикc запланирован на вечер; проверка назначена.\n\n"
            "Пример 3:\n"
            "Диалог:\n"
            "[18:30] Кто идёт на футбол завтра?\n"
            "[18:32] Я +1.\n"
            "[18:35] Беру билеты на 7 человек.\n"
            "Сводка:\n"
            "- Организовали поход на футбол; купят 7 билетов.\n\n"
            "Теперь сделай сводку для следующего диалога за сегодня:\n\n"
            f"{text.strip()}\n\n"
            "Сводка:\n"
        )

        try:
            # Truncate overly long inputs by characters to avoid OOM.
            truncated = prompt[:32000]
            max_new_tokens = max(64, min(max_length, 256))
            min_new_tokens = max(16, min(min_length, 128))
            eos_id = None
            try:
                eos_id = self._tokenizer.eos_token_id if self._tokenizer is not None else None
            except Exception:
                eos_id = None
            outputs = self._pipe(
                truncated,
                # Generation controls for causal LM
                max_new_tokens=max_new_tokens,
                min_new_tokens=min_new_tokens,
                do_sample=do_sample,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                num_beams=num_beams,
                no_repeat_ngram_size=no_repeat_ngram_size,
                repetition_penalty=repetition_penalty,
                early_stopping=early_stopping,
                truncation=True,
                eos_token_id=eos_id,
                pad_token_id=(self._tokenizer.pad_token_id if self._tokenizer else None),
                return_full_text=False,
            )
            if isinstance(outputs, list) and outputs:
                summary = outputs[0].get("generated_text") or outputs[0].get("summary_text")
                if isinstance(summary, str) and summary.strip():
                    cleaned = self._postprocess_summary(summary.strip())
                    return cleaned
            logger.warning("Summarization pipeline returned no text; returning fallback")
            return "(no summary)"
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "(summary failed)"

    @staticmethod
    def _postprocess_summary(text: str) -> str:
        """Lightweight cleanup to reduce trivial repetition artifacts.

        - Collapse consecutive duplicate sentences
        - Normalize excessive whitespace
        """
        # Split into sentences by simple punctuation heuristic
        parts = re.split(r"(?<=[\.!?])\s+", text)
        deduped = []
        last = None
        for p in parts:
            s = p.strip()
            if not s:
                continue
            if last is not None and s == last:
                continue
            deduped.append(s)
            last = s
        result = " ".join(deduped)
        # Also collapse triple repeated words phrases (very naive safeguard)
        result = re.sub(r"(\b\w+(?:\s+\w+){0,5}\b)(?:\s+\1){2,}", r"\1", result)
        return result.strip()


# Global singleton service
summarization_service = SummarizationService()


