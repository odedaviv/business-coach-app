from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from sheets import read_client_progress
from claude_ai import generate_coaching
from database import (init_db, create_user, verify_user, get_user, get_all_clients,
                      get_meetings, get_meeting, save_meeting, update_sheets_id,
                      update_password, save_coaching_note, get_coaching_notes)
from transcribe import transcribe_audio, summarize_meeting, generate_meeting_title
from contacts import read_contacts, save_contact, whatsapp_link, send_email
from messaging import generate_whatsapp_message, generate_email_report
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import functools
from datetime import datetime

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), override=True)
init_db()

# Auto-create admin from env vars (for Railway)
_admin_name = os.getenv('ADMIN_NAME', '')
_admin_pass = os.getenv('ADMIN_PASSWORD', '')
if _admin_name and _admin_pass:
    try:
        create_user(_admin_name, _admin_pass, is_admin=True)
    except Exception:
        pass

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_AUDIO = {'mp3', 'mp4', 'wav', 'm4a', 'webm', 'ogg', 'mpeg'}


def allowed_audio(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO


# ---------- Auth ----------

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session or not session['user'].get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        user = verify_user(name, password)
        if user:
            session['user'] = user
            return redirect(url_for('index') if user['is_admin'] else url_for('portal'))
        return render_template('login.html', error='שם משתמש או סיסמה שגויים')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


# ---------- Admin routes ----------

@app.route('/')
@admin_required
def index():
    clients = get_all_clients()
    return render_template('index.html', clients=clients)


@app.route('/client/<client_name>')
@admin_required
def client(client_name):
    user = get_user(client_name)
    sheets_id = user.get('sheets_id', '') if user else ''
    progress = []
    sheets_error = None
    if sheets_id:
        try:
            progress = read_client_progress(sheets_id)
        except Exception as e:
            sheets_error = str(e)
    meetings = get_meetings(client_name)
    notes = get_coaching_notes(client_name, limit=5)
    return render_template('client.html', client_name=client_name,
                           progress=progress, sheets_id=sheets_id,
                           sheets_error=sheets_error, meetings=meetings, notes=notes)


@app.route('/client/<client_name>/new_meeting')
@admin_required
def new_meeting_page(client_name):
    return render_template('new_meeting.html', client_name=client_name)


@app.route('/meeting/<int:meeting_id>')
@login_required
def meeting_detail(meeting_id):
    meeting = get_meeting(meeting_id)
    if not meeting:
        return 'פגישה לא נמצאה', 404
    user = session['user']
    if not user['is_admin'] and user['name'] != meeting['client_name']:
        return 'אין הרשאה', 403
    return render_template('meeting_detail.html', meeting=meeting)


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# ---------- Client portal ----------

@app.route('/portal')
@login_required
def portal():
    if session['user']['is_admin']:
        return redirect(url_for('index'))
    client_name = session['user']['name']
    user = get_user(client_name)
    sheets_id = user.get('sheets_id', '') if user else ''
    progress = []
    sheets_error = None
    if sheets_id:
        try:
            progress = read_client_progress(sheets_id)
        except Exception as e:
            sheets_error = str(e)
    meetings = get_meetings(client_name)
    notes = get_coaching_notes(client_name, limit=10)
    return render_template('portal.html', client_name=client_name,
                           progress=progress, sheets_error=sheets_error,
                           meetings=meetings, notes=notes)


# ---------- API ----------

@app.route('/api/add_client', methods=['POST'])
@admin_required
def add_client():
    data = request.json
    name = data['name'].strip()
    password = data.get('password', '').strip() or (name + '123')
    sheets_id = data.get('sheets_id', '').strip()
    try:
        create_user(name, password, is_admin=False, sheets_id=sheets_id)
    except Exception:
        return jsonify({'error': 'לקוח כבר קיים'}), 400
    return jsonify({'success': True, 'default_password': password})


@app.route('/api/set_sheets_id', methods=['POST'])
@admin_required
def set_sheets_id():
    data = request.json
    update_sheets_id(data['client'], data['sheets_id'])
    return jsonify({'success': True})


@app.route('/api/generate', methods=['POST'])
@login_required
def generate():
    data = request.json
    # Determine which client
    if session['user']['is_admin']:
        client_name = data.get('client', '')
    else:
        client_name = session['user']['name']

    user = get_user(client_name)
    sheets_id = user.get('sheets_id', '') if user else ''
    if not sheets_id:
        return jsonify({'error': 'לא מחובר לגוגל שיטס'}), 400

    try:
        progress = read_client_progress(sheets_id)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    client_note = data.get('note', '')
    result = generate_coaching(client_name, progress, client_note)
    save_coaching_note(client_name, client_note, result['remaining'], result['motivation'])
    return jsonify(result)


@app.route('/api/upload_meeting', methods=['POST'])
@admin_required
def upload_meeting():
    client_name = request.form.get('client', '').strip()
    audio_file = request.files.get('audio')
    if not audio_file or not client_name:
        return jsonify({'error': 'חסר קובץ או שם לקוח'}), 400
    if not allowed_audio(audio_file.filename):
        return jsonify({'error': 'פורמט קובץ לא נתמך'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = audio_file.filename.rsplit('.', 1)[-1].lower() if '.' in audio_file.filename else 'webm'
    filename = secure_filename(f"{client_name}_{timestamp}.{ext}")
    audio_path = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(audio_path)

    try:
        transcript = transcribe_audio(audio_path)
        summary = summarize_meeting(client_name, transcript)
        title = generate_meeting_title(transcript)
    except Exception as e:
        os.remove(audio_path)
        return jsonify({'error': f'שגיאה בעיבוד: {str(e)}'}), 500

    meeting_id = save_meeting(client_name, datetime.now().strftime('%Y-%m-%d'),
                              title, filename, transcript, summary)
    return jsonify({'meeting_id': meeting_id, 'title': title,
                    'transcript': transcript, 'summary': summary})


@app.route('/api/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    user = session['user']
    target = data.get('name', user['name'])
    if not user['is_admin'] and target != user['name']:
        return jsonify({'error': 'אין הרשאה'}), 403
    update_password(target, data['password'])
    return jsonify({'success': True})


@app.route('/contacts')
@admin_required
def contacts():
    contacts_sheets_id = os.getenv('CONTACTS_SHEETS_ID', '')
    contact_list = []
    error = None
    if contacts_sheets_id:
        try:
            contact_list = read_contacts(contacts_sheets_id)
        except Exception as e:
            error = str(e)
    return render_template('contacts.html', contacts=contact_list,
                           sheets_id=contacts_sheets_id, error=error)


@app.route('/api/send_whatsapp_prep', methods=['POST'])
@admin_required
def send_whatsapp_prep():
    """Generate WhatsApp message + link for a specific client."""
    data = request.json
    client_name = data['client_name']
    phone = data['phone']
    # sheets_id can come from contacts sheet directly (column G)
    sheets_id = data.get('sheets_id', '')
    if not sheets_id:
        user = get_user(client_name)
        sheets_id = user.get('sheets_id', '') if user else ''
    progress = []
    if sheets_id:
        try:
            progress = read_client_progress(sheets_id)
        except Exception:
            pass
    message = generate_whatsapp_message(client_name, progress, sheets_id)
    link = whatsapp_link(phone, message)
    return jsonify({'message': message, 'link': link})


@app.route('/api/send_email_report', methods=['POST'])
@admin_required
def send_email_report():
    """Generate and send email report to a client."""
    data = request.json
    client_name = data['client_name']
    email = data['email']
    sheets_id = data.get('sheets_id', '')
    if not sheets_id:
        user = get_user(client_name)
        sheets_id = user.get('sheets_id', '') if user else ''
    if not sheets_id:
        return jsonify({'error': 'לא מוגדר Google Sheets ללקוח — הוסף ID בעמודה G בגיליון'}), 400
    try:
        progress = read_client_progress(sheets_id)
        subject, html = generate_email_report(client_name, progress, sheets_id)
        if not subject:
            return jsonify({'error': 'אין נתונים לשליחה'}), 400
        send_email(email, subject, html)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save_contact', methods=['POST'])
@admin_required
def api_save_contact():
    data = request.json
    sheets_id = os.getenv('CONTACTS_SHEETS_ID', '')
    if not sheets_id:
        return jsonify({'error': 'CONTACTS_SHEETS_ID לא מוגדר'}), 400
    try:
        save_contact(sheets_id, data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update_contact', methods=['POST'])
@admin_required
def api_update_contact():
    data = request.json
    sheets_id = os.getenv('CONTACTS_SHEETS_ID', '')
    if not sheets_id:
        return jsonify({'error': 'CONTACTS_SHEETS_ID לא מוגדר'}), 400
    try:
        from contacts import update_contact
        row_index = data.get('row_index', 2)
        update_contact(sheets_id, row_index, {
            'name': data.get('name', ''),
            'phone': data.get('phone', ''),
            'email': data.get('email', ''),
            'meeting_day': data.get('meeting_day', ''),
            'meeting_time': data.get('meeting_time', ''),
            'notes': data.get('notes', ''),
            'sheets_id': data.get('sheets_id', ''),
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(debug=debug, port=port, host='0.0.0.0')
