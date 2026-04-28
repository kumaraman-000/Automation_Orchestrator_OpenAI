from concurrent.futures import ThreadPoolExecutor
import json
import os
import smtplib
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

from ai_agent.summarize import summarize_log, create_ticket, decision_maker


MAX_PARALLEL = 1
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class ScriptOrchestrator:
    def __init__(self):
        self.scripts = self.load_scripts()
        self.status_lock = threading.Lock()
        self.status = {
            s: {
                "status": "Pending",
                "start": None,
                "end": None,
                "stdout": "",
                "stderr": "",
                "summary": "",
                "decision": "",
                "ticket": "",
            }
            for s in self.scripts
        }
        self.log_file = BASE_DIR / "logs" / "json_log.json"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists() or not self.log_file.read_text().strip():
            self.log_file.write_text("[]")
        else:
            try:
                json.loads(self.log_file.read_text())
            except json.JSONDecodeError:
                backup_file = self.log_file.with_suffix(".invalid.json")
                self.log_file.replace(backup_file)
                self.log_file.write_text("[]")
                print(f"Invalid JSON log moved to: {backup_file}")

    def load_scripts(self):
        with open(BASE_DIR / "config" / "scripts.json") as f:
            return json.load(f)["scripts"]

    def resolve_script_path(self, script_path):
        path = Path(script_path)
        if path.is_absolute():
            return path

        candidates = [
            Path.cwd() / path,
            BASE_DIR / path,
            BASE_DIR.parent / path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return BASE_DIR.parent / path

    def log_run(self, script, status, start_time, end_time, message="", details=None):
        details = details or {}
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "script": script,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "message": message,
            "summary": details.get("summary", ""),
            "decision": details.get("decision", ""),
            "ticket": details.get("ticket", ""),
            "stdout": details.get("stdout", ""),
            "stderr": details.get("stderr", ""),
        }

        try:
            with open(self.log_file, "r+") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
                logs.append(entry)
                f.seek(0)
                json.dump(logs, f, indent=4)
                f.truncate()
        except Exception as e:
            print("Failed to write to JSON log:", e)

    def run_script(self, script_path):
        start_time = datetime.now().strftime("%H:%M:%S")
        with self.status_lock:
            if self.status[script_path]["status"] == "Running":
                return None

            self.status[script_path]["start"] = start_time
            self.status[script_path]["end"] = None
            self.status[script_path]["status"] = "Running"
            self.status[script_path]["stdout"] = ""
            self.status[script_path]["stderr"] = ""
            self.status[script_path]["summary"] = ""
            self.status[script_path]["decision"] = ""
            self.status[script_path]["ticket"] = ""

        resolved_script_path = self.resolve_script_path(script_path)
        result = subprocess.run(
            [sys.executable, str(resolved_script_path)],
            capture_output=True,
            text=True,
            cwd=str(BASE_DIR.parent),
        )
        end_time = datetime.now().strftime("%H:%M:%S")
        with self.status_lock:
            self.status[script_path]["stdout"] = result.stdout
            self.status[script_path]["stderr"] = result.stderr

        if result.returncode == 0:
            with self.status_lock:
                self.status[script_path]["status"] = "Pass"
                self.status[script_path]["end"] = end_time
                completed_status = self.status[script_path].copy()
            self.log_run(script_path, "Pass", start_time, end_time, details=completed_status)
            return completed_status

        screenshot_dir = BASE_DIR / "Static" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        with self.status_lock:
            self.status[script_path]["status"] = "Fail"
            self.status[script_path]["end"] = end_time
        summary = summarize_log(script_path, result.stdout, result.stderr)
        with self.status_lock:
            self.status[script_path]["summary"] = summary
        decision = decision_maker(summary, script_path, result.stdout, result.stderr)
        with self.status_lock:
            self.status[script_path]["decision"] = decision
        ticket_status = "No Ticket Raised"
        print(f"Decision made: {decision}")

        if decision == "1":
            ticket_status = create_ticket(summary, script_path, result.stdout, result.stderr)

        with self.status_lock:
            self.status[script_path]["ticket"] = ticket_status
            completed_status = self.status[script_path].copy()
        self.log_run(
            script_path,
            "Fail",
            start_time,
            end_time,
            f"Summary: {summary} | Ticket: {ticket_status}",
            details=completed_status,
        )
        return completed_status

    def run_all(self):
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
            list(executor.map(self.run_script, self.scripts))
        return self.get_status()

    def get_status(self):
        with self.status_lock:
            return {
                script: details.copy()
                for script, details in self.status.items()
            }


def _env_value(*names, default=None):
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip().strip('"').strip("'")
    return default


def _email_recipients(value):
    if not value:
        return []

    cleaned = value.strip().strip("[]")
    return [
        recipient.strip().strip('"').strip("'")
        for recipient in cleaned.split(",")
        if recipient.strip()
    ]


def send_email(status_dict):
    email_user = _env_value("EMAIL_USER")
    email_pass = _env_value("EMAIL_PASS", "EMAIL_PASSWORD")
    email_from = _env_value("EMAIL_FROM", default=email_user)
    email_to = _email_recipients(_env_value("EMAIL_TO"))
    smtp_server = _env_value("SMTP_SERVER", default="smtp.gmail.com")
    smtp_port = int(_env_value("SMTP_PORT", default="587"))
    subject = _env_value(
        "EMAIL_SUBJECT",
        "subject",
        default=f"Test Execution Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )
    

    missing_values = []
    if not email_user:
        missing_values.append("EMAIL_USER")
    if not email_pass:
        missing_values.append("EMAIL_PASS or EMAIL_PASSWORD")
    if not email_from:
        missing_values.append("EMAIL_FROM")
    if not email_to:
        missing_values.append("EMAIL_TO")

    if missing_values:
        print(f"[EMAIL SKIPPED] Missing environment values: {', '.join(missing_values)}")
        return False

    body = ""
    for script, info in status_dict.items():
        info = info or {}
        body += f"""
Script: {script}
Status: {info.get('status', 'Unknown')}
Start: {info.get('start', 'N/A')}
End: {info.get('end', 'N/A')}
Summary: {info.get('summary', 'N/A')}
Jira Ticket: {info.get('ticket', 'N/A')}
------------------------------------------------------------
"""

    msg = MIMEMultipart()
    msg["From"] = email_from
    msg["To"] = ", ".join(email_to)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_pass)
            server.send_message(msg)
        print("[EMAIL SENT] Automation Summary")
        return True
    except Exception as e:
        print("[EMAIL FAILED]", str(e))
        return False


if __name__ == "__main__":
    orchestrator = ScriptOrchestrator()
    orchestrator.run_all()
    print("All scripts executed.")
    send_email(orchestrator.get_status())
    with open(orchestrator.log_file, "r") as log_file:
        print("Log created. Kindly check.")
