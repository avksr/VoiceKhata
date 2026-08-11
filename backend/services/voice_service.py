"""Speech-to-text belongs in the browser for this MVP; this module is an extension point for Whisper."""

def speech_to_text_provider_status() -> str:
    return "Browser Web Speech API"
