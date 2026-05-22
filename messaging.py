"""
Generates motivational messages and sends them via WhatsApp/email.
"""
import anthropic
import os
from datetime import datetime

_client = None


def get_claude():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    return _client


def generate_whatsapp_message(client_name, progress_data, sheets_id=''):
    """Short, warm WhatsApp message with links to portal and Google Sheet."""
    app_url = os.getenv('APP_URL', 'http://localhost:5000')
    portal_link = f"{app_url}/portal"
    sheets_link = f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit" if sheets_id else ''

    if not progress_data:
        msg = f"שלום {client_name}! זמן לעדכן את הנתונים בגיליון ולהמשיך קדימה 💪"
    else:
        total_goal = sum(p['monthly_goal'] for p in progress_data)
        total_done = sum(p['cumulative'] for p in progress_data)
        remaining = max(0, total_goal - total_done)
        pct = round(total_done / total_goal * 100) if total_goal else 0
        days_left = _days_remaining()

        prompt = f"""כתוב הודעת WhatsApp קצרה ואישית (עד 3 משפטים) ליועץ ביטוח/פיננסים בשם {client_name}.

נתונים: עשה {total_done:.0f} מתוך {total_goal:.0f} ({pct}%) | נשאר {remaining:.0f} | {days_left} ימים לסוף החודש

כלל:
- אם {pct} >= 80: הודעת שיא + עידוד לסיים
- אם 50 <= {pct} < 80: הודעת "יאללה בוא נמשיך, נשאר X..."
- אם {pct} < 50: הודעה שמדרבנת "לא נשאר הרבה זמן, אבל אפשר!"

כתוב בעברית, חמה ואישית, עם אמוג'י אחד לכל היותר. אל תתחיל ב"שלום"."""

        response = get_claude().messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        msg = response.content[0].text.strip()

    # Append links
    msg += f"\n\n📊 הפורטל שלך: {portal_link}"
    if sheets_link:
        msg += f"\n📋 גיליון המעקב: {sheets_link}"
    return msg


def generate_email_report(client_name, progress_data, sheets_id=''):
    """Full HTML email with weekly progress report + motivation + links."""
    if not progress_data:
        return None, None

    total_goal = sum(p['monthly_goal'] for p in progress_data)
    total_done = sum(p['cumulative'] for p in progress_data)
    pct = round(total_done / total_goal * 100) if total_goal else 0
    days_left = _days_remaining()

    rows_html = ''
    for item in progress_data:
        item_pct = round(item['cumulative'] / item['monthly_goal'] * 100) if item['monthly_goal'] else 0
        color = '#16a34a' if item_pct >= 80 else '#d97706' if item_pct >= 50 else '#dc2626'
        bar_width = min(item_pct, 100)
        rows_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;font-weight:500">{item['category']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center">{int(item['monthly_goal'])}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center;color:{color};font-weight:bold">{int(item['cumulative'])}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center">{int(item['remaining'])}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0">
            <div style="background:#e5e7eb;border-radius:4px;height:8px">
              <div style="background:{color};border-radius:4px;height:8px;width:{bar_width}%"></div>
            </div>
            <span style="font-size:11px;color:#6b7280">{item_pct}%</span>
          </td>
        </tr>"""

    # Generate motivation text via Claude
    motivation_prompt = f"""כתוב פסקת מוטיבציה קצרה (3-4 משפטים) לסיכום שבועי ל{client_name}.
עשה {total_done:.0f}/{total_goal:.0f} ({pct}%), נשארו {days_left} ימים בחודש.
כתוב בעברית, אישי, עוצמתי ומעשי."""

    motivation_response = get_claude().messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=300,
        messages=[{'role': 'user', 'content': motivation_prompt}]
    )
    motivation_text = motivation_response.content[0].text.strip()

    app_url = os.getenv('APP_URL', 'http://localhost:5000')
    portal_link = f"{app_url}/portal"
    sheets_link = f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit" if sheets_id else ''

    subject = f"דוח שבועי | {client_name} | {datetime.now().strftime('%d/%m/%Y')}"

    buttons_html = f"""
    <a href="{portal_link}"
       style="display:inline-block;background:#1e40af;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:bold;margin-left:8px">
      הפורטל האישי שלי ←
    </a>"""
    if sheets_link:
        buttons_html += f"""
    <a href="{sheets_link}"
       style="display:inline-block;background:#16a34a;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:bold">
      גיליון המעקב ←
    </a>"""

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<body style="font-family:Arial,sans-serif;background:#f9fafb;margin:0;padding:20px">
<div style="max-width:600px;margin:0 auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
  <div style="background:#1e3a5f;color:white;padding:24px 28px">
    <h1 style="margin:0;font-size:20px">עודד אביב | יועץ עסקי</h1>
    <p style="margin:6px 0 0;opacity:0.8;font-size:14px">דוח שבועי — {datetime.now().strftime('%d/%m/%Y')}</p>
  </div>
  <div style="padding:24px 28px">
    <h2 style="color:#1f2937;font-size:16px;margin:0 0 16px">שלום {client_name},</h2>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <thead>
        <tr style="background:#f3f4f6">
          <th style="padding:10px 12px;text-align:right;color:#374151">תחום</th>
          <th style="padding:10px 12px;text-align:center;color:#374151">יעד</th>
          <th style="padding:10px 12px;text-align:center;color:#374151">בוצע</th>
          <th style="padding:10px 12px;text-align:center;color:#374151">נשאר</th>
          <th style="padding:10px 12px;color:#374151">התקדמות</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <div style="margin:20px 0;padding:16px;background:#eff6ff;border-right:4px solid #1e40af;border-radius:8px">
      <p style="margin:0;color:#1e3a5f;line-height:1.7">{motivation_text}</p>
    </div>
    <div style="margin:20px 0">{buttons_html}</div>
    <p style="color:#9ca3af;font-size:12px;margin:16px 0 0">
      נשארו <strong style="color:#1f2937">{days_left} ימים</strong> בחודש | {pct}% הושגו
    </p>
  </div>
</div>
</body>
</html>"""

    return subject, html


def _days_remaining():
    now = datetime.now()
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime(now.year, now.month + 1, 1)
    return (next_month - now).days
