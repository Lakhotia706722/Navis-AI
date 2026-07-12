"""Tests for voice synthesis and subtitle generation."""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from ai.voice_engine import VoiceEngine, VoicePlan
from ai.subtitle_generator import generate_srt, generate_vtt, seconds_to_timestamp
from ai.schemas import ScriptLine


class TestVoiceEngine:
    """Voice synthesis tests."""

    @patch("ai.voice_engine.OpenAI")
    def test_synthesize_speech_success(self, mock_openai):
        """Test successful speech synthesis."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Mock the response
        mock_response = MagicMock()
        mock_response.content = b"fake mp3 data"
        mock_client.audio.speech.create.return_value = mock_response

        # Test
        engine = VoiceEngine()
        engine.client = mock_client

        output_path = "/tmp/test.mp3"
        result_path, char_count = engine.synthesize_speech("Hello world", output_path)

        assert result_path == output_path
        assert char_count == 11  # "Hello world"
        mock_client.audio.speech.create.assert_called_once()

    def test_voice_plan_creation(self):
        """Test voice plan creation."""
        lines = [
            ScriptLine(line_number=1, type="narration", text="Welcome", duration_seconds=2.0),
            ScriptLine(line_number=2, type="action", text="Scene action", duration_seconds=1.0),
            ScriptLine(line_number=3, type="narration", text="Continue", duration_seconds=3.0),
        ]

        voice_plan = VoicePlan(lines, target_duration=6.0)

        assert len(voice_plan.narration_lines) == 2
        assert voice_plan.get_narration_text() == "Welcome Continue"

    def test_voice_plan_timing_map(self):
        """Test voice plan timing map."""
        lines = [
            ScriptLine(line_number=1, type="narration", text="First", duration_seconds=2.0),
            ScriptLine(line_number=2, type="narration", text="Second", duration_seconds=3.0),
        ]

        voice_plan = VoicePlan(lines, target_duration=5.0)
        timing = voice_plan.get_timing_map()

        assert len(timing["narration_lines"]) == 2
        assert timing["narration_lines"][0]["start_time"] == 0.0
        assert timing["narration_lines"][0]["end_time"] == 2.0
        assert timing["narration_lines"][1]["start_time"] == 2.0
        assert timing["narration_lines"][1]["end_time"] == 5.0
        assert timing["total_narration_chars"] == 11  # "First Second"


class TestSubtitleGenerator:
    """Subtitle generation tests."""

    def test_seconds_to_timestamp_srt(self):
        """Test SRT timestamp format."""
        assert seconds_to_timestamp(3.5, format="srt") == "00:00:03,500"
        assert seconds_to_timestamp(65.250, format="srt") == "00:01:05,250"
        assert seconds_to_timestamp(3665.100, format="srt") == "01:01:05,100"

    def test_seconds_to_timestamp_vtt(self):
        """Test VTT timestamp format."""
        assert seconds_to_timestamp(3.5, format="vtt") == "00:00:03.500"
        assert seconds_to_timestamp(65.250, format="vtt") == "00:01:05.250"
        assert seconds_to_timestamp(3665.100, format="vtt") == "01:01:05.100"

    def test_generate_srt(self, tmp_path):
        """Test SRT generation."""
        narration_lines = [
            {"line_number": 1, "text": "First line", "start_time": 0.0, "end_time": 2.5},
            {"line_number": 2, "text": "Second line", "start_time": 2.5, "end_time": 5.0},
        ]

        output_path = tmp_path / "test.srt"
        result_path, count = generate_srt(narration_lines, str(output_path))

        assert count == 2
        assert output_path.exists()

        content = output_path.read_text()
        assert "1\n00:00:00,000 --> 00:00:02,500\nFirst line" in content
        assert "2\n00:00:02,500 --> 00:00:05,000\nSecond line" in content

    def test_generate_vtt(self, tmp_path):
        """Test VTT generation."""
        narration_lines = [
            {"line_number": 1, "text": "First line", "start_time": 0.0, "end_time": 2.5},
        ]

        output_path = tmp_path / "test.vtt"
        result_path, count = generate_vtt(narration_lines, str(output_path))

        assert count == 1
        assert output_path.exists()

        content = output_path.read_text()
        assert "WEBVTT" in content
        assert "00:00:00.000 --> 00:00:02.500\nFirst line" in content

    def test_generate_srt_multiline_subtitles(self, tmp_path):
        """Test SRT with multiple subtitles."""
        narration_lines = [
            {"line_number": i, "text": f"Line {i}", "start_time": i * 2.0, "end_time": (i + 1) * 2.0}
            for i in range(1, 6)
        ]

        output_path = tmp_path / "test.srt"
        result_path, count = generate_srt(narration_lines, str(output_path))

        assert count == 5

        content = output_path.read_text()
        lines = content.split("\n\n")
        assert len([l for l in lines if l.strip()]) == 5  # 5 subtitle blocks


class TestSubtitleTimingEdgeCases:
    """Edge case tests for timing."""

    def test_seconds_to_timestamp_zero(self):
        """Test timestamp at zero."""
        assert seconds_to_timestamp(0.0, format="srt") == "00:00:00,000"

    def test_seconds_to_timestamp_fractional(self):
        """Test fractional seconds."""
        assert seconds_to_timestamp(0.001, format="srt") == "00:00:00,001"
        assert seconds_to_timestamp(0.999, format="srt") == "00:00:00,999"

    def test_seconds_to_timestamp_large_duration(self):
        """Test large duration (multi-hour video)."""
        # 2 hours, 30 minutes, 45.5 seconds
        result = seconds_to_timestamp(9045.5, format="vtt")
        assert result == "02:30:45.500"
