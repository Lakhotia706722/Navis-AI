"""Composing stage orchestrator: voice synthesis + subtitles."""
import logging
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ai.voice_engine import VoiceEngine, VoicePlan
from ai.subtitle_generator import generate_srt, generate_vtt
from backend.models import Scene, RenderJob, UsageLog
from backend.storage import s3_client
from backend.config import settings

logger = logging.getLogger(__name__)


def run_composing_pipeline(
    render_job: RenderJob,
    script,  # Script object from Phase 3
    db: Session,
) -> tuple[dict, dict]:
    """
    Composing pipeline: TTS synthesis + subtitle generation.

    Args:
        render_job: RenderJob being processed
        script: Script object (from planning phase)
        db: Database session

    Returns:
        (output_dict with audio_path/subtitle_paths, cost_stats)
    """
    cost_stats = {
        "tts_characters": 0,
        "audio_path": None,
        "srt_path": None,
        "vtt_path": None,
    }

    logger.info(f"Starting composing pipeline for render_job {render_job.id}")

    # Step 1: Create voice plan
    logger.info("Step 1: Creating voice plan...")
    voice_plan = VoicePlan(script.lines, script.total_duration_seconds)
    timing_map = voice_plan.get_timing_map()
    narration_text = voice_plan.get_narration_text()
    logger.info(f"✓ Voice plan created: {len(voice_plan.narration_lines)} narration lines, {len(narration_text)} chars")

    # Step 2: Synthesize speech (TTS)
    logger.info("Step 2: Synthesizing speech with OpenAI TTS...")
    voice_engine = VoiceEngine()

    # Temporary local file (will upload to S3)
    local_audio_path = f"/tmp/render-{render_job.id}.mp3"
    try:
        audio_path, char_count = voice_engine.synthesize_speech(narration_text, local_audio_path)
        cost_stats["tts_characters"] = char_count
        logger.info(f"✓ Speech synthesized: {char_count} chars → {audio_path}")
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise

    # Step 3: Upload audio to S3
    logger.info("Step 3: Uploading audio to S3...")
    try:
        s3_key = f"audio/render-{render_job.id}.mp3"
        s3_url = s3_client.upload_file(local_audio_path, s3_key)
        cost_stats["audio_path"] = s3_url
        logger.info(f"✓ Audio uploaded: {s3_url}")

        # Clean up temp file
        if os.path.exists(local_audio_path):
            os.remove(local_audio_path)

    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise

    # Step 4: Generate subtitles (SRT + VTT)
    logger.info("Step 4: Generating subtitles...")
    narration_lines = timing_map["narration_lines"]

    # SRT
    local_srt_path = f"/tmp/render-{render_job.id}.srt"
    try:
        srt_path, srt_count = generate_srt(narration_lines, local_srt_path)

        # Upload to S3
        srt_key = f"subtitles/render-{render_job.id}.srt"
        srt_url = s3_client.upload_file(srt_path, srt_key)
        cost_stats["srt_path"] = srt_url
        logger.info(f"✓ SRT generated: {srt_count} subtitles → {srt_url}")

        if os.path.exists(local_srt_path):
            os.remove(local_srt_path)

    except Exception as e:
        logger.error(f"SRT generation failed: {e}")
        raise

    # VTT
    local_vtt_path = f"/tmp/render-{render_job.id}.vtt"
    try:
        vtt_path, vtt_count = generate_vtt(narration_lines, local_vtt_path)

        # Upload to S3
        vtt_key = f"subtitles/render-{render_job.id}.vtt"
        vtt_url = s3_client.upload_file(vtt_path, vtt_key)
        cost_stats["vtt_path"] = vtt_url
        logger.info(f"✓ VTT generated: {vtt_count} subtitles → {vtt_url}")

        if os.path.exists(local_vtt_path):
            os.remove(local_vtt_path)

    except Exception as e:
        logger.error(f"VTT generation failed: {e}")
        raise

    # Step 5: Log TTS usage
    logger.info("Step 5: Logging TTS character usage...")
    try:
        usage_log = UsageLog(
            project_id=render_job.project_id,
            usage_type="tts_chars",
            quantity=cost_stats["tts_characters"],
            cost_usd=calculate_tts_cost(cost_stats["tts_characters"]),
            metadata={
                "model": settings.openai_tts_model,
                "voice": settings.openai_tts_voice,
                "narration_lines": len(narration_lines),
            },
        )
        db.add(usage_log)
        db.commit()
        logger.info(f"✓ Logged {cost_stats['tts_characters']} TTS characters")
    except Exception as e:
        logger.error(f"Failed to log TTS usage: {e}")
        db.rollback()
        raise

    logger.info("✓ Composing pipeline complete")
    return cost_stats, {"tts_chars": cost_stats["tts_characters"]}


def calculate_tts_cost(characters: int) -> float:
    """
    Calculate estimated cost for TTS characters.

    Using OpenAI TTS pricing (as of July 2024):
    - $0.015 per 1,000 characters

    Args:
        characters: Number of characters synthesized

    Returns:
        Estimated USD cost
    """
    return round(characters * 0.015 / 1000, 4)
