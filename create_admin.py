from database import init_db, create_user
from dotenv import load_dotenv
load_dotenv()
init_db()
try:
    create_user("oded", "12345", is_admin=True)
    print("Admin created: oded / 12345")
except Exception as e:
    print(f"Note: {e}")
