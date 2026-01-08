#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Slack notification trigger for DaVinci Resolve Deliver render jobs.

Install location (macOS):
  ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Deliver

Resolve will execute this script and provide the following global variables:
  job:    render job id (string / int depending on Resolve)
  status: render status string
  error:  error string (if any)

Notes
  - This script prints progress messages to the console (Resolve scripting console / logs).
  - Slack credentials are kept in the script as requested.
  - For modern Slack Python, this script uses slack_sdk (not the deprecated slackclient import path).

Dependencies (in the Python environment used by Resolve):
  pip install slack_sdk
"""

import datetime
import json
import os
import platform
import socket
import sys
import traceback
import subprocess

# --------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "resolve_slack_settings", "resolve_slack_settings.json")

LOG_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

# Temporary default log path, used before config is loaded
LOG_PATH = os.path.expanduser(f"~/Desktop/resolve_slack_deliver_{LOG_DATE}.log")

def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str) -> None:
    print(f"[{_ts()}] {msg}")
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{_ts()}] {msg}\n")
    except Exception:
        pass

def ensure_config_exists(config_path: str) -> bool:
    if os.path.isfile(config_path):
        return True

    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        template = {
            "slack_token": "xoxb-REPLACE_WITH_YOUR_TOKEN",
            "channel_name": "CXXXXXXXX",
            "log_directory": "~/Desktop/resolve_slack_deliver_{{date}}.log"
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2)

        log(f"Config created at {config_path}")
        log("Please edit the file and relaunch the render.")
        return False

    except Exception:
        log("Config error: failed to create config file")
        log(traceback.format_exc())
        return False

def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        raw = f.read()

    if not raw.strip():
        raise ValueError("Config file is empty")

    cfg = json.loads(raw)
    if not isinstance(cfg, dict):
        raise ValueError("Config root must be a JSON object")
    return cfg

def init_from_config() -> bool:
    global LOG_PATH
    global slack_token
    global channel_name

    if not ensure_config_exists(CONFIG_PATH):
        return False

    try:
        cfg = load_config(CONFIG_PATH)

        slack_token = str(cfg.get("slack_token", "")).strip()
        channel_name = str(cfg.get("channel_name", "")).strip()

        LOG_PATH = build_log_path(cfg)

        log_dir = os.path.dirname(LOG_PATH)
        if not os.path.isdir(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception:
                log(f"Config error: cannot create log directory {log_dir}")
                return False

        if not slack_token:
            log("Config error: 'slack_token' is missing or empty")
            return False

        if not channel_name:
            log("Config error: 'channel_name' is missing or empty")
            return False

        return True

    except Exception as e:
        log(f"Config error: {e}")
        log(traceback.format_exc())
        return False

def ensure_slack_sdk_installed(log_func) -> bool:
    try:
        import slack_sdk  # noqa
        log_func("Dependency check: slack_sdk already installed")
        return True
    except Exception:
        log_func("Dependency check: slack_sdk missing, attempting installation")

    try:
        python_exec = sys.executable
        log_func(f"Dependency install: using python {python_exec}")

        result = subprocess.run(
            [python_exec, "-m", "pip", "install", "--upgrade", "slack_sdk"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.stdout.strip():
            log_func("pip stdout:\n" + result.stdout.strip())
        if result.stderr.strip():
            log_func("pip stderr:\n" + result.stderr.strip())

        if result.returncode != 0:
            log_func("Dependency install failed (pip error)")
            return False

        import slack_sdk  # noqa
        log_func("Dependency install: slack_sdk successfully installed")
        return True

    except Exception as e:
        log_func(f"Dependency install failed: {e}")
        log_func(traceback.format_exc())
        return False

def build_log_path(cfg: dict) -> str:
    base_dir = cfg.get("log_directory", "~/Desktop")
    if not isinstance(base_dir, str) or not base_dir.strip():
        base_dir = "~/Desktop"

    base_dir = os.path.expanduser(base_dir)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"resolve_slack_deliver_{date_str}.log"

    return os.path.join(base_dir, filename)

def get_resolve():
    r = globals().get("resolve")
    if r is not None:
        return r
    try:
        import DaVinciResolveScript  # type: ignore
        r = DaVinciResolveScript.scriptapp("Resolve")
        if r is not None:
            return r
    except Exception:
        pass
    return None

def get_globals():
    return globals().get("job"), globals().get("status"), globals().get("error")

def get_job_details(project, job_id):
    try:
        job_list = project.GetRenderJobList() or []
    except Exception:
        return None

    for jd in job_list:
        try:
            if jd.get("JobId") == job_id:
                return jd
        except Exception:
            continue
    return None

def get_detailed_status(project, job_id):
    if job_id is None:
        return None
    try:
        return project.GetRenderJobStatus(job_id)
    except Exception:
        return None

def pick_status(status_global, detailed_status):
    if status_global:
        return str(status_global)
    if isinstance(detailed_status, dict):
        s = detailed_status.get("Status") or detailed_status.get("status")
        if s:
            return str(s)
    if detailed_status:
        return str(detailed_status)
    return "Unknown"

def build_slack_message(project_name, status_global, error_global, job_details, detailed_status):
    st = pick_status(status_global, detailed_status)

    timeline = None
    outname = None

    if isinstance(job_details, dict):
        timeline = job_details.get("TimelineName") or job_details.get("Timeline") or None
        outname = (
            job_details.get("OutputFilename")
            or job_details.get("FileName")
            or job_details.get("CustomName")
            or None
        )

    parts = []
    parts.append(f"{st}")

    if project_name:
        parts.append(f"[{project_name}]")

    if timeline:
        parts.append(f"{timeline}")

    if outname:
        parts.append(f"→ {outname}")

    if error_global:
        parts.append(f"(Error: {str(error_global).strip()})")

    return " ".join(parts)

def notify_slack(message: str) -> bool:
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except Exception:
        log("Slack: missing slack_sdk")
        log(traceback.format_exc())
        return False

    client = WebClient(token=slack_token)

    try:
        resp = client.chat_postMessage(channel=channel_name, text=message)
        ok = bool(resp.get("ok", True))
        return ok
    except SlackApiError as e:
        err = None
        try:
            err = e.response.get("error")
        except Exception:
            err = str(e)
        log(f"SlackApiError: {err}")
        return False
    except Exception:
        log("Slack: unexpected error")
        log(traceback.format_exc())
        return False

def notify_macos(title: str, message: str) -> None:
    try:
        safe_title = title.replace('"', '\\"')
        safe_msg = message.replace('"', '\\"')
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_msg}" with title "{safe_title}"'],
            check=False
        )
    except Exception:
        log("macOS notification failed")
        log(traceback.format_exc())

def main():
    if not init_from_config():
        return

    if not ensure_slack_sdk_installed(log):
        log("Fatal: slack_sdk dependency unavailable")
        return

    log("Deliver hook: start")
    log(f"Python: {sys.version.split()[0]} ({sys.executable})")
    log(f"Host: {socket.gethostname()} | OS: {platform.platform()}")
    log(f"Config path: {CONFIG_PATH}")
    log(f"Log path: {LOG_PATH}")

    job_id, status_global, error_global = get_globals()
    log(f"Trigger globals: job={job_id!r} status={status_global!r} error={error_global!r}")

    r = get_resolve()
    if r is None:
        log("Resolve API: could not obtain 'resolve'")
        return

    try:
        pm = r.GetProjectManager()
        project = pm.GetCurrentProject() if pm else None
    except Exception:
        log("Resolve API: error while getting current project")
        log(traceback.format_exc())
        return

    if project is None:
        log("Resolve API: no current project")
        return

    try:
        project_name = project.GetName()
    except Exception:
        project_name = "(unknown)"

    detailed_status = get_detailed_status(project, job_id)
    job_details = get_job_details(project, job_id) if job_id is not None else None

    slack_msg = build_slack_message(
        project_name=project_name,
        status_global=status_global,
        error_global=error_global,
        job_details=job_details,
        detailed_status=detailed_status,
    )

    log(f"Slack message: {slack_msg}")

    ok = notify_slack(slack_msg)
    log("Deliver hook: done (Slack OK)" if ok else "Deliver hook: done (Slack FAILED)")

    notify_macos("DaVinci Resolve", slack_msg)

if __name__ == "__main__":
    slack_token = ""
    channel_name = ""
    try:
        main()
    except Exception:
        log("Deliver hook: fatal error")
        log(traceback.format_exc())