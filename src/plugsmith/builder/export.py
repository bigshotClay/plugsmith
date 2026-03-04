"""Output formatters: qdmr YAML, Anytone CSV, and human-readable summary."""

import csv
import logging
import os
from pathlib import Path
from typing import Optional

import yaml

from .zones import MAX_CHANNELS, MAX_ZONES

log = logging.getLogger(__name__)


def write_qdmr_yaml(codeplug: dict, output_path: str) -> None:
    """Write codeplug as qdmr-compatible YAML."""
    with open(output_path, "w") as f:
        yaml.dump(codeplug, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    log.info(f"Wrote qdmr YAML codeplug to {output_path}")


def write_anytone_csv(codeplug: dict, output_dir: str) -> None:
    """Write Anytone CPS-compatible Channel.csv as a fallback import method."""
    os.makedirs(output_dir, exist_ok=True)
    ch_path = os.path.join(output_dir, "Channel.csv")
    with open(ch_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "No.", "Channel Name", "Receive Frequency", "Transmit Frequency",
            "Channel Type", "Transmit Power", "Band Width", "CTCSS/DCS Decode",
            "CTCSS/DCS Encode", "Contact", "Contact TG/DMR ID", "Color Code",
            "Repeater Slot", "Scan List", "Busy Lock/TX Permit",
        ])
        for i, ch in enumerate(codeplug["channels"], 1):
            if "analog" in ch:
                a = ch["analog"]
                decode = ""
                encode = ""
                if "rxTone" in a and "ctcss" in a["rxTone"]:
                    decode = str(a["rxTone"]["ctcss"])
                if "txTone" in a and "ctcss" in a["txTone"]:
                    encode = str(a["txTone"]["ctcss"])
                writer.writerow([
                    i, a["name"], f"{a['rxFrequency']:.5f}",
                    f"{a['txFrequency']:.5f}", "A-Analog", "High", "25K",
                    decode, encode, "", "", "", "", "", "Always",
                ])
            elif "digital" in ch:
                d = ch["digital"]
                writer.writerow([
                    i, d["name"], f"{d['rxFrequency']:.5f}",
                    f"{d['txFrequency']:.5f}", "D-Digital", "High", "12.5K",
                    "", "", d.get("contact", ""), "",
                    d.get("colorCode", 1), d.get("timeSlot", "TS1").replace("TS", ""),
                    "", "Color Code",
                ])
    log.info(f"Wrote Anytone CSV to {output_dir}/")


def write_summary(
    codeplug: dict,
    output_path: Optional[str] = None,
    zone_specs: Optional[list[dict]] = None,
) -> str:
    """Write a human-readable summary of the codeplug. Returns the summary string."""
    lines = [
        "=" * 70,
        "CODEPLUG BUILDER SUMMARY",
        "=" * 70,
    ]

    n_analog = sum(1 for ch in codeplug["channels"] if "analog" in ch)
    n_digital = sum(1 for ch in codeplug["channels"] if "digital" in ch)
    n_zones = len(codeplug["zones"])
    n_contacts = len(codeplug["contacts"])

    lines.append(f"\nTotal channels:     {n_analog + n_digital} / {MAX_CHANNELS}")
    lines.append(f"  Analog FM:        {n_analog}")
    lines.append(f"  Digital DMR:      {n_digital}")
    lines.append(f"Zones:              {n_zones} / {MAX_ZONES}")
    lines.append(f"Contacts (TGs):     {n_contacts}")

    lines.append(f"\n{'Zone':<25} {'Channels':>8}")
    lines.append("-" * 35)
    for z in codeplug["zones"]:
        lines.append(f"  {z['name']:<23} {len(z['A']):>8}")

    states_covered: set[str] = set()
    if zone_specs:
        for zs in zone_specs:
            if zs["state"]:
                states_covered.add(zs["state"])
    lines.append(f"\nStates covered: {len(states_covered)} — {', '.join(sorted(states_covered))}")

    if zone_specs:
        lines.append("")
        for tier in ("home", "adjacent", "shallow"):
            tier_zones = [zs for zs in zone_specs if zs["tier"] == tier]
            tier_states = sorted(set(zs["state"] for zs in tier_zones if zs["state"]))
            tier_ch = sum(len(zs["channels"]) for zs in tier_zones)
            if tier_states:
                lines.append(
                    f"  {tier.capitalize():<10} {len(tier_states):>2} states, "
                    f"{tier_ch:>5} channels: {', '.join(tier_states)}"
                )

    summary = "\n".join(lines)
    if output_path:
        with open(output_path, "w") as f:
            f.write(summary)
    return summary
