[storage google_cal]
type = "google_calendar"
token_file = "~/.config/vdirsyncer/google_token"
client_id = "{{GOOGLE_CLIENT_ID}}"
client_secret.fetch = ["command", "security", "find-generic-password", "-s", "vdirsyncer-google-secret", "-w"]
{{A_READ_ONLY}}

[storage strato_cal]
type = "caldav"
url = "{{STRATO_URL}}"
username = "{{STRATO_USER}}"
password.fetch = ["command", "security", "find-generic-password", "-s", "vdirsyncer-strato-password", "-w"]
