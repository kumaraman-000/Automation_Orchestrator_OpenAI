from flask import Flask, render_template, jsonify, request
from orchestrator import ScriptOrchestrator, send_email
import threading
import os
from pathlib import Path


app = Flask(__name__, static_folder="Static", static_url_path="/static")
orchestrator = ScriptOrchestrator()
BASE_DIR = Path(__file__).resolve().parent

@app.route("/")
def index():
    return render_template("index.html", scripts=orchestrator.scripts)

@app.route("/status")
def status():
    return jsonify(orchestrator.get_status())

@app.route("/run_all", methods=["POST"])
def run_all():
    def run_and_email():
        completed_status = {}
        try:
            completed_status = orchestrator.run_all()
        finally:
            send_email(completed_status or orchestrator.get_status())

    threading.Thread(target=run_and_email).start()
    return jsonify({"message": "All scripts are running"})

@app.route("/run_script", methods=["POST"])
def run_script():
    script = request.json.get("script")

    def run_one_and_email():
        completed_status = None
        try:
            completed_status = orchestrator.run_script(script)
        finally:
            if completed_status:
                send_email({script: completed_status})

    threading.Thread(target=run_one_and_email).start()
    return jsonify({"message": f"{script} is running"})

@app.route("/failure_detail/<path:script>")
def failure_detail(script):
    status = orchestrator.get_status().get(script, {})
    screenshot_path = f"static/screenshots/{os.path.basename(script).replace('.py', '')}.png"
    screenshot_file = BASE_DIR / "Static" / "screenshots" / f"{os.path.basename(script).replace('.py', '')}.png"
    return jsonify({
        "stderr": status.get("stderr", ""),
        "stdout": status.get("stdout", ""),
        "summary": status.get("summary", ""),  #  Add this for summary
        "decision": status.get("decision", ""),  # Add this for decision making
        "ticket": status.get("ticket", ""),
        "screenshot": f"/{screenshot_path}" if screenshot_file.exists() else ""
    })

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=5000)
