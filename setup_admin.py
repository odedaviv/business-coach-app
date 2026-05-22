"""
Run this once to create your admin account.
Usage: python setup_admin.py
"""
from database import init_db, create_user
from dotenv import load_dotenv

load_dotenv()
init_db()

print("=== הגדרת חשבון מנהל ===")
name = input("שם המנהל (לדוגמה: עודד): ").strip()
password = input("סיסמה: ").strip()

try:
    create_user(name, password, is_admin=True)
    print(f"\n✓ חשבון המנהל '{name}' נוצר בהצלחה!")
    print("כעת תוכל להריץ את האפליקציה: python app.py")
except Exception as e:
    if 'UNIQUE constraint' in str(e):
        print(f"\n⚠ משתמש בשם '{name}' כבר קיים")
    else:
        raise
