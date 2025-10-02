# file: audio_generator.py
"""
Enhanced Audio Briefing Generator
Supports multiple TTS engines, voice options, and audio formats
"""

import os
from pathlib import Path
from typing import Optional, Literal
import re
from datetime import datetime

# ==================== CONFIGURATION ====================

# TTS Engine selection (priority: edge-tts > gtts > pyttsx3)
TTS_ENGINE = os.getenv("TTS_ENGINE", "auto").lower()  # auto, gtts, edge, pyttsx3, elevenlabs

# Voice settings
VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE", "en")
VOICE_GENDER = os.getenv("VOICE_GENDER", "female")  # male, female
SPEECH_RATE = float(os.getenv("SPEECH_RATE", "1.0"))  # 0.5 to 2.0
AUDIO_FORMAT = os.getenv("AUDIO_FORMAT", "mp3")  # mp3, wav

# Output directory
OUTPUT_DIR = Path(os.getenv("AUDIO_OUTPUT_DIR", "."))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ElevenLabs API (premium TTS)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice


# ==================== TEXT PREPROCESSING ====================

def preprocess_text_for_speech(text: str) -> str:
    """
    Clean and prepare text for text-to-speech conversion.

    Args:
        text: Raw markdown/text content

    Returns:
        Cleaned text suitable for TTS
    """

    # Remove markdown headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove markdown links but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    # Remove markdown bold/italic
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)

    # Remove markdown code blocks
    text = re.sub(r'```[^\n]*\n.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Remove URLs
    text = re.sub(r'https?://[^\s]+', '', text)

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove bullet points and numbering
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Remove extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    # Add pauses for better narration
    text = text.replace('\n\n', '. ')
    text = text.replace(':', ', ')

    # Clean up
    text = text.strip()

    return text


# ==================== TTS ENGINE: GTTS ====================

def generate_with_gtts(text: str, output_path: str) -> Optional[str]:
    """
    Generate audio using Google Text-to-Speech (gTTS).
    Free, reliable, but limited voice options.
    """
    try:
        from gtts import gTTS

        print("🔊 Using gTTS (Google Text-to-Speech)")

        # Determine language and slow speed
        lang = VOICE_LANGUAGE
        slow = SPEECH_RATE < 0.9

        # Create TTS object
        tts = gTTS(text=text, lang=lang, slow=slow)

        # Save to file
        tts.save(output_path)

        print(f"✅ Audio saved: {output_path}")
        return output_path

    except ImportError:
        print("❌ gTTS not installed. Install with: pip install gtts")
        return None
    except Exception as e:
        print(f"❌ gTTS error: {e}")
        return None


# ==================== TTS ENGINE: EDGE-TTS ====================

def generate_with_edge_tts(text: str, output_path: str) -> Optional[str]:
    """
    Generate audio using Microsoft Edge TTS.
    Free, high-quality voices, many options.
    """
    try:
        import edge_tts
        import asyncio

        print("🔊 Using Edge TTS (Microsoft)")

        # Voice selection based on language and gender
        voice_map = {
            'en-female': 'en-US-AriaNeural',
            'en-male': 'en-US-GuyNeural',
            'es-female': 'es-ES-ElviraNeural',
            'es-male': 'es-ES-AlvaroNeural',
            'fr-female': 'fr-FR-DeniseNeural',
            'fr-male': 'fr-FR-HenriNeural',
            'de-female': 'de-DE-KatjaNeural',
            'de-male': 'de-DE-ConradNeural',
            'it-female': 'it-IT-ElsaNeural',
            'it-male': 'it-IT-DiegoNeural',
            'pt-female': 'pt-BR-FranciscaNeural',
            'pt-male': 'pt-BR-AntonioNeural',
            'ja-female': 'ja-JP-NanamiNeural',
            'ja-male': 'ja-JP-KeitaNeural',
            'zh-female': 'zh-CN-XiaoxiaoNeural',
            'zh-male': 'zh-CN-YunxiNeural',
        }

        voice_key = f"{VOICE_LANGUAGE}-{VOICE_GENDER}"
        voice = voice_map.get(voice_key, 'en-US-AriaNeural')

        # Calculate rate
        rate_percent = int((SPEECH_RATE - 1.0) * 100)
        rate_str = f"{rate_percent:+d}%"

        async def _generate():
            communicate = edge_tts.Communicate(text, voice, rate=rate_str)
            await communicate.save(output_path)

        # Run async function
        asyncio.run(_generate())

        print(f"✅ Audio saved: {output_path}")
        return output_path

    except ImportError:
        print("❌ edge-tts not installed. Install with: pip install edge-tts")
        return None
    except Exception as e:
        print(f"❌ Edge TTS error: {e}")
        return None


# ==================== TTS ENGINE: PYTTSX3 ====================

def generate_with_pyttsx3(text: str, output_path: str) -> Optional[str]:
    """
    Generate audio using pyttsx3 (offline TTS).
    Works offline but lower quality.
    """
    try:
        import pyttsx3

        print("🔊 Using pyttsx3 (Offline TTS)")

        # Initialize engine
        engine = pyttsx3.init()

        # Set properties
        voices = engine.getProperty('voices')

        # Select voice based on gender
        for voice in voices:
            if VOICE_GENDER == 'female' and 'female' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
            elif VOICE_GENDER == 'male' and 'male' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        # Set rate
        rate = engine.getProperty('rate')
        engine.setProperty('rate', rate * SPEECH_RATE)

        # Save to file
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()

        print(f"✅ Audio saved: {output_path}")
        return output_path

    except ImportError:
        print("❌ pyttsx3 not installed. Install with: pip install pyttsx3")
        return None
    except Exception as e:
        print(f"❌ pyttsx3 error: {e}")
        return None


# ==================== TTS ENGINE: ELEVENLABS ====================

def generate_with_elevenlabs(text: str, output_path: str) -> Optional[str]:
    """
    Generate audio using ElevenLabs API (premium, most realistic).
    Requires API key and credits.
    """
    try:
        from elevenlabs import generate, set_api_key, save

        if not ELEVENLABS_API_KEY:
            print("❌ ElevenLabs API key not configured")
            return None

        print("🔊 Using ElevenLabs (Premium TTS)")

        # Set API key
        set_api_key(ELEVENLABS_API_KEY)

        # Generate audio
        audio = generate(
            text=text,
            voice=ELEVENLABS_VOICE_ID,
            model="eleven_monolingual_v1"
        )

        # Save to file
        save(audio, output_path)

        print(f"✅ Audio saved: {output_path}")
        return output_path

    except ImportError:
        print("❌ elevenlabs not installed. Install with: pip install elevenlabs")
        return None
    except Exception as e:
        print(f"❌ ElevenLabs error: {e}")
        return None


# ==================== MAIN FUNCTION ====================

def generate_audio_briefing(
        text: str,
        filename: Optional[str] = None,
        engine: Optional[str] = None
) -> Optional[str]:
    """
    Convert text briefing to audio using the best available TTS engine.

    Args:
        text: The text content to convert to speech
        filename: Optional custom filename (defaults to timestamped)
        engine: Force specific TTS engine (gtts, edge, pyttsx3, elevenlabs)

    Returns:
        Path to generated audio file, or None if generation failed
    """

    print("\n" + "=" * 60)
    print("🎙️  AUDIO BRIEFING GENERATION")
    print("=" * 60)

    # Validate input
    if not text or len(text.strip()) < 10:
        print("❌ Text too short for audio generation")
        return None

    # Preprocess text
    print("📝 Preprocessing text for speech...")
    clean_text = preprocess_text_for_speech(text)

    # Limit length (most TTS engines have limits)
    max_chars = 5000
    if len(clean_text) > max_chars:
        print(f"⚠️  Text truncated from {len(clean_text)} to {max_chars} characters")
        clean_text = clean_text[:max_chars] + "... End of briefing."

    print(f"📊 Text length: {len(clean_text)} characters")

    # Generate filename
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_briefing_{timestamp}.{AUDIO_FORMAT}"

    output_path = OUTPUT_DIR / filename

    # Determine which engine to use
    selected_engine = engine or TTS_ENGINE

    # Try engines in order of preference
    if selected_engine == "auto":
        engines_to_try = ['edge', 'gtts', 'pyttsx3']
        if ELEVENLABS_API_KEY:
            engines_to_try.insert(0, 'elevenlabs')
    else:
        engines_to_try = [selected_engine]

    # Attempt generation with each engine
    for engine_name in engines_to_try:
        print(f"\n🔧 Trying {engine_name.upper()}...")

        result = None

        if engine_name == 'gtts':
            result = generate_with_gtts(clean_text, str(output_path))
        elif engine_name == 'edge':
            result = generate_with_edge_tts(clean_text, str(output_path))
        elif engine_name == 'pyttsx3':
            result = generate_with_pyttsx3(clean_text, str(output_path))
        elif engine_name == 'elevenlabs':
            result = generate_with_elevenlabs(clean_text, str(output_path))

        if result:
            file_size = Path(result).stat().st_size / 1024  # KB
            print(f"\n✅ SUCCESS! Audio file: {result}")
            print(f"📦 File size: {file_size:.1f} KB")
            print("=" * 60 + "\n")
            return result

    # All engines failed
    print("\n❌ All TTS engines failed")
    print("=" * 60 + "\n")
    return None


# ==================== BATCH PROCESSING ====================

def generate_multiple_versions(text: str, output_dir: Optional[Path] = None) -> dict:
    """
    Generate audio in multiple voices/languages for comparison.

    Returns:
        Dictionary of {engine_name: file_path}
    """

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = OUTPUT_DIR

    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    engines = ['gtts', 'edge', 'pyttsx3']
    if ELEVENLABS_API_KEY:
        engines.append('elevenlabs')

    for engine in engines:
        filename = f"briefing_{engine}_{timestamp}.{AUDIO_FORMAT}"
        output_path = output_dir / filename

        print(f"\n📢 Generating with {engine.upper()}...")

        if engine == 'gtts':
            result = generate_with_gtts(preprocess_text_for_speech(text), str(output_path))
        elif engine == 'edge':
            result = generate_with_edge_tts(preprocess_text_for_speech(text), str(output_path))
        elif engine == 'pyttsx3':
            result = generate_with_pyttsx3(preprocess_text_for_speech(text), str(output_path))
        elif engine == 'elevenlabs':
            result = generate_with_elevenlabs(preprocess_text_for_speech(text), str(output_path))

        if result:
            results[engine] = result

    print(f"\n✅ Generated {len(results)} audio versions")
    return results


# ==================== STANDALONE EXECUTION ====================

if __name__ == '__main__':
    # Test audio generation
    test_text = """
    # Daily AI Intelligence Briefing

    Welcome to your daily AI news briefing. Here are the top stories from the world of artificial intelligence.

    ## Story 1: Major Breakthrough in Language Models

    Researchers have announced a significant advancement in large language models, 
    achieving a 40% improvement in reasoning capabilities while reducing computational 
    requirements by 30%. This breakthrough could democratize access to advanced AI systems.

    ## Story 2: New Computer Vision Techniques

    A novel approach to computer vision has been published, showing remarkable results 
    in real-time object detection with 95% accuracy across diverse environments.

    That concludes today's briefing. Stay tuned for tomorrow's updates.
    """

    print("🧪 Testing audio generation...\n")

    # Generate single version
    audio_file = generate_audio_briefing(test_text)

    if audio_file:
        print(f"\n✅ Test successful! Audio file: {audio_file}")
        print("\nTo play the audio:")
        print(f"  - Windows: start {audio_file}")
        print(f"  - macOS: open {audio_file}")
        print(f"  - Linux: xdg-open {audio_file}")
    else:
        print("\n❌ Test failed. Check TTS engine installation.")