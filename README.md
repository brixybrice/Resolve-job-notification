 DaVinci Resolve Render Notifications

Slack & macOS notifications for Deliver render jobs

This project provides a robust Python script for DaVinci Resolve (macOS) that sends a minimal Slack message and a native macOS notification whenever a render job finishes in the Deliver page.

It is designed for professional post-production workflows, with an emphasis on reliability, clarity, and zero noise.

⸻

Features
	•	Triggered automatically at the end of a render job (Deliver page)
	•	Sends a concise Slack notification
	•	Displays a native macOS notification (no external tools required)
	•	External JSON configuration file (no secrets hardcoded)
	•	Automatic creation of the config file if missing
	•	Daily log files with date-based naming
	•	Optional automatic installation of slack_sdk
	•	Fully compatible with DaVinci Resolve Deliver scripts on macOS
	•	Defensive logging and clear error reporting

⸻

Example Slack Message

Complete [MyProject] Timeline_01 → master_prores.mov

In case of failure:

Failed [MyProject] Timeline_01 → master_prores.mov (Error: ...)


⸻

Requirements
	•	macOS
	•	DaVinci Resolve (Deliver page scripting enabled)
	•	Python environment bundled with DaVinci Resolve
	•	Slack Bot Token with chat:write scope
	•	Internet access for Slack notifications

⸻

Installation

1. Script location

Copy the script into the Deliver scripts folder:

~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Deliver/

Example structure:

Deliver/
├── job_notif.py
└── resolve_slack_settings/
    └── resolve_slack_settings.json

2. First run (automatic config creation)

On first execution, if the configuration file does not exist, the script will create:
resolve_slack_settings/resolve_slack_settings.json

with a template and stop execution.

Edit the file before running again.

⸻

Configuration File

resolve_slack_settings/resolve_slack_settings.json
{
  "slack_token": "xoxb-REPLACE_WITH_YOUR_TOKEN",
  "channel_name": "C0123456789",
  "log_directory": "~/Desktop"
}

Configuration fields
	•	slack_token
Slack Bot User OAuth Token (xoxb-...)
	•	channel_name
Slack channel ID (C... or G... recommended)
	•	log_directory
Directory where daily log files will be written
The script generates filenames automatically:

resolve_slack_deliver_YYYY-MM-DD.log



⸻

Slack Setup
	1.	Create a Slack App
	2.	Add a Bot User
	3.	Grant OAuth scope:
	•	chat:write
	4.	Install the app to your workspace
	5.	Invite the bot to the target channel
	6.	Copy the Bot User OAuth Token (xoxb-...)

⸻

DaVinci Resolve Setup
	1.	Go to the Deliver page
	2.	Open Render Settings → Advanced Settings
	3.	Enable Trigger script at End
	4.	Select the script (job_notif.py)
	5.	Save this as a Render Preset (recommended)

Every render using this preset will trigger notifications automatically.

⸻

Logs
	•	Logs are written to the directory defined in log_directory
	•	One log file per day
	•	Logs include:
	•	Script execution
	•	Config loading
	•	Dependency checks
	•	Slack errors
	•	Resolve API issues

Example:
resolve_slack_deliver_2026-01-08.log

Dependency Handling

The script checks whether slack_sdk is available in Resolve’s Python environment.

If missing, it will:
	•	Attempt to install it using Resolve’s embedded Python
	•	Log the result
	•	Abort cleanly if installation fails

No silent failures.

⸻

What This Script Does Not Do
	•	No render queue polling
	•	No performance metrics
	•	No GPU / CPU usage
	•	No filesystem scanning
	•	No background daemon

It only reacts to what Resolve explicitly provides at the end of a render job.

⸻

Intended Use Cases
	•	Local render workstation
	•	Editor or colorist wanting immediate feedback
	•	Small studio pipelines
	•	Slack-based monitoring without noise

⸻

License

MIT License
Use, modify, and integrate freely.
