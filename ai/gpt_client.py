"""OpenAI GPT client for AI planning."""
import logging
import json
from typing import Optional, Dict, Any

from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class GPTClient:
    """Client for OpenAI GPT API (planning + analysis)."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def call_gpt(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Call GPT with system + user prompts.

        Args:
            system_prompt: System context
            user_prompt: User query
            response_format: "json_object" or None for text
            temperature: Creativity (0.0-1.0)

        Returns:
            {"text": response_text, "tokens": usage_dict}
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }

            if response_format == "json_object":
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)

            text = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            logger.info(f"GPT call: {usage['total_tokens']} tokens")
            return {"text": text, "tokens": usage}

        except Exception as e:
            logger.error(f"GPT API error: {e}")
            raise

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """
        Parse JSON from GPT response (handles markdown code blocks).

        Args:
            text: GPT response text

        Returns:
            Parsed JSON dict
        """
        # Try direct parsing first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        if "```json" in text:
            start = text.find("```json") + len("```json")
            end = text.find("```", start)
            if end > start:
                json_str = text[start:end].strip()
                return json.loads(json_str)

        # Try extracting from regular code block
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                json_str = text[start:end].strip()
                return json.loads(json_str)

        raise ValueError("Could not parse JSON from GPT response")


# Singleton instance
gpt_client = GPTClient()
