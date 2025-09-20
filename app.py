from flask import Flask, render_template, request, redirect, url_for, send_file, session
import tempfile, zipfile, os, json
from dcs_briefgen import parser, generator

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # replace later

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file part", 400

    file = request.files["file"]
    if file.filename == "":
        return "No file selected", 400

    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, file.filename)
    file.save(path)

    data = parser.parse_miz(path)
    session["flights"] = data["flights"]
    session["situation"] = data["situation"]
    session["blue_task"] = data["blue_task"]
    session["start_epoch"] = data["start_epoch"]

    return redirect("/select_flights")


@app.route("/select_flights")
def select_flights():
    flights = session.get("flights", [])
    situation = session.get("situation", "")
    blue_task = session.get("blue_task", "")
    start_epoch = session.get("start_epoch")
    return render_template(
        "select.html",
        flights=flights,
        situation=situation,
        blue_task=blue_task,
        start_epoch = start_epoch
    )


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

@app.route('/review')
def review():
    flights = session.get('selected_flights', [])
    return render_template('review.html', flights=flights)

@app.route('/get_flight/<int:index>')
def get_flight(index):
    flights = session.get('selected_flights', [])
    if 0 <= index < len(flights):
        return flights[index]
    return {}, 404

@app.route("/flights/<flight_id>")
def flight_detail(flight_id):
    flights = session.get("flights", [])
    flight = next((f for f in flights if f["group_name"] == flight_id), None)
    if not flight:
        return "Flight not found", 404

    return render_template("flight.html", flight=flight)

if __name__ == "__main__":
    app.run(debug=True)