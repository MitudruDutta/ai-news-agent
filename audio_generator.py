# file: audio_generator.py
from gtts import gTTS
import os


def generate_audio_briefing(text, filename="ai_news_briefing.mp3", language='en'):
    """
    Converts the news briefing text into an audio file (MP3).

    Args:
        text (str): The text content of the briefing.
        filename (str): The name of the output MP3 file.
        language (str): The language code for the speech (e.g., 'en' for English).

    Returns:
        str: The path to the generated audio file, or None if generation fails.
    """
    try:
        # Create a gTTS object
        tts = gTTS(text=text, lang=language, slow=False)

        # Save the audio file
        tts.save(filename)

        # Get the absolute path of the file
        file_path = os.path.abspath(filename)
        print(f"Audio briefing successfully generated and saved to {file_path}")
        return file_path
    except Exception as e:
        print(f"An error occurred during audio generation: {e}")
        return None


if __name__ == '__main__':
    # Example usage:
    test_content = (
        "Hello. Here is your daily summary of the top AI news. "
        "First, OpenAI has announced a new model. "
        "Second, Google DeepMind has achieved a breakthrough in robotics."
    )

    audio_file = generate_audio_briefing(test_content)

    if audio_file:
        # On Windows
        if os.name == 'nt':
            os.system(f'start {audio_file}')
        # On macOS
        elif os.name == 'posix':
            os.system(f'open {audio_file}')