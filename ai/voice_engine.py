"""Text-to-speech (TTS) voice synthesis using OpenAI."""
import logging
from typing import Optional, List
from pathlib import Path

from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class VoiceEngine:
    """OpenAI TTS voice synthesis."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_tts_model  # "tts-1-hd"
        self.voice = settings.openai_tts_voice  # "nova", "echo", "fable", "alloy", "onyx", "shimmer"

    def synthesize_speech(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
    ) -> tuple[str, int]:
        """
        Synthesize speech from text using OpenAI TTS.

        Args:
            text: Text to synthesize (narration/dialogue)
            output_path: Path to save .mp3 file
            voice: Voice name (default: settings.openai_tts_voice)

        Returns:
            (output_path, character_count) — path to saved file, characters used for billing
        """
        voice = voice or self.voice
        char_count = len(text)

        try:
            logger.info(f"Synthesizing speech: {len(text)} chars, voice={voice}")

            response = self.client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
            )

            # Write to file
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"✓ Synthesized {char_count} chars to {output_path}")
            return output_path, char_count

        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise


class VoicePlan:
    """Plan for narration: which lines speak when."""

    def __init__(self, script_lines: List, target_duration: float):
        """
        Initialize voice plan from script lines.

        Args:
            script_lines: List of ScriptLine objects with duration_seconds
            target_duration: Total video duration
        """
        self.script_lines = script_lines
        self.target_duration = target_duration
        self.narration_lines = [line for line in script_lines if line.type == "narration"]

    def get_narration_text(self) -> str:
        """Get all narration concatenated."""
        return " ".join([line.text for line in self.narration_lines])

    def get_timing_map(self) -> dict:
        """
        Get timing info: when each narration line starts/ends.

        Returns:
            {
                "narration_lines": [
                    {
                        "line_number": 1,
                        "text": "Welcome...",
                        "start_time": 0.0,
                        "end_time": 3.0,
                        "duration": 3.0
                    }
                ],
                "total_narration_chars": 500
            }
        """
        timing_map = {
            "narration_lines": [],
            "total_narration_chars": len(self.get_narration_text()),
        }

        cumulative_time = 0.0
        for line in self.narration_lines:
            start_time = cumulative_time
            end_time = start_time + line.duration_seconds

            timing_map["narration_lines"].append(
                {
                    "line_number": line.line_number,
                    "text": line.text,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": line.duration_seconds,
                }
            )

            cumulative_time = end_time

        return timing_map


# Singleton instance
voice_engine = VoiceEngine()
