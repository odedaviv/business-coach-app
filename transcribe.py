from openai import OpenAI
import anthropic
import os

_openai = None
_claude = None


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
    with open(audio_path, 'rb') as f:
        result = get_openai().audio.transcriptions.create(
            model='whisper-1',
            file=f,
            language='he'
        )
    return result.text


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
