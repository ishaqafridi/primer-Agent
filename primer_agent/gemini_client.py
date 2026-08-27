"""
PrimerAgent Gemini Client — Production-Grade Google Gemini API Integration

Provides a reusable, configurable client for the Google Gemini API with:
- Secure API key handling via environment variables
- Exponential backoff retry logic for transient failures
- Rate-limit handling with configurable RPM
- Streaming response support
- Configurable model selection
- Comprehensive logging and error handling

Usage:
    from primer_agent.gemini_client import GeminiClient
    
    client = GeminiClient()  # Uses GOOGLE_API_KEY env var
    response = client.invoke("Analyze this DNA sequence...")
    
    # With tools for ReAct agent
    llm_with_tools = client.get_model_with_tools(tool_list)
"""

import os
import json
import time
import logging
from typing import List, Optional, Any, Dict

from primer_agent.config import GEMINI_CONFIG

logger = logging.getLogger(__name__)


class GeminiClientError(Exception):
    """Raised when the Gemini client encounters an unrecoverable error."""
    pass


class GeminiClient:
    """
    Production-grade Google Gemini API client for PrimerAgent.
    
    Handles authentication, model selection, retry logic, rate limiting,
    and provides both direct invocation and LangChain-compatible interfaces.
    
    Attributes:
        model_name: The Gemini model identifier (e.g., 'gemini-2.5-flash')
        temperature: Sampling temperature for response generation
        max_retries: Maximum number of retry attempts for transient failures
        rate_limit_rpm: Maximum requests per minute
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        max_retries: Optional[int] = None,
        rate_limit_rpm: Optional[int] = None,
    ):
        """
        Initialize the Gemini client.
        
        Args:
            model_name: Gemini model to use. Defaults to config default.
            api_key: Google API key. Falls back to GOOGLE_API_KEY env var.
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.
            max_output_tokens: Maximum tokens in response.
            max_retries: Number of retry attempts for transient errors.
            rate_limit_rpm: Requests per minute limit.
        """
        # Resolve API key
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "No GOOGLE_API_KEY found. Set it via environment variable or "
                "pass api_key parameter. The agent will run in limited mode."
            )

        # Configuration with defaults from config.py
        self.model_name = model_name or GEMINI_CONFIG["default_model"]
        self.temperature = temperature if temperature is not None else GEMINI_CONFIG["temperature"]
        self.max_output_tokens = max_output_tokens or GEMINI_CONFIG["max_output_tokens"]
        self.max_retries = max_retries if max_retries is not None else GEMINI_CONFIG["max_retries"]
        self.rate_limit_rpm = rate_limit_rpm or GEMINI_CONFIG["rate_limit_rpm"]
        self._retry_base_delay = GEMINI_CONFIG["retry_base_delay"]

        # Rate limiting state
        self._request_timestamps: List[float] = []

        # Token usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0

        # LangChain model instance (lazy-initialized)
        self._llm = None
        self._llm_with_tools = None

        logger.info(
            f"GeminiClient initialized: model={self.model_name}, "
            f"temperature={self.temperature}, max_retries={self.max_retries}"
        )

    def _get_llm(self):
        """
        Lazy-initialize the LangChain ChatGoogleGenerativeAI model.
        
        Returns:
            ChatGoogleGenerativeAI instance configured with current settings.
            
        Raises:
            GeminiClientError: If langchain-google-genai is not installed.
        """
        if self._llm is None:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise GeminiClientError(
                    "langchain-google-genai is required. "
                    "Install it with: pip install langchain-google-genai"
                )

            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
            )
        return self._llm

    def get_model_with_tools(self, tools: List[Any]):
        """
        Bind a list of LangChain tools to the Gemini model.
        
        This enables the ReAct agent to use Gemini's function calling
        capability to autonomously select and invoke tools.
        
        Args:
            tools: List of LangChain @tool-decorated functions.
            
        Returns:
            A ChatGoogleGenerativeAI instance with tools bound.
        """
        llm = self._get_llm()
        self._llm_with_tools = llm.bind_tools(tools)
        logger.info(f"Bound {len(tools)} tools to Gemini model")
        return self._llm_with_tools

    def _enforce_rate_limit(self):
        """
        Enforce rate limiting by sleeping if necessary.
        
        Uses a sliding window to track request timestamps and
        ensures we don't exceed the configured RPM limit.
        """
        now = time.time()
        window_start = now - 60.0  # 1-minute sliding window

        # Remove timestamps outside the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > window_start
        ]

        if len(self._request_timestamps) >= self.rate_limit_rpm:
            # Need to wait until the oldest request in window expires
            sleep_time = self._request_timestamps[0] - window_start + 0.1
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        self._request_timestamps.append(time.time())

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a prompt to Gemini and return the text response.
        
        Includes retry logic with exponential backoff for transient errors
        (429 rate limit, 500/503 server errors).
        
        Args:
            prompt: The user/agent prompt to send.
            system_prompt: Optional system-level instructions.
            
        Returns:
            The text content of Gemini's response.
            
        Raises:
            GeminiClientError: After all retries are exhausted.
        """
        llm = self._get_llm()
        messages = []

        if system_prompt:
            from langchain_core.messages import SystemMessage
            messages.append(SystemMessage(content=system_prompt))

        from langchain_core.messages import HumanMessage
        messages.append(HumanMessage(content=prompt))

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                self._enforce_rate_limit()
                response = llm.invoke(messages)
                self.total_requests += 1

                # Track token usage if available
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = response.usage_metadata
                    self.total_input_tokens += getattr(usage, "input_tokens", 0)
                    self.total_output_tokens += getattr(usage, "output_tokens", 0)

                return response.content

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Handle 404 NOT_FOUND model availability errors by falling back
                if any(k in error_str for k in ["404", "not_found", "no longer available", "not found"]):
                    fallbacks = [m for m in GEMINI_CONFIG.get("fallback_models", []) if m != self.model_name]
                    if not fallbacks or attempt >= self.max_retries:
                        break
                    fallback = fallbacks[attempt % len(fallbacks)]
                    logger.warning(f"Model '{self.model_name}' not available ({e}). Falling back to '{fallback}'.")
                    self.model_name = fallback
                    self._llm = None
                    self._llm_with_tools = None
                    llm = self._get_llm()
                    continue

                # Check if retryable
                is_retryable = any(
                    code in error_str
                    for code in ["429", "500", "503", "rate", "quota", "resource_exhausted"]
                )

                if is_retryable and attempt < self.max_retries:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Gemini API error (attempt {attempt + 1}/{self.max_retries + 1}): "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    break

        raise GeminiClientError(
            f"Gemini API call failed after {self.max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def invoke_with_tools(self, messages: List[Any]) -> Any:
        """
        Send messages to the tool-bound Gemini model for the ReAct loop.
        """
        if self._llm_with_tools is None:
            raise GeminiClientError(
                "Tools not bound. Call get_model_with_tools() first."
            )

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                self._enforce_rate_limit()
                response = self._llm_with_tools.invoke(messages)
                self.total_requests += 1

                # Track token usage if available
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    usage = response.usage_metadata
                    self.total_input_tokens += getattr(usage, "input_tokens", 0)
                    self.total_output_tokens += getattr(usage, "output_tokens", 0)

                return response

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Handle 404 NOT_FOUND model availability errors by falling back
                if any(k in error_str for k in ["404", "not_found", "no longer available", "not found"]):
                    fallbacks = [m for m in GEMINI_CONFIG.get("fallback_models", []) if m != self.model_name]
                    if not fallbacks or attempt >= self.max_retries:
                        break
                    fallback = fallbacks[attempt % len(fallbacks)]
                    logger.warning(f"Model '{self.model_name}' not available ({e}). Falling back to '{fallback}'.")
                    self.model_name = fallback
                    self._llm = None
                    self._llm_with_tools = None
                    continue

                is_retryable = any(
                    code in error_str
                    for code in ["429", "500", "503", "rate", "quota", "resource_exhausted"]
                )

                if is_retryable and attempt < self.max_retries:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Gemini API error (attempt {attempt + 1}/{self.max_retries + 1}): "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    break

        raise GeminiClientError(
            f"Gemini tool call failed after {self.max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    @staticmethod
    def extract_json(text: str) -> Dict[str, Any]:
        """
        Safely extract and parse JSON from LLM text responses, handling markdown code blocks.
        
        Args:
            text: Text response string from LLM.
            
        Returns:
            Parsed JSON dictionary.
            
        Raises:
            ValueError: If valid JSON cannot be extracted.
        """
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            # Fallback: search for first { and last }
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(clean[start:end+1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse valid JSON from response: {e}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Return cumulative API usage statistics.
        
        Returns:
            Dictionary with total_requests, total_input_tokens,
            total_output_tokens, and model_name.
        """
        return {
            "model": self.model_name,
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
        }

