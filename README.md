# Automation Orchestrator Dashboard

This project is a small Flask-based automation dashboard for running Selenium test scripts, tracking pass/fail status, summarizing failures with OpenAI, optionally raising Jira tickets, writing JSON logs, and sending email reports.

## What This Project Does

- Runs Selenium test scripts from a web dashboard.
- Shows live script status: `Pending`, `Running`, `Pass`, or `Fail`.
- Prevents duplicate clicks while a script is already running.
- Writes run history to `logs/json_log.json`.
- Captures stdout, stderr, summary, decision, and Jira ticket status.
- Uses OpenAI to summarize failed test logs in plain English.
- Uses decision logic to decide whether a failure is a test/script issue or a webpage/product issue.
- Creates Jira tickets for product/webpage issues when Jira is configured.
- Sends email reports for both pass and fail runs.

## Project Structure

```text
python_orchestrator/
  ai_agent/
    summarize.py              # OpenAI summary, decision logic, Jira ticket creation
  config/
    scripts.json              # List of test scripts shown in the dashboard
  logs/
    json_log.json             # JSON run history
    run_log.txt               # Optional plain log file
  Static/
    styles.css                # Dashboard styles
    screenshots/              # Failure screenshots
  templates/
    index.html                # Dashboard UI
  Test_case/
    demo_login_logout.py      # Demo Selenium login/logout test
  dashboard.py                # Flask web dashboard
  orchestrator.py             # Script runner, JSON logging, email sender
  requirements.txt            # Python dependencies
  .env.example                # Environment variable template
```

## Requirements

- Python 3.10+
- Google Chrome installed
- ChromeDriver support through Selenium Manager
- Internet access for:
  - demo Selenium site
  - OpenAI API
  - Gmail SMTP
  - Jira API, if Jira ticket creation is enabled

## Setup

1. Open PowerShell in the project folder:

```powershell
cd D:\python_selenium-20250131T080010Z-001\Admin_dashboard\python_orchestrator
```

2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create your local `.env` file:

```powershell
copy .env.example .env
```

5. Fill in `.env` with your real values.

## Environment Variables

```env
OPENAI_API_KEY="your-openai-api-key"
OPENAI_MODEL="gpt-4o-mini"

EMAIL_USER="your-smtp-login@example.com"
EMAIL_PASSWORD="your-email-app-password"
EMAIL_FROM="your-sender@example.com"
EMAIL_TO="recipient1@example.com,recipient2@example.com"
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT="587"
EMAIL_SUBJECT="Automation Orchestrator Summary Report"

JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="your-jira-email@example.com"
JIRA_API_TOKEN="your-jira-api-token"
JIRA_PROJECT_KEY="PROJ"
JIRA_ISSUE_TYPE="Bug"

DEMO_USERNAME="student"
DEMO_PASSWORD="Password123"
```

For Gmail, use an app password, not your normal Gmail password.

## How To Run

Start the dashboard:

```powershell
python dashboard.py
```

Open in your browser:

```text
http://127.0.0.1:5000
```

Use the dashboard:

- Click `Run All` to run all scripts in `config/scripts.json`.
- Click `Run` beside one script to run only that script.
- If a script fails, click `Details` or the failed row to see logs, summary, decision, Jira status, and screenshot.

## How Scripts Are Configured

Scripts are listed in [config/scripts.json](config/scripts.json):

```json
{
  "scripts": [
    "python_orchestrator/Test_case/demo_login_logout.py"
  ]
}
```

Add more test files by adding their paths to this list.

## Demo Login Test

The demo test is in [Test_case/demo_login_logout.py](Test_case/demo_login_logout.py).

Default valid credentials:

```env
DEMO_USERNAME="student"
DEMO_PASSWORD="Password123"
```

To test failure handling, set an incorrect password:

```env
DEMO_PASSWORD="wrong-password"
```

Then restart the dashboard and run the script.

## Logging

Every completed run writes an entry to:

```text
logs/json_log.json
```

Each entry includes:

- timestamp
- script
- status
- start time
- end time
- summary
- decision
- Jira ticket status
- stdout
- stderr

If `json_log.json` is missing or empty, the orchestrator recreates it. If it is invalid JSON, it is backed up and recreated.

## Email Reports

Email is sent after:

- `Run All`
- individual `Run`

Email includes:

- script name
- status
- start/end time
- OpenAI or fallback summary
- Jira ticket result
- stdout
- stderr

The email code is in `send_email()` inside [orchestrator.py](orchestrator.py).

## OpenAI Summary And Decision

The OpenAI integration is in [ai_agent/summarize.py](ai_agent/summarize.py).

It does two things:

1. `summarize_log()` creates a plain-English failure summary.
2. `decision_maker()` returns:

```text
0 = script/test data/environment issue, no Jira ticket
1 = webpage/product issue, create Jira ticket
```

Examples:

- Incorrect password -> `0`
- Missing expected button -> `1`

There is also fallback logic, so common failures still get useful summaries even if the OpenAI request fails.

## Jira Ticket Creation

Jira tickets are created only when `decision_maker()` returns `1`.

Required Jira values:

```env
JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="your-jira-email@example.com"
JIRA_API_TOKEN="your-jira-api-token"
JIRA_PROJECT_KEY="PROJ"
JIRA_ISSUE_TYPE="Bug"
```

The Jira issue includes summary, script name, stdout, and stderr.

## Troubleshooting

**Dashboard does not open**

Make sure Flask is installed and run:

```powershell
python dashboard.py
```

**Email not received**

- Check `EMAIL_TO`.
- Check Gmail app password.
- Check spam folder.
- Confirm `SMTP_SERVER="smtp.gmail.com"` and `SMTP_PORT="587"`.
- Restart the dashboard after editing `.env`.

**Summary or decision not generated**

- Check `OPENAI_API_KEY`.
- Confirm `openai>=2.0.0` is installed.
- Restart the dashboard after editing `.env`.

**JSON log not updating**

- Make sure the script finishes running.
- Check `logs/json_log.json`.
- If it was invalid, the orchestrator backs it up as `json_log.invalid.json`.

**Selenium browser does not start**

- Make sure Chrome is installed.
- Upgrade Selenium if needed:

```powershell
pip install --upgrade selenium
```

## Production Notes

- Never commit `.env`.
- Rotate any API keys or app passwords that were shared accidentally.
- Keep `FLASK_DEBUG` off in production.
- Use real Jira project credentials before enabling ticket creation.
- Review generated Jira tickets before relying on automation in production.

