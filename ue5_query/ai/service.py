import os
import threading
from typing import Iterator, List, Dict, Optional, Callable
from pathlib import Path

# Optional import to allow running without the lib installed initially
try:
    import anthropic
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    Anthropic = None

from ue5_query.utils.logger import get_project_logger
from ue5_query.utils.config_manager import ConfigManager

logger = get_project_logger(__name__)

class IntelligenceService:
    """
    Manages interaction with the LLM provider (Anthropic Claude).
    Handles authentication, prompt construction, and streaming responses.
    """
    
    DEFAULT_MODEL = "claude-3-haiku-20240307"
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.client: Optional[Anthropic] = None
        self.api_key: str = ""
        self.model: str = self.DEFAULT_MODEL
        self._is_initialized = False
        
        self.initialize()

    def initialize(self) -> bool:
        """Initialize the Anthropic client using config"""
        if not HAS_ANTHROPIC:
            logger.warning("Anthropic library not found. AI features will be disabled.")
            return False

        self.api_key = self.config.get("ANTHROPIC_API_KEY", "")
        self.model = self.config.get("ANTHROPIC_MODEL", self.DEFAULT_MODEL)

        if not self.api_key or self.api_key == "your_api_key_here":
            logger.info("Anthropic API key not configured. AI features will be disabled.")
            return False

        try:
            self.client = Anthropic(api_key=self.api_key)
            self._is_initialized = True
            logger.info(f"IntelligenceService initialized with model: {self.model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            return False

    def is_available(self) -> bool:
        return self._is_initialized

    def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        system_prompt: str = "",
        on_token: Callable[[str], None] = None,
        on_complete: Callable[[str], None] = None,
        on_error: Callable[[str], None] = None
    ):
        """
        Stream a chat completion from Claude.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: System context instruction
            on_token: Callback for each text chunk (str)
            on_complete: Callback when done (full_text)
            on_error: Callback for exceptions
        """
        if not self.is_available():
            if on_error:
                on_error("AI Service not initialized. Please configure API Key.")
            return

        def _run():
            full_response = []
            try:
                with self.client.messages.stream(
                    max_tokens=4096,
                    messages=messages,
                    model=self.model,
                    system=system_prompt,
                ) as stream:
                    for text in stream.text_stream:
                        full_response.append(text)
                        if on_token:
                            # Use root.after logic in the view, here we just call the callback
                            on_token(text)
                
                final_text = "".join(full_response)
                if on_complete:
                    on_complete(final_text)

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                if on_error:
                    on_error(str(e))

        # Run in background thread
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def test_connection(self) -> Dict[str, any]:
        """Verify API connectivity"""
        if not self.is_available():
            return {"success": False, "message": "Service not initialized"}
            
        try:
            message = self.client.messages.create(
                max_tokens=10,
                messages=[{"role": "user", "content": "Ping"}],
                model=self.model,
            )
            return {"success": True, "message": message.content[0].text}
        except Exception as e:
            return {"success": False, "message": str(e)}
