"""Radio-specific hardware settings metadata for in-app documentation and editing.

Each SettingMeta entry provides the YAML key, display label, type information,
description of what the setting does, recommended value for amateur radio
operation, and any legal or safety warnings.

The ANYTONE_SETTINGS list covers the anytone_settings block used by the
AT-D868UV, AT-D878UV, AT-D878UVII, and AT-D578UV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SettingMeta:
    """Metadata for a single radio hardware setting."""

    key: str
    """YAML field key within its group dict (e.g. 'encryption')."""

    label: str
    """Short UI label shown next to the control."""

    stype: str
    """Widget type: 'bool' | 'int' | 'str' | 'enum'."""

    description: str
    """Plain-language explanation of what this setting does."""

    ham_preferred: str
    """Recommended value or state for amateur radio operation."""

    warning: str | None = None
    """Legal or safety warning shown prominently in orange. None = no warning."""

    options: list[str] | None = None
    """Valid string values for enum types. None for bool/int/str."""

    default: Any = None
    """Default value used when the key is absent from config."""


# ---------------------------------------------------------------------------
# AnyTone settings groups
# Each entry: (display_name, yaml_subkey, list[SettingMeta])
# The yaml_subkey is the key under anytone_settings in config.yaml.
# ---------------------------------------------------------------------------

ANYTONE_SETTINGS: list[tuple[str, str, list[SettingMeta]]] = [

    # ------------------------------------------------------------------
    # Boot
    # ------------------------------------------------------------------
    (
        "Boot",
        "bootSettings",
        [
            SettingMeta(
                key="bootDisplay",
                label="Boot Screen",
                stype="enum",
                options=["Default", "Image", "Battery", "Off"],
                default="Default",
                description=(
                    "What to show on the display during radio startup. "
                    "'Default' shows the radio model info screen. 'Image' shows "
                    "a custom bitmap stored on the SD card. 'Battery' shows "
                    "the current charge level."
                ),
                ham_preferred="Default",
            ),
            SettingMeta(
                key="bootPasswordEnabled",
                label="Boot Password",
                stype="bool",
                default=False,
                description=(
                    "Requires a numeric PIN before the radio will fully power on. "
                    "Prevents unauthorized use if the radio is lost or stolen. "
                    "If the password is forgotten, a full factory reset is required "
                    "to recover the radio, erasing all programmed channels and settings."
                ),
                ham_preferred="Disabled",
                warning=(
                    "Keep disabled. If you forget the PIN, recovery requires a "
                    "factory reset that wipes all programmed channels and settings."
                ),
            ),
            SettingMeta(
                key="defaultChannel",
                label="Default Channel on Boot",
                stype="bool",
                default=False,
                description=(
                    "When enabled, the radio always starts on Zone A's priority "
                    "channel every time it powers on, rather than resuming the "
                    "last used channel."
                ),
                ham_preferred="Disabled — resume last used channel",
            ),
            SettingMeta(
                key="gpsCheck",
                label="Require GPS Fix Before TX",
                stype="bool",
                default=False,
                description=(
                    "When enabled, the radio will not allow transmission until "
                    "a GPS satellite fix has been acquired. Intended for systems "
                    "that require position data before operation."
                ),
                ham_preferred="Disabled — allows TX at any time without waiting for GPS",
            ),
            SettingMeta(
                key="reset",
                label="Reset Channel on Every Boot",
                stype="bool",
                default=False,
                description=(
                    "Resets the channel selector to zone 1, channel 1 on every "
                    "power-on cycle. Rarely useful and confuses operators who "
                    "expect the radio to remember where they left off."
                ),
                ham_preferred="Disabled",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # Power Save
    # ------------------------------------------------------------------
    (
        "Power Save",
        "powerSaveSettings",
        [
            SettingMeta(
                key="powerSave",
                label="Receiver Power Save",
                stype="enum",
                options=["Off", "Save25", "Save50"],
                default="Save50",
                description=(
                    "Reduces receiver power consumption by duty-cycling the RF "
                    "front-end during idle. Save50 wakes every other frame (50% "
                    "duty cycle). Save25 wakes every fourth frame. Extends battery "
                    "life with a slight increase in response latency to weak signals."
                ),
                ham_preferred="Save50 — good balance of battery life and responsiveness",
            ),
            SettingMeta(
                key="autoShutdown",
                label="Auto Shutdown (minutes, 0=off)",
                stype="int",
                default=0,
                description=(
                    "Automatically powers off after this many minutes of inactivity "
                    "(no PTT, no received signal, no button presses). "
                    "0 disables auto-shutdown."
                ),
                ham_preferred="0 (disabled) for base/mobile; 30–60 for portable use",
            ),
            SettingMeta(
                key="atpc",
                label="Auto TX Power Control (ATPC)",
                stype="bool",
                default=False,
                description=(
                    "Automatically reduces transmitter output power based on received "
                    "signal strength from the repeater. Can save battery but may "
                    "reduce your signal margin in unpredictable ways."
                ),
                ham_preferred="Disabled — use manual power level selection",
            ),
            SettingMeta(
                key="fan",
                label="Cooling Fan",
                stype="enum",
                options=["Off", "Sub", "Main", "PTT"],
                default="PTT",
                description=(
                    "Controls when the internal cooling fan runs to manage heat. "
                    "'PTT' = fan only runs during transmit (quiet, effective). "
                    "'Main' = fan runs whenever the radio is powered on. "
                    "'Sub' = low-speed continuous. 'Off' = fan never runs."
                ),
                ham_preferred="PTT — thermal protection during TX, silent otherwise",
                warning=(
                    "Setting to 'Off' may cause overheating during extended transmissions "
                    "at high power. Use 'PTT' or 'Main' for high-duty-cycle operation."
                ),
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # Programmable Keys
    # ------------------------------------------------------------------
    (
        "Programmable Keys",
        "keySettings",
        [
            SettingMeta(
                key="funcKey1Short",
                label="P1 Key — Short Press",
                stype="str",
                default="Monitor",
                description=(
                    "Function assigned to a short press of the P1 programmable button "
                    "(top side key on most AnyTone models). "
                    "Monitor forces the squelch fully open to hear weak signals. "
                    "Other common values: Scan, Reverse, Zone, Power, Repeater."
                ),
                ham_preferred="Monitor — lets you verify a frequency is clear",
            ),
            SettingMeta(
                key="funcKey1Long",
                label="P1 Key — Long Press",
                stype="str",
                default="Scan",
                description=(
                    "Function assigned to holding P1 for the long-press duration. "
                    "Scan starts the channel scan mode."
                ),
                ham_preferred="Scan",
            ),
            SettingMeta(
                key="funcKey2Short",
                label="P2 Key — Short Press",
                stype="str",
                default="Reverse",
                description=(
                    "Function for a short press of the P2 button (second side key). "
                    "'Reverse' swaps TX and RX frequencies so you can listen on the "
                    "repeater's input — essential for checking if someone is "
                    "transmitting direct without going through the machine."
                ),
                ham_preferred="Reverse — fundamental repeater troubleshooting tool",
            ),
            SettingMeta(
                key="funcKey2Long",
                label="P2 Key — Long Press",
                stype="str",
                default="Off",
                description="Function for holding P2.",
                ham_preferred="Off or Zone",
            ),
            SettingMeta(
                key="funcKey3Short",
                label="P3 Key — Short Press",
                stype="str",
                default="Power",
                description=(
                    "Cycles through transmit power levels (Low → Medium → High) "
                    "with each press. Useful for adjusting output when working "
                    "close-in stations or reducing QRM."
                ),
                ham_preferred="Power — quick TX power adjustment",
            ),
            SettingMeta(
                key="funcKey3Long",
                label="P3 Key — Long Press",
                stype="str",
                default="Off",
                description="Function for holding P3.",
                ham_preferred="Off",
            ),
            SettingMeta(
                key="funcKey4Short",
                label="P4 Key — Short Press",
                stype="str",
                default="Repeater",
                description=(
                    "'Repeater' toggles talkaround mode — the radio transmits and "
                    "receives on the output (RX) frequency, bypassing the repeater "
                    "offset. Essential when working another station direct."
                ),
                ham_preferred="Repeater — talkaround toggle",
            ),
            SettingMeta(
                key="funcKey4Long",
                label="P4 Key — Long Press",
                stype="str",
                default="SMS",
                description="Function for holding P4.",
                ham_preferred="SMS or Off",
            ),
            SettingMeta(
                key="funcKey5Short",
                label="P5 Key — Short Press",
                stype="str",
                default="Off",
                description="Function for a short press of P5 (if present on your model).",
                ham_preferred="Off or GPS",
            ),
            SettingMeta(
                key="funcKey5Long",
                label="P5 Key — Long Press",
                stype="str",
                default="Dial",
                description="Function for holding P5.",
                ham_preferred="Dial or Off",
            ),
            SettingMeta(
                key="funcKey6Short",
                label="P6 Key — Short Press",
                stype="str",
                default="Off",
                description=(
                    "Function for a short press of P6. The 'Encryption' option assigns "
                    "this key to toggle encrypted mode on/off. On amateur radio "
                    "frequencies, encryption is prohibited — an accidental key press "
                    "could silently engage encryption without the operator knowing."
                ),
                ham_preferred="Off",
                warning=(
                    "Do NOT assign 'Encryption' to any programmable key. "
                    "Encryption is prohibited on amateur radio frequencies under "
                    "47 CFR Part 97.113(a)(4). If assigned, accidental activation "
                    "would silently make your transmissions illegal."
                ),
            ),
            SettingMeta(
                key="funcKey6Long",
                label="P6 Key — Long Press",
                stype="str",
                default="Off",
                description="Function for holding P6. Same encryption risk applies.",
                ham_preferred="Off",
                warning=(
                    "Do NOT assign 'Encryption'. See P6 Short Press warning above."
                ),
            ),
            SettingMeta(
                key="longPressDuration",
                label="Long Press Duration",
                stype="enum",
                options=["0.5 s", "1 s", "2 s", "3 s"],
                default="1 s",
                description=(
                    "How long a button must be held before the radio treats it as a "
                    "long press rather than a short press."
                ),
                ham_preferred="1 s — responsive but avoids accidental long-presses",
            ),
            SettingMeta(
                key="upDownKeys",
                label="Up/Down Key Function",
                stype="enum",
                options=["Channel", "Volume"],
                default="Channel",
                description=(
                    "What the up/down arrow buttons (or channel knob, depending on model) "
                    "control. 'Channel' steps through memory channels. 'Volume' adjusts "
                    "audio output level."
                ),
                ham_preferred="Channel — most operators expect these keys to change channels",
            ),
            SettingMeta(
                key="autoKeyLock",
                label="Auto Key Lock",
                stype="bool",
                default=False,
                description=(
                    "Automatically locks the keypad after a period of inactivity. "
                    "Prevents accidental channel changes or settings changes when the "
                    "radio is in a pocket or bag. Requires holding a key to unlock."
                ),
                ham_preferred="Disabled — lock manually when needed",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # Tones & Alerts
    # ------------------------------------------------------------------
    (
        "Tones & Alerts",
        "toneSettings",
        [
            SettingMeta(
                key="keyTone",
                label="Key Tone",
                stype="bool",
                default=False,
                description=(
                    "Plays a short click tone every time a button is pressed, "
                    "providing audible feedback. Can be distracting to nearby "
                    "operators or in quiet environments."
                ),
                ham_preferred="Disabled",
            ),
            SettingMeta(
                key="dmrTalkPermit",
                label="DMR Talk Permit Tone",
                stype="bool",
                default=True,
                description=(
                    "Plays a short beep when the radio successfully acquires a DMR "
                    "time slot and the network has granted channel access. "
                    "This is your go-ahead signal — wait for the tone before speaking "
                    "to ensure your transmission actually makes it onto the network."
                ),
                ham_preferred="Enabled — do not speak until you hear the permit tone",
            ),
            SettingMeta(
                key="fmTalkPermit",
                label="FM Talk Permit Tone",
                stype="bool",
                default=False,
                description=(
                    "Plays a tone when you begin transmitting on an FM analog channel. "
                    "Less critical than the DMR permit tone since FM TX starts instantly "
                    "without waiting for slot allocation."
                ),
                ham_preferred="Disabled",
            ),
            SettingMeta(
                key="smsAlert",
                label="SMS Alert Tone",
                stype="bool",
                default=True,
                description=(
                    "Plays an alert tone when a DMR SMS message is received — for "
                    "example, a BrandMeister system notification, net announcement, "
                    "or direct message from another station."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="callAlert",
                label="Call Alert Tone",
                stype="bool",
                default=True,
                description=(
                    "Plays a tone when a DMR private call arrives addressed specifically "
                    "to your radio's DMR ID. Useful when the radio is not in hand."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="dmrIdle",
                label="DMR Idle Channel Tone",
                stype="bool",
                default=False,
                description=(
                    "Plays periodic tones on an idle DMR channel to confirm the radio "
                    "is still active on the time slot. These tones transmit on the air "
                    "and are disruptive to other stations sharing the repeater."
                ),
                ham_preferred="Disabled — do not generate unnecessary on-air traffic",
            ),
            SettingMeta(
                key="dmrReset",
                label="DMR Reset Tone",
                stype="bool",
                default=False,
                description=(
                    "Plays a tone when a DMR call ends and the channel returns to idle. "
                    "The hang time countdown already indicates the call is winding down, "
                    "making this tone redundant for most operators."
                ),
                ham_preferred="Disabled",
            ),
            SettingMeta(
                key="startup",
                label="Startup Chime",
                stype="bool",
                default=False,
                description="Plays a chime or audio melody when the radio powers on.",
                ham_preferred="Disabled — quiet startup",
            ),
            SettingMeta(
                key="tot",
                label="TOT Warning Tone",
                stype="bool",
                default=True,
                description=(
                    "Plays a warning tone when the Transmit Timeout Timer (TOT) is "
                    "about to forcibly end your transmission. Hearing this tone means "
                    "you must release PTT immediately or the radio will cut your audio."
                ),
                ham_preferred="Enabled — critical safety and courtesy feature",
            ),
            SettingMeta(
                key="wxAlarm",
                label="Weather Alert Tone",
                stype="bool",
                default=False,
                description=(
                    "Plays an alert tone when a NOAA EAS (Emergency Alert System) "
                    "weather alert tone is decoded on a programmed weather channel. "
                    "Useful for emergency preparedness and SKYWARN operations."
                ),
                ham_preferred="Enabled if you monitor NOAA weather channels",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    (
        "Display",
        "displaySettings",
        [
            SettingMeta(
                key="brightness",
                label="Brightness (1–10)",
                stype="int",
                default=6,
                description=(
                    "Display backlight brightness level. Higher values improve "
                    "outdoor readability but consume more battery and can be blinding "
                    "in low-light conditions."
                ),
                ham_preferred="5–7 for general use; lower at night to preserve night vision",
            ),
            SettingMeta(
                key="backlightDuration",
                label="Backlight Duration (idle)",
                stype="str",
                default="15 s",
                description=(
                    "How long the backlight stays on after a button press or squelch "
                    "activity while the radio is idle. Common values: Off, 5 s, 15 s, "
                    "30 s, 1 min, 2 min, Infinite."
                ),
                ham_preferred="15 s — sufficient to read the display, then saves battery",
            ),
            SettingMeta(
                key="backlightDurationTX",
                label="Backlight Duration (TX)",
                stype="str",
                default="Infinite",
                description=(
                    "How long the backlight stays on while you are transmitting. "
                    "Keeping this 'Infinite' ensures the display is always lit during TX."
                ),
                ham_preferred="Infinite — keep display lit during all transmissions",
            ),
            SettingMeta(
                key="backlightDurationRX",
                label="Backlight Duration (RX)",
                stype="str",
                default="15 s",
                description=(
                    "How long the backlight stays on while receiving a signal "
                    "(squelch is open)."
                ),
                ham_preferred="15 s",
            ),
            SettingMeta(
                key="showClock",
                label="Show Clock",
                stype="bool",
                default=True,
                description="Displays the current time on the radio screen.",
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="showCall",
                label="Show Caller Callsign",
                stype="bool",
                default=True,
                description=(
                    "Displays the transmitting station's callsign on the screen "
                    "during an active DMR call — sourced from Talker Alias data "
                    "or a matching entry in your contact list."
                ),
                ham_preferred="Enabled — know who you're talking to",
            ),
            SettingMeta(
                key="showContact",
                label="Show Contact Name",
                stype="bool",
                default=True,
                description=(
                    "Shows the DMR contact name from your programmed contact list "
                    "for incoming calls. If the station is not in your list, falls "
                    "back to showing their numeric DMR ID."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="showLastHeard",
                label="Show Last Heard",
                stype="bool",
                default=True,
                description=(
                    "Shows the callsign or ID of the last station heard on the "
                    "current channel in the display."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="showTimeSlot",
                label="Show Time Slot",
                stype="bool",
                default=True,
                description=(
                    "Shows the active DMR time slot (TS1 or TS2) on the display. "
                    "DMR divides a single frequency into two interleaved time slots, "
                    "doubling repeater capacity. Knowing which slot your channel uses "
                    "is essential for network troubleshooting."
                ),
                ham_preferred="Enabled — important for DMR troubleshooting",
            ),
            SettingMeta(
                key="showChannelType",
                label="Show Channel Type (D/A)",
                stype="bool",
                default=True,
                description=(
                    "Displays 'D' (Digital/DMR) or 'A' (Analog/FM) to indicate which "
                    "operating mode the current channel uses."
                ),
                ham_preferred="Enabled — confirms you're in the correct mode at a glance",
            ),
            SettingMeta(
                key="showColorCode",
                label="Show Color Code",
                stype="bool",
                default=False,
                description=(
                    "Displays the DMR color code (0–15) on screen. Color codes act "
                    "like a sub-channel filter — only signals with the matching code "
                    "are decoded. The color code is already programmed per channel, "
                    "so showing it on screen is usually redundant."
                ),
                ham_preferred="Disabled — color code is set in the channel, not needed on display",
            ),
            SettingMeta(
                key="showChannelNumber",
                label="Show Channel Number",
                stype="bool",
                default=False,
                description=(
                    "Shows the memory channel number alongside the channel name. "
                    "Channel names are typically more meaningful than numbers."
                ),
                ham_preferred="Disabled — channel name conveys more information",
            ),
            SettingMeta(
                key="callEndPrompt",
                label="Call End Prompt",
                stype="bool",
                default=True,
                description=(
                    "Shows a brief on-screen notification when a DMR call ends "
                    "and the channel returns to idle."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="lastCallerDisplay",
                label="Last Caller Display",
                stype="enum",
                options=["Off", "ID+Call", "ID+Name"],
                default="Off",
                description=(
                    "Shows information about the last station to transmit on the "
                    "current channel. Helpful on busy repeaters to track who just "
                    "finished a transmission."
                ),
                ham_preferred="ID+Call — shows DMR ID and callsign",
            ),
            SettingMeta(
                key="language",
                label="Display Language",
                stype="enum",
                options=["English", "Chinese"],
                default="English",
                description="Language used for radio menus and on-screen prompts.",
                ham_preferred="English (for US operators)",
            ),
            SettingMeta(
                key="dateFormat",
                label="Date Format",
                stype="enum",
                options=["YearFirst", "MonthFirst", "DayFirst"],
                default="YearFirst",
                description=(
                    "How dates are displayed on screen. "
                    "YearFirst = YYYY-MM-DD (ISO 8601, internationally unambiguous). "
                    "MonthFirst = MM/DD/YYYY (US convention). "
                    "DayFirst = DD/MM/YYYY (European convention)."
                ),
                ham_preferred="YearFirst — unambiguous ISO 8601 format",
            ),
            SettingMeta(
                key="callColor",
                label="Caller Display Color",
                stype="enum",
                options=["Orange", "Red", "Blue", "Green", "White", "Cyan", "Purple"],
                default="Orange",
                description=(
                    "Color used to display the calling station's callsign or ID "
                    "during an active DMR call. Choose a high-contrast color for "
                    "your ambient lighting conditions."
                ),
                ham_preferred="Orange — high contrast on the AT-D878UVII display",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------
    (
        "Audio",
        "audioSettings",
        [
            SettingMeta(
                key="enhance",
                label="Audio Enhancement (DSP)",
                stype="bool",
                default=True,
                description=(
                    "Enables DSP-based audio processing including noise reduction "
                    "and automatic gain control on received audio. Generally improves "
                    "intelligibility in noisy RF or acoustic conditions."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="muteDelay",
                label="Squelch Tail Mute Delay",
                stype="str",
                default="5 min",
                description=(
                    "How long squelch stays open after a received signal drops "
                    "before closing again (squelch hang time). Prevents rapid "
                    "open/close cycles on marginal signals (squelch chatter). "
                    "Common values: Off, 500 ms, 1 s, 2 s, 5 min, Infinite."
                ),
                ham_preferred="5 min — avoids choppy audio on weak or marginal signals",
            ),
            SettingMeta(
                key="fmMicGain",
                label="FM Mic Gain (1–10)",
                stype="int",
                default=6,
                description=(
                    "Microphone preamplifier gain level for FM analog transmissions. "
                    "Higher values amplify the mic more before modulation. Too high "
                    "causes over-deviation and audio distortion on the receiving end."
                ),
                ham_preferred="5–6 — test with a signal report from another station",
            ),
            SettingMeta(
                key="enableFMMicGain",
                label="Enable FM Mic Gain Override",
                stype="bool",
                default=True,
                description=(
                    "Enables the custom FM mic gain value set above. When disabled, "
                    "the radio uses its default mic gain for FM."
                ),
                ham_preferred="Enabled",
            ),
            SettingMeta(
                key="maxVolume",
                label="Max Volume Limit (0 = no limit)",
                stype="int",
                default=0,
                description=(
                    "Caps the maximum audio output volume the user can select. "
                    "0 = no cap. A cap can protect hearing in environments where "
                    "the volume knob might be accidentally turned up."
                ),
                ham_preferred="0 — no cap; let the operator manage their own volume",
            ),
            SettingMeta(
                key="recording",
                label="Audio Recording to SD Card",
                stype="bool",
                default=False,
                description=(
                    "Enables recording of received (and optionally transmitted) audio "
                    "to an SD card installed in the radio. Useful for net logging, "
                    "traffic handling records, or emergency operations documentation."
                ),
                ham_preferred="Disabled by default; enable if call logging is needed",
            ),
            SettingMeta(
                key="voxDelay",
                label="VOX Delay (ms, 0 = off)",
                stype="int",
                default=0,
                description=(
                    "Voice Operated Transmit delay — the radio begins transmitting "
                    "automatically when audio is detected on the microphone. "
                    "0 = VOX fully disabled. Non-zero values are the hold time "
                    "after audio stops before TX drops."
                ),
                ham_preferred="0 — disabled; use PTT for precise, reliable transmit control",
            ),
            SettingMeta(
                key="voxSource",
                label="VOX Audio Source",
                stype="enum",
                options=["Mic", "USB", "Both"],
                default="Both",
                description=(
                    "Which audio input can trigger VOX transmission: internal "
                    "microphone, USB audio, or both. Only relevant if VOX delay is "
                    "non-zero."
                ),
                ham_preferred="Both (only matters if VOX is enabled)",
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # DMR
    # ------------------------------------------------------------------
    (
        "DMR",
        "dmrSettings",
        [
            SettingMeta(
                key="groupCallHangTime",
                label="Group Call Hang Time",
                stype="str",
                default="2 s",
                description=(
                    "After a DMR group call ends, the time slot remains 'warm' for "
                    "this duration before the radio releases it and returns to normal "
                    "monitoring. During hang time you can respond without waiting for "
                    "a new slot grant from the network. Common values: 1 s – 7 s."
                ),
                ham_preferred="2 s — enough time to respond conversationally",
            ),
            SettingMeta(
                key="privateCallHangTime",
                label="Private Call Hang Time",
                stype="str",
                default="5 s",
                description=(
                    "Same as group call hang time but for DMR private (direct station-to-"
                    "station) calls. A slightly longer hang time allows for natural "
                    "back-and-forth conversation rhythm."
                ),
                ham_preferred="5 s — conversational pacing for private calls",
            ),
            SettingMeta(
                key="preWaveDelay",
                label="Pre-Key (PTT) Delay",
                stype="str",
                default="300 ms",
                description=(
                    "Delay between pressing PTT and the radio actually beginning to "
                    "transmit audio. On BrandMeister and most hosted networks, the server "
                    "needs time to allocate a slot, bring up reflector connections, and "
                    "route the call. Without this delay, the first syllable of every "
                    "transmission is clipped. Common values: 0 ms, 100 ms, 200 ms, 300 ms."
                ),
                ham_preferred=(
                    "300 ms — prevents first-syllable clipping on BrandMeister and "
                    "most DMR networks"
                ),
            ),
            SettingMeta(
                key="filterOwnID",
                label="Filter Own ID (echo suppress)",
                stype="bool",
                default=False,
                description=(
                    "When enabled, the radio mutes audio from stations transmitting "
                    "your own DMR ID — preventing you from hearing yourself echoed back "
                    "when a linked reflector loops your signal. "
                    "Disabling it lets you monitor your own signal quality."
                ),
                ham_preferred="Disabled — useful to hear how your own signal sounds",
            ),
            SettingMeta(
                key="smsFormat",
                label="SMS Format",
                stype="enum",
                options=["Motorola", "Standard"],
                default="Motorola",
                description=(
                    "DMR SMS message encoding format. BrandMeister uses the Motorola "
                    "proprietary format. 'Standard' follows the ETSI DMR specification "
                    "and is used by some other networks. "
                    "Incorrect format results in garbled or undelivered messages."
                ),
                ham_preferred="Motorola — required for BrandMeister compatibility",
            ),
            SettingMeta(
                key="sendTalkerAlias",
                label="Send Talker Alias",
                stype="bool",
                default=True,
                description=(
                    "Broadcasts your callsign as a DMR Talker Alias embedded in the "
                    "radio signal. Other stations can see your callsign on their display "
                    "even if you are not in their contact list. This is the primary "
                    "identification mechanism on DMR networks."
                ),
                ham_preferred=(
                    "Enabled — strongly recommended for FCC Part 97 station identification"
                ),
            ),
            SettingMeta(
                key="talkerAliasSource",
                label="Talker Alias Source",
                stype="enum",
                options=["Radio", "SSID", "Contact", "GPS"],
                default="Radio",
                description=(
                    "Where the Talker Alias callsign data comes from. 'Radio' uses the "
                    "callsign stored in the radio's identity settings — the most reliable "
                    "choice. 'Contact' uses a matching entry in your contact list name. "
                    "'GPS' appends position data to the alias."
                ),
                ham_preferred="Radio — uses your stored callsign directly",
            ),
            SettingMeta(
                key="talkerAliasEncoding",
                label="Talker Alias Encoding",
                stype="enum",
                options=["ISO8", "7bit", "Extended"],
                default="ISO8",
                description=(
                    "Character encoding for the Talker Alias data field. "
                    "ISO8 = 8-bit Latin character set (best compatibility with most radios). "
                    "7bit = basic 7-bit ASCII subset. "
                    "Extended = extended characters for non-Latin scripts."
                ),
                ham_preferred="ISO8 — maximum compatibility with other DMR radios and networks",
            ),
            SettingMeta(
                key="monitorSlotMatch",
                label="Monitor: Slot Matching",
                stype="enum",
                options=["Off", "Single", "Both"],
                default="Off",
                description=(
                    "While in Monitor mode (forced squelch open), controls whether "
                    "received DMR signals must match the channel's configured time slot. "
                    "'Off' = decode traffic on both time slots. "
                    "'Single' = only the programmed slot."
                ),
                ham_preferred="Off — monitor all traffic on both time slots",
            ),
            SettingMeta(
                key="monitorColorCodeMatch",
                label="Monitor: Color Code Matching",
                stype="bool",
                default=False,
                description=(
                    "While in Monitor mode, requires received DMR signals to match "
                    "the channel's programmed color code. Disabling this lets you "
                    "hear all DMR signals on the frequency regardless of color code."
                ),
                ham_preferred="Disabled — monitor all traffic regardless of color code",
            ),
            SettingMeta(
                key="monitorIDMatch",
                label="Monitor: ID Matching",
                stype="bool",
                default=False,
                description=(
                    "While in Monitor mode, requires the received station's DMR ID "
                    "to match an entry in your contact list before the audio is decoded. "
                    "Disabling this lets you hear all stations."
                ),
                ham_preferred="Disabled — monitor all stations",
            ),
            SettingMeta(
                key="encryption",
                label="Encryption Algorithm",
                stype="enum",
                options=["AES", "BasicPrivacy", "EnhancedPrivacy", "ARC4", "XTEA"],
                default="AES",
                description=(
                    "The encryption algorithm that will be used IF encryption is "
                    "actively enabled AND encryption keys are programmed into the radio. "
                    "Selecting an algorithm here does NOT enable encryption — keys must "
                    "also be loaded and the encryption feature toggled on per-channel. "
                    "AES-256 is the strongest available algorithm."
                ),
                ham_preferred=(
                    "AES (algorithm only — never load encryption keys for ham band operation)"
                ),
                warning=(
                    "ENCRYPTION IS PROHIBITED on amateur radio frequencies. "
                    "47 CFR Part 97.113(a)(4) forbids transmissions in which the "
                    "meaning is obscured to other operators. Do NOT load encryption keys "
                    "or enable encrypted channels for ham band operation. Violations may "
                    "result in FCC enforcement action including license revocation."
                ),
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # GPS
    # ------------------------------------------------------------------
    (
        "GPS",
        "gpsSettings",
        [
            SettingMeta(
                key="units",
                label="Units",
                stype="enum",
                options=["Archaic", "Metric"],
                default="Archaic",
                description=(
                    "'Archaic' = US imperial units — speed in mph, distance in miles, "
                    "altitude in feet. 'Metric' = SI units — km/h, kilometers, meters. "
                    "Affects all GPS display values."
                ),
                ham_preferred="Archaic for US operators; Metric for international",
            ),
            SettingMeta(
                key="timeZone",
                label="Time Zone (UTC offset)",
                stype="str",
                default="UTC-06:00",
                description=(
                    "UTC offset applied to the GPS clock for local time display. "
                    "The radio's internal time is driven by GPS UTC — this offset "
                    "converts it to your local time. "
                    "Examples: UTC-05:00 (ET), UTC-06:00 (CT), UTC-07:00 (MT), "
                    "UTC-08:00 (PT). Adjust by +1 hour during Daylight Saving Time."
                ),
                ham_preferred=(
                    "Your local UTC offset — e.g. UTC-06:00 for Central Standard Time"
                ),
            ),
            SettingMeta(
                key="reportPosition",
                label="Report GPS Position",
                stype="bool",
                default=False,
                description=(
                    "Enables automatic position reporting — the radio periodically "
                    "transmits your GPS coordinates to a configured server (e.g., "
                    "BrandMeister GPS tracking). Your location will appear on public "
                    "GPS tracking maps such as brandmeister.network."
                ),
                ham_preferred=(
                    "Disabled unless you intentionally want to appear on tracking maps"
                ),
            ),
            SettingMeta(
                key="mode",
                label="Satellite System",
                stype="enum",
                options=[
                    "GPS",
                    "Beidou",
                    "GLONASS",
                    "GPS+Beidou",
                    "GPS+GLONASS",
                    "Beidou+GLONASS",
                    "All",
                ],
                default="GPS",
                description=(
                    "Which satellite constellation(s) to use for positioning. "
                    "GPS (American) works well in North America. Adding GLONASS "
                    "(Russian) or Beidou (Chinese) increases visible satellites, "
                    "improving fix accuracy and time-to-first-fix in poor sky views. "
                    "'All' uses every available constellation but consumes more power."
                ),
                ham_preferred=(
                    "GPS for North America; GPS+GLONASS for better urban/weak-sky coverage"
                ),
            ),
        ],
    ),
]
