"""Subtitle generation (SRT and VTT formats)."""
import logging
from typing import List, Optional
from datetime import timedelta

logger = logging.getLogger(__name__)


def seconds_to_timestamp(seconds: float, format: str = "srt") -> str:
    """
    Convert seconds to timestamp.

    Args:
        seconds: Time in seconds (e.g., 3.5)
        format: "srt" (00:00:03,500) or "vtt" (00:00:03.500)

    Returns:
        Formatted timestamp
    """
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = int(td.total_seconds() % 60)
    millis = int((td.total_seconds() % 1) * 1000)

    sep = "," if format == "srt" else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def generate_srt(
    narration_lines: List[dict],
    output_path: str,
) -> tuple[str, int]:
    """
    Generate SRT subtitle file.

    Args:
        narration_lines: List of dicts with line_number, text, start_time, end_time
        output_path: Path to save .srt file

    Returns:
        (output_path, num_subtitles)
    """
    srt_content = []

    for idx, line in enumerate(narration_lines, 1):
        start_ts = seconds_to_timestamp(line["start_time"], format="srt")
        end_ts = seconds_to_timestamp(line["end_time"], format="srt")

        srt_content.append(f"{idx}\n{start_ts} --> {end_ts}\n{line['text']}\n")

    srt_text = "\n".join(srt_content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_text)

    logger.info(f"✓ Generated SRT: {len(narration_lines)} subtitles to {output_path}")
    return output_path, len(narration_lines)


def generate_vtt(
    narration_lines: List[dict],
    output_path: str,
) -> tuple[str, int]:
    """
    Generate VTT (WebVTT) subtitle file.

    Args:
        narration_lines: List of dicts with line_number, text, start_time, end_time
        output_path: Path to save .vtt file

    Returns:
        (output_path, num_subtitles)
    """
    vtt_content = ["WEBVTT\n"]

    for line in narration_lines:
        start_ts = seconds_to_timestamp(line["start_time"], format="vtt")
        end_ts = seconds_to_timestamp(line["end_time"], format="vtt")

        vtt_content.append(f"{start_ts} --> {end_ts}\n{line['text']}\n")

    vtt_text = "\n".join(vtt_content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(vtt_text)

    logger.info(f"✓ Generated VTT: {len(narration_lines)} subtitles to {output_path}")
    return output_path, len(narration_lines)
