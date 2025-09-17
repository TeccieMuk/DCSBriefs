from flask import Flask, render_template, request, redirect, url_for, send_file, session
import tempfile, zipfile, os, json
from dcs_briefgen import parser, generator

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # replace later

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['mizfile']
    if not file or not file.filename.endswith('.miz'):
        return "Please upload a .miz file", 400

    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, file.filename)
    file.save(path)

    # Parse mission
    data = parser.parse_miz(path)
    flights = data['flights']
    situation = data['situation']
    blue_task = data['blue_task']

    session['miz_path'] = path
    session['flights'] = flights

    return render_template('select.html', flights=flights, situation=situation, blue_task=blue_task)


@app.route('/generate', methods=['POST'])
def generate():
    selected = request.form.getlist('flights')
    miz_path = session.get('miz_path')
    flights = session.get('flights')
    situation = session.get('situation', "")
    blue_task = session.get('blue_task', "")

    out_dir = tempfile.mkdtemp()
    zip_path = os.path.join(out_dir, 'briefing.zip')

    generator.create_briefing(
        miz_path,
        selected_groups=selected,
        out_zip=zip_path,
        flights=flights,
        situation=situation,
        blue_task=blue_task
    )

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)