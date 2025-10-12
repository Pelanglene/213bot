"""Summarization service using local GGUF model via llama-cpp.

Default model: Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF (4-bit). The model
is loaded lazily and cached on disk. Inference is performed locally.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from typing import Optional
from urllib.parse import urlparse
import urllib.request as urlrequest

from llama_cpp import Llama
from huggingface_hub import hf_hub_download


logger = logging.getLogger(__name__)


class SummarizationService:
    """Wrap llama-cpp generation for Vikhr GGUF model."""

    def __init__(self, model_repo_or_path: str = "Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF"):
        self.model_repo_or_path = model_repo_or_path
        self._llm: Optional[Llama] = None

    def _ensure_llm(self) -> None:
        if self._llm is not None:
            return
        try:
            # Resolve model path: allow local absolute path via env, else HF cache location
            model_path = os.getenv("LLAMA_MODEL_PATH")
            if not model_path or not os.path.exists(model_path):
                # Prefer direct URL download when provided
                cache_dir = os.getenv("HUGGINGFACE_HUB_CACHE") or "/app/storage/huggingface/hub"
                url = os.getenv(
                    "LLAMA_MODEL_URL",
                    "https://huggingface.co/Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF/resolve/main/Vikhr-Llama-3.2-1B-Q4_K_M.gguf?download=true",
                )
                try:
                    os.makedirs(cache_dir, exist_ok=True)
                except Exception:
                    pass

                filename_env = os.getenv("LLAMA_MODEL_FILE")
                parsed_name = os.path.basename(urlparse(url).path) or "model.gguf"
                filename = filename_env or parsed_name
                dest_path = os.path.join(cache_dir, filename)

                # Download only if not present
                if not os.path.exists(dest_path):
                    try:
                        with urlrequest.urlopen(url) as resp, open(dest_path, "wb") as out:
                            shutil.copyfileobj(resp, out)
                        logger.info(f"Downloaded GGUF model to {dest_path}")
                    except Exception as direct_err:
                        # Fallback: try huggingface_hub by repo/file if configured
                        repo_id = os.getenv(
                            "LLAMA_REPO_ID", "Vikhrmodels/Vikhr-Llama-3.2-1B-instruct-GGUF"
                        )
                        hf_filename = filename_env or "Vikhr-Llama-3.2-1B-instruct-Q4_K_M.gguf"
                        try:
                            dest_path = hf_hub_download(
                                repo_id=repo_id,
                                filename=hf_filename,
                                cache_dir=cache_dir,
                            )
                            logger.info(f"Fetched GGUF via hf_hub_download to {dest_path}")
                        except Exception as dl_err:
                            raise RuntimeError(
                                f"Model file download failed: direct URL error={direct_err}; hf_hub_download error={dl_err}"
                            )

                model_path = dest_path

            n_ctx = int(os.getenv("LLAMA_CTX", "4096"))
            n_threads = int(os.getenv("LLAMA_THREADS", str(os.cpu_count() or 4)))
            n_gpu_layers = int(os.getenv("LLAMA_N_GPU_LAYERS", "0"))

            # Build kwargs without passing None for rope params
            llm_kwargs = dict(
                model_path=model_path,
                n_ctx=n_ctx,
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )
            rope_base_env = (os.getenv("LLAMA_ROPE_FREQ_BASE") or "").strip()
            rope_scale_env = (os.getenv("LLAMA_ROPE_FREQ_SCALE") or "").strip()
            try:
                if rope_base_env and rope_base_env not in ("0", "0.0"):
                    llm_kwargs["rope_freq_base"] = float(rope_base_env)
            except Exception:
                pass
            try:
                if rope_scale_env and rope_scale_env not in ("0", "0.0"):
                    llm_kwargs["rope_freq_scale"] = float(rope_scale_env)
            except Exception:
                pass

            self._llm = Llama(**llm_kwargs)
            logger.info(f"Initialized llama-cpp with model at {model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize llama-cpp model: {e}")
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
        self._ensure_llm()
        assert self._llm is not None

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
            max_tokens = max(64, min(max_length, 256))
            # llama-cpp expects plain generation parameters
            result = self._llm(
                prompt=truncated,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repeat_penalty=repetition_penalty,
                stop=["\n\nДиалог:", "\n\nПример", "\n\nСводка:"],
                echo=False,
            )
            try:
                summary = (result.get("choices", [{}])[0].get("text", "") or "").strip()
            except Exception:
                summary = ""
            if summary:
                cleaned = self._postprocess_summary(summary)
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


