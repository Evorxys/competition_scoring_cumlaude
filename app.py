from flask import Flask, render_template, request, redirect, url_for, session
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Use a strong secret key for session management

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Dummy admin credentials (Replace with secure authentication)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password123'

# Function to load data from JSON
def load_data():
    if os.path.exists('judges.json'):
        with open('judges.json') as f:
            data = json.load(f)
            return data['judges'], data['contestants'], data['criteria'], data.get('scores', {})
    else:
        return [], [], [], {}  # Return empty lists if the file doesn't exist

# Function to save data to JSON
def save_data(judges, contestants, criteria, scores):
    with open('judges.json', 'w') as f:
        json.dump({'judges': judges, 'contestants': contestants, 'criteria': criteria, 'scores': scores}, f)

# Load judges, contestants, criteria, and scores globally at the start
judges, contestants, criteria, scores = load_data()

@app.route('/')
def home():
    return render_template('home.html', contestants=contestants)

@app.route('/judges')
def judges_page():
    return render_template('judges.html', judges=judges)

@app.route('/results')
def results_page():
    # Only allow access if the admin is logged in
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))

    # Calculate total scores for each contestant
    contestant_scores = {c['name']: 0 for c in contestants}
    for judge_scores in scores.values():
        for contestant, score_data in judge_scores.items():
            contestant_scores[contestant] += sum(score_data.values())

    # Sort contestants by total scores
    ranked_contestants = sorted(contestant_scores.items(), key=lambda x: x[1], reverse=True)

    return render_template('results.html', ranked_contestants=ranked_contestants)

@app.route('/judge/<int:judge_id>', methods=['GET', 'POST'])
def judge_scoring(judge_id):
    global judges, contestants, criteria, scores

    if judge_id < 0 or judge_id >= len(judges):
        return "Judge not found!", 404

    judge_name = judges[judge_id]['name']

    if request.method == 'POST':
        # Process submitted scores
        if judge_name not in scores:
            scores[judge_name] = {}

        for contestant in contestants:
            contestant_name = contestant['name']
            if contestant_name not in scores[judge_name]:
                scores[judge_name][contestant_name] = {}

            for criterion in criteria:
                try:
                    score_input = request.form.get(f'{contestant_name}_{criterion["name"]}')
                    score = float(score_input.replace('%', ''))
                    if 0 <= score <= 100:
                        scores[judge_name][contestant_name][criterion['name']] = score
                    else:
                        raise ValueError("Score out of range")
                except ValueError:
                    return f"Invalid score input for {contestant_name} in {criterion['name']}. Please enter a valid percentage (0-100%).", 400

        save_data(judges, contestants, criteria, scores)
        return redirect(url_for('judge_scoring', judge_id=judge_id))

    # Pass judge_id to the template
    return render_template('judge_scoring.html', judge_name=judge_name, contestants=contestants, criteria=criteria, judge_id=judge_id)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Check if the admin is logged in
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return redirect(url_for('admin_login'))

    global judges, contestants, criteria, scores

    if request.method == 'POST':
        if 'clear' in request.form:
            # Clear judges, contestants, and criteria
            judges.clear()
            contestants.clear()
            criteria.clear()
            scores.clear()
            save_data(judges, contestants, criteria, scores)
            return redirect(url_for('admin'))

        # Process judges form
        for i in range(len(request.form.getlist('judgeName[]'))):
            judge_name = request.form.getlist('judgeName[]')[i]
            judge_bio = request.form.getlist('judgeBio[]')[i]
            judge_photo = request.files.getlist('judgePhoto[]')[i]

            if judge_photo and judge_photo.filename != '':
                # Save photo to the uploads directory
                photo_filename = f'judge_{i}_{judge_photo.filename}'
                judge_photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

                # Append judge info to the list (if not already added)
                if not any(j['name'] == judge_name for j in judges):
                    judges.append({
                        'name': judge_name,
                        'bio': judge_bio,
                        'photo': photo_filename
                    })

        # Process contestants form
        for i in range(len(request.form.getlist('contestantName[]'))):
            contestant_name = request.form.getlist('contestantName[]')[i]
            contestant_age = request.form.getlist('contestantAge[]')[i]
            contestant_photo = request.files.getlist('contestantPhoto[]')[i]

            if contestant_photo and contestant_photo.filename != '':
                # Save photo to the uploads directory
                photo_filename = f'contestant_{i}_{contestant_photo.filename}'
                contestant_photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

                # Append contestant info to the list (if not already added)
                if not any(c['name'] == contestant_name for c in contestants):
                    contestants.append({
                        'name': contestant_name,
                        'age': contestant_age,
                        'photo': photo_filename
                    })

        # Process criteria form
        criteria_names = request.form.getlist('criteriaName[]')
        criteria_percentages = request.form.getlist('criteriaPercentage[]')
        criteria.clear()  # Clear old criteria

        for i in range(len(criteria_names)):
            criteria.append({
                'name': criteria_names[i],
                'percentage': int(criteria_percentages[i])
            })

        save_data(judges, contestants, criteria, scores)
        return redirect(url_for('admin'))

    return render_template('admin.html', judges=judges, contestants=contestants, criteria=criteria)

# Admin login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple check for admin credentials
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))

        return "Login failed. Please check your credentials."

    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
