import os
import gc
import time
import numpy as np
from typing import List, Optional, Tuple
import logging

try:
    from sentence_transformers import SentenceTransformer
    import torch
except ImportError:
    SentenceTransformer = None
    torch = None

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from ue5_query.utils.logger import get_project_logger

logger = get_project_logger(__name__)

class EmbeddingProcessor:
    """
    Handles model loading, device management, and robust text embedding
    with adaptive batch sizing and error recovery.
    """
    def __init__(self, model_name: str, use_gpu: str = "auto", batch_size: int = 16):
        self.model_name = model_name
        self.use_gpu_config = use_gpu
        self.batch_size = batch_size
        self.model = None
        self.device = "cpu"
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the SentenceTransformer model with appropriate device settings."""
        if not SentenceTransformer:
            raise ImportError("sentence-transformers is required for EmbeddingProcessor")

        self.model = SentenceTransformer(self.model_name)
        self.device = "cpu"

        if self.use_gpu_config == "auto":
            if torch and torch.cuda.is_available():
                self.device = "cuda"
                self._log_gpu_info()
            else:
                logger.info("GPU not detected or Torch not available, using CPU")
        elif self.use_gpu_config == "true":
            if torch:
                self.device = "cuda"
                self._log_gpu_info()
            else:
                logger.error("GPU forced but Torch not available")
                raise RuntimeError("GPU forced but Torch not available")

        self.model = self.model.to(self.device)
        logger.info(f"Model loaded on {self.device} with batch size {self.batch_size}")

    def _log_gpu_info(self):
        """Log details about the detected GPU."""
        try:
            gpu_name = torch.cuda.get_device_name(0)
            capability = torch.cuda.get_device_capability(0)
            sm_version = capability[0] * 10 + capability[1]
            
            mode_msg = "native support"
            if sm_version > 120:
                mode_msg = "PTX compatibility mode (SM > 12.0)"
            
            logger.info(f"GPU detected: {gpu_name} (SM {capability[0]}.{capability[1]}) - {mode_msg}")
        except Exception as e:
            logger.warning(f"Could not retrieve detailed GPU info: {e}")

    def embed_batches(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of texts using adaptive batch sizing and robust error handling.
        """
        if not texts:
            return np.zeros((0, self.model.get_sentence_embedding_dimension()))

        # Pre-process texts with strict truncation
        processed_texts = self._preprocess_texts(texts)
        
        all_vecs = []
        cuda_failed = False
        current_batch_size = self.batch_size
        cuda_error_count = 0
        
        bar = tqdm(total=len(processed_texts), desc="Embedding chunks", unit="chunk") if tqdm else None
        
        i = 0
        while i < len(processed_texts):
            batch = processed_texts[i:i + current_batch_size]
            
            try:
                # Attempt encoding
                vecs = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    batch_size=current_batch_size,
                    device=self.device
                )
                all_vecs.append(vecs)
                
                # Success - reset error counters
                cuda_error_count = 0
                i += len(batch)
                if bar: bar.update(len(batch))

            except (IndexError, RuntimeError) as e:
                # Handle errors
                error_msg = str(e).lower()
                is_cuda_error = 'cuda' in error_msg or 'device' in error_msg or 'gpu' in error_msg
                
                if is_cuda_error and not cuda_failed:
                    cuda_error_count += 1
                    logger.warning(f"CUDA error at batch {i} (attempt {cuda_error_count}): {str(e)[:100]}")
                    
                    if cuda_error_count <= 4 and current_batch_size > 1:
                        # Reduce batch size
                        current_batch_size = max(1, current_batch_size // 2)
                        logger.info(f"Reducing batch size to {current_batch_size} and retrying...")
                        time.sleep(1) # Let GPU cool down/reset
                        continue
                    else:
                        # Fallback to CPU
                        logger.error("Max retries reached or batch size 1 failed. Falling back to CPU.")
                        self._fallback_to_cpu()
                        cuda_failed = True
                        continue
                else:
                    # CPU or other error - try individual encoding as last resort
                    logger.error(f"Encoding failed on {self.device}: {str(e)[:100]}. Trying individual fallback.")
                    self._encode_individually(batch, all_vecs)
                    i += len(batch)
                    if bar: bar.update(len(batch))

        if bar: bar.close()
        
        if cuda_failed:
            logger.info("Completed with CPU fallback.")
            
        return np.vstack(all_vecs)

    def _preprocess_texts(self, texts: List[str]) -> List[str]:
        """Truncate texts safely to avoid tokenizer errors."""
        max_seq = getattr(self.model, 'max_seq_length', 512)
        safe_max = max_seq - 10
        tokenizer = getattr(self.model, 'tokenizer', None)
        
        processed = []
        for text in texts:
            if tokenizer:
                try:
                    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=True, max_length=safe_max)
                    text = tokenizer.decode(tokens, skip_special_tokens=True)
                except Exception:
                    text = text[:safe_max * 4]
            else:
                text = text[:safe_max * 4]
            processed.append(text)
        return processed

    def _fallback_to_cpu(self):
        """Force model to CPU mode, clearing GPU memory."""
        try:
            del self.model
            gc.collect()
            if torch:
                torch.cuda.empty_cache()
        except:
            pass
            
        logger.info("Re-initializing model on CPU...")
        self.model = SentenceTransformer(self.model_name, device='cpu')
        self.device = 'cpu'

    def _encode_individually(self, batch: List[str], all_vecs: List[np.ndarray]):
        """Encode items one by one as a last resort."""
        dims = self.model.get_sentence_embedding_dimension()
        for text in batch:
            try:
                vec = self.model.encode([text], convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False)
                all_vecs.append(vec)
            except Exception as e:
                logger.error(f"Failed to encode single chunk: {e}")
                all_vecs.append(np.zeros((1, dims)))
