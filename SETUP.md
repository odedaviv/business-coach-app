# הגדרת האפליקציה

## צעד 1 — Python
ודא ש-Python 3.10+ מותקן. פתח Terminal בתיקייה זו:
```
pip install -r requirements.txt
```

## צעד 2 — Google Sheets API

1. כנס ל-[Google Cloud Console](https://console.cloud.google.com/)
2. צור פרויקט חדש
3. הפעל את **Google Sheets API** + **Google Drive API**
4. צור **Service Account** (IAM & Admin → Service Accounts)
5. הורד את קובץ ה-JSON ושמור אותו כ-`credentials.json` בתיקייה זו
6. צור Google Spreadsheet חדש עם לקוחות
7. שתף את ה-Spreadsheet עם כתובת האימייל של ה-Service Account (Editor)
8. העתק את ה-ID של ה-Spreadsheet מה-URL

## צעד 3 — קובץ הגדרות

העתק `.env.example` לקובץ `.env` ומלא:
```
ANTHROPIC_API_KEY=...     (מ-console.anthropic.com)
OPENAI_API_KEY=...         (מ-platform.openai.com - לתמלול)
GOOGLE_SHEETS_ID=...       (ID מה-URL של הגיליון)
GOOGLE_CREDENTIALS_FILE=credentials.json
SECRET_KEY=מחרוזת-אקראית-ארוכה
```

## צעד 4 — יצירת חשבון מנהל

```
python setup_admin.py
```

## צעד 5 — הפעלה

```
python app.py
```

פתח בדפדפן: http://localhost:5000

---

## מבנה האפליקציה

| URL | תיאור |
|-----|--------|
| `/` | לוח הבקרה שלך (דורש כניסה כמנהל) |
| `/client/<שם>` | עדכון יומי + פגישות של לקוח |
| `/client/<שם>/new_meeting` | הקלטת/העלאת פגישה חדשה |
| `/meeting/<id>` | צפייה בפגישה + תמלול |
| `/portal` | הפורטל האישי של הלקוח |
| `/login` | כניסה |

## הוספת לקוח חדש

מלוח הבקרה — הזן שם לקוח וסיסמה. האפליקציה:
- מוסיפה טאב ב-Google Sheets
- יוצרת חשבון לקוח לפורטל האישי

## מבנה Google Sheets

כל לקוח מקבל טאב עם העמודות:
`חודש | יעד חודשי | תאריך עדכון | מה עשית החודש | מה עשית השבוע | מה עשית היום | מה נשאר | מסר מוטיבציוני`
