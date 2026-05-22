from gauth import get_gc as _get_gc


def read_client_progress(sheets_id):
    """
    Read progress from a client's Google Sheet by spreadsheet ID.
    Expected structure:
      Row 1: headers (מוצר/תחום, לידים, יעד חודשי, שבוע 1-5, סה"כ, %, יעד שנתי, יעד חודשי ממוצע)
      Row 2+: data rows (one per category)
    Returns list of dicts.
    """
    if not sheets_id:
        raise RuntimeError('לא הוגדר Google Sheets ID ללקוח זה')

    gc = _get_gc()

    # Support 'SPREADSHEET_ID:GID' format for specific tab
    if ':' in sheets_id:
        spreadsheet_id, gid = sheets_id.split(':', 1)
        spreadsheet = gc.open_by_key(spreadsheet_id)
        ws = next((s for s in spreadsheet.worksheets() if str(s.id) == gid),
                  spreadsheet.sheet1)
    else:
        ws = gc.open_by_key(sheets_id).sheet1

    rows = ws.get_all_values()

    if len(rows) < 2:
        return []

    results = []
    for row in rows[1:]:
        category = row[0].strip() if row else ''
        if not category:
            continue
        try:
            monthly_goal = _to_num(row[2]) if len(row) > 2 else 0
            week1 = _to_num(row[3]) if len(row) > 3 else 0
            week2 = _to_num(row[4]) if len(row) > 4 else 0
            week3 = _to_num(row[5]) if len(row) > 5 else 0
            week4 = _to_num(row[6]) if len(row) > 6 else 0
            week5 = _to_num(row[7]) if len(row) > 7 else 0
            cumulative = _to_num(row[8]) if len(row) > 8 else 0
            percentage = row[9].strip() if len(row) > 9 else '0%'
        except Exception:
            continue

        if monthly_goal == 0 and cumulative == 0:
            continue

        remaining = max(0, monthly_goal - cumulative)
        results.append({
            'category': category,
            'monthly_goal': monthly_goal,
            'weeks': [week1, week2, week3, week4, week5],
            'cumulative': cumulative,
            'remaining': remaining,
            'percentage': percentage,
        })

    return results


def _to_num(val):
    if val == '' or val is None:
        return 0
    try:
        return float(str(val).replace(',', '').replace('%', '').strip())
    except Exception:
        return 0
