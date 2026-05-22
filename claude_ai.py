import anthropic
import json
import re
import os
from datetime import datetime

_client = None


def get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    return _client


def generate_coaching(client_name, progress_data, client_note=''):
    today = datetime.now().strftime('%d/%m/%Y')
    days_remaining = _days_remaining()

    # Format progress table for AI
    lines = []
    total_goal = 0
    total_done = 0
    for item in progress_data:
        total_goal += item['monthly_goal']
        total_done += item['cumulative']
        lines.append(
            f"- {item['category']}: יעד {item['monthly_goal']:.0f} | "
            f"בוצע {item['cumulative']:.0f} | נשאר {item['remaining']:.0f} ({item['percentage']})"
        )

    overall_pct = round(total_done / total_goal * 100) if total_goal else 0
    progress_text = '\n'.join(lines) if lines else 'אין נתונים'

    note_section = f"\nמה הלקוח מספר: {client_note}" if client_note.strip() else ""

    prompt = f"""אתה יועץ עסקי מוטיבציוני עבור {client_name}.

תאריך היום: {today} | נותרו {days_remaining} ימים בחודש

התקדמות חודשית לפי תחום:
{progress_text}

סה"כ: {total_done:.0f} מתוך {total_goal:.0f} ({overall_pct}%){note_section}

השב בעברית בפורמט JSON בלבד:
{{
  "remaining": "ניתוח ספציפי ומעשי של מה נשאר לעשות — איפה הפוקוס צריך להיות בימים הקרובים",
  "motivation": "מסר מוטיבציוני אישי ועוצמתי של 2-3 משפטים בהתאמה לנתונים"
}}"""

    response = get_client().messages.create(
        model='claude-opus-4-5',
        max_tokens=800,
        messages=[{'role': 'user', 'content': prompt}]
    )

    text = response.content[0].text.strip()
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f'Could not parse AI response: {text}')


def _days_remaining():
    now = datetime.now()
    if now.month == 12:
        from datetime import datetime as dt
        next_month = dt(now.year + 1, 1, 1)
    else:
        next_month = datetime(now.year, now.month + 1, 1)
    return (next_month - now).days
