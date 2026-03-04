"""Hardware config submission to GitHub Issues."""
from __future__ import annotations
import os
import textwrap
import requests

# Fine-grained PAT stored as the PAT_TOKEN GitHub Actions secret.
# At release time the CI workflow injects it via the PAT_TOKEN environment
# variable.  Locally it falls back to "" (submission is silently skipped).
GITHUB_REPO = "bigshotClay/plugsmith"
GITHUB_ISSUES_TOKEN: str = os.environ.get("PAT_TOKEN", "")

_ISSUES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/issues"
_LABEL = "hw-config-submission"


def is_submission_needed(radio_model: str, submitted_firmware: str) -> bool:
    """True when radio is unsupported AND no prior submission has been recorded."""
    from plugsmith.tool_discovery import RADIO_PROFILES
    return radio_model not in RADIO_PROFILES and not submitted_firmware


def submit_hw_profile(
    radio_key: str,
    display_name: str,
    firmware_version: str,
    hw_settings_yaml: str,
    notes: str,
    dmrconf_version: str,
) -> str:
    """POST a hardware config issue to GitHub. Returns the created issue HTML URL."""
    if not GITHUB_ISSUES_TOKEN:
        raise RuntimeError(
            "GITHUB_ISSUES_TOKEN is not configured. "
            "See src/plugsmith/hw_submit.py for setup instructions."
        )
    body = textwrap.dedent(f"""\
        ## Hardware Config Submission: {display_name} (`{radio_key}`)

        **Firmware version:** `{firmware_version}`
        **dmrconf version:** `{dmrconf_version}`
        **Submitted via:** plugsmith (in-app)

        ### Hardware settings (from config.yaml)

        ```yaml
        {hw_settings_yaml.strip() or "(none — user has not configured hw settings)"}
        ```

        ### Notes

        {notes.strip() or "(none)"}
    """)
    resp = requests.post(
        _ISSUES_URL,
        json={
            "title": f"[hw-config] {display_name} / fw {firmware_version}",
            "body": body,
            "labels": [_LABEL],
        },
        headers={
            "Authorization": f"Bearer {GITHUB_ISSUES_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]
