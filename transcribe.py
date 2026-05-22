from openai import OpenAI
import anthropic
import os
import math
import tempfile

_openai = None
_claude = None

MAX_BYTES = 24 * 1024 * 1024  # 24MB — under Whisper's 25MB limit
CHUNK_MINUTES = 20             # split into 20-minute chunks


def get_openai():
    global _openai
    if _openai is None:
        _openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    return _openai


def get_claude():
    global _claude
    if _claude is None:
        _claude = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    return _claude


def transcribe_audio(audio_path):
    """Transcribe audio — splits automatically if file > 24MB."""
    if os.path.getsize(audio_path) <= MAX_BYTES:
        return _transcribe_file(audio_path)
    return _transcribe_chunked(audio_path)


def _transcribe_file(path):
    with open(path, 'rb') as f:
        result = get_openai().audio.transcriptions.create(
            model='whisper-1', file=f, language='he'
        )
    return result.text


def _transcribe_chunked(audio_path):
    """Split into chunks and transcribe each one."""
    try:
        from pydub import AudioSegment
    except ImportError:
        return _transcribe_file(audio_path)  # fallback

    ext = audio_path.rsplit('.', 1)[-1].lower()
    audio = AudioSegment.from_file(audio_path, format=ext)

    chunk_ms = CHUNK_MINUTES * 60 * 1000
    n_chunks = math.ceil(len(audio) / chunk_ms)
    texts = []

    for i in range(n_chunks):
        chunk = audio[i * chunk_ms: (i + 1) * chunk_ms]
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            chunk.export(tmp.name, format='mp3')
            texts.append(_transcribe_file(tmp.name))
            os.unlink(tmp.name)

    return ' '.join(texts)


def summarize_meeting(client_name, transcript):
    prompt = f"""אתה יועץ עסקי מקצועי. קיבלת תמלול של פגישת ייעוץ עם {client_name}.

תמלול הפגישה:
{transcript}

צור סיכום פגישה מקצועי ומסודר בעברית הכולל:

**נושאי הפגישה**
- רשימת הנושאים המרכזיים שנדונו

**החלטות והסכמות**
- מה הוחלט בפגישה

**משימות ומחויבויות**
- מה על הלקוח לעשות עד הפגישה הבאה
- מה על היועץ לעשות

**נקודות מעקב**
- נושאים לבדיקה בפגישה הבאה"""

    response = get_claude().messages.create(
        model='claude-opus-4-5',
        max_tokens=1500,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response.content[0].text


def generate_meeting_title(transcript):
    prompt = f"""בהתבסס על תחילת התמלול הבא, צור כותרת קצרה לפגישה (עד 6 מילים בעברית):

{transcript[:500]}

החזר רק את הכותרת, ללא הסברים."""

    response = get_claude().messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=50,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return response.content[0].text.strip()
