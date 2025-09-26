import json
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'your_super_secret_key' 
DATABASE_FILE = 'database.json'

# --- Data Helper Functions ---
def load_data():
    if not os.path.exists(DATABASE_FILE):
        return {'users': [], 'items': [], 'comments': []}
    with open(DATABASE_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# REMOVED: The hash_password function is no longer needed.

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = load_data()
        form_type = request.form.get('form_type')
        email = request.form['email']
        password = request.form['password']

        if form_type == 'login':
            user_found = None
            for user in data['users']:
                # CHANGED: Direct password comparison instead of hash comparison.
                if user['email'] == email and user['password'] == password:
                    user_found = user
                    break
            
            if user_found:
                session['email'] = user_found['email']
                session['role'] = user_found['role']
                if user_found['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid credentials.")

        elif form_type == 'register':
            if any(user['email'] == email for user in data['users']):
                return render_template('login.html', error="User already exists.")
            
            new_user = {
                'email': email,
                # CHANGED: Saving plain text password instead of a hash.
                'password': password, 
                'role': 'user'
            }
            data['users'].append(new_user)
            save_data(data)
            return redirect(url_for('login'))

    return render_template('login.html')

# --- All other routes remain the same ---

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    data = load_data()
    return render_template('dashboard.html', items=data['items'])

@app.route('/report', methods=['POST'])
def report_item():
    if 'email' not in session:
        return redirect(url_for('login'))
    data = load_data()
    is_electrical = 'isElectrical' in request.form
    new_item = {
        'id': len(data['items']) + 1, 'itemName': request.form['itemName'],
        'location': request.form['location'], 'identityMarks': request.form['identityMarks'],
        'contactNumber': request.form['contactNumber'], 'personalDetails': request.form['personalDetails'],
        'lostPlace': request.form['lostPlace'], 'isElectrical': is_electrical,
        'trackingId': f"TRK-{uuid.uuid4().hex[:8].upper()}" if is_electrical else None,
        'status': 'not_found', 'reportedBy': session['email'], 'currentLocation': None
    }
    data['items'].append(new_item)
    save_data(data)
    return redirect(url_for('dashboard'))

@app.route('/item/<int:item_id>', methods=['GET', 'POST'])
def item_details(item_id):
    if 'email' not in session:
        return redirect(url_for('login'))
    data = load_data()
    item = next((item for item in data['items'] if item['id'] == item_id), None)
    if not item: return "Item not found", 404
    if request.method == 'POST':
        new_comment = {
            'itemId': item_id, 'commentText': request.form['comment'],
            'commenterEmail': session['email']
        }
        data['comments'].append(new_comment)
        save_data(data)
        return redirect(url_for('item_details', item_id=item_id))
    item_comments = [c for c in data['comments'] if c['itemId'] == item_id]
    user_role = session.get('role', 'user')
    return render_template('item_details.html', item=item, comments=item_comments, user_role=user_role)

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': return redirect(url_for('login'))
    data = load_data()
    return render_template('admin.html', items=data['items'])

@app.route('/admin/update_status/<int:item_id>', methods=['POST'])
def update_status(item_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    data = load_data()
    item = next((item for item in data['items'] if item['id'] == item_id), None)
    if item:
        item['status'] = 'found' if item['status'] == 'not_found' else 'not_found'
        save_data(data)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_location/<int:item_id>', methods=['POST'])
def update_location(item_id):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    data = load_data()
    item = next((item for item in data['items'] if item['id'] == item_id), None)
    if item:
        try:
            item['currentLocation'] = {'lat': float(request.form['latitude']), 'lng': float(request.form['longitude'])}
            save_data(data)
        except (ValueError, TypeError): pass 
    return redirect(url_for('item_details', item_id=item_id))

@app.route('/get_item_location/<int:item_id>')
def get_item_location(item_id):
    if 'email' not in session: return jsonify({'error': 'Unauthorized'}), 401
    data = load_data()
    item = next((item for item in data['items'] if item['id'] == item_id), None)
    return jsonify(item.get('currentLocation'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)