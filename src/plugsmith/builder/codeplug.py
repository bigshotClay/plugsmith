"""Generate qdmr-compatible YAML codeplug from zone specs."""

import logging
from typing import Optional

from .zones import tg_name, MAX_CHANNELS, CHANNEL_NAME_MAX

log = logging.getLogger(__name__)


def generate_codeplug_yaml(
    zone_specs: list[dict],
    dmr_id: int,
    callsign: str,
    dmr_talkgroups: Optional[list[tuple]] = None,
    hw_settings: Optional[dict] = None,
    hw_settings_key: Optional[str] = None,
) -> dict:
    """Generate a qdmr-compatible codeplug dict from pre-built zone specs.

    Args:
        zone_specs: List of {"name", "tier", "state", "channels"} dicts.
            Each channel dict has: ch_type ("analog"|"digital"), name, rx_freq, tx_freq,
            pl_tone, tsq_tone (analog); color_code, time_slot, tg_num (digital).
        dmr_id: Operator DMR ID number.
        callsign: Operator callsign.
        dmr_talkgroups: Unused; kept for API symmetry.
        hw_settings: Optional hardware settings dict for the target radio family.
        hw_settings_key: config.yaml key for the hw block (e.g. "anytone_settings").
            The qdmr YAML key is derived by stripping the "_settings" suffix.
    """
    settings: dict = {
        "defaultID": callsign,
        "introLine1": callsign,
        "introLine2": "plugsmith",
        "micLevel": 5,
        "speech": False,
        "power": "High",
        "squelch": 2,
        "vox": 0,
        "tot": 180,
    }
    if hw_settings and hw_settings_key:
        qdmr_key = hw_settings_key.removesuffix("_settings")
        settings[qdmr_key] = hw_settings

    codeplug: dict = {
        "version": "0.12.0",
        "settings": settings,
        "radioIDs": [
            {"dmr": {"id": callsign, "name": callsign, "number": dmr_id}}
        ],
        "contacts": [],
        "groupLists": [],
        "channels": [],
        "zones": [],
        "scanLists": [],
    }

    # Collect all TG numbers referenced in digital channels
    used_tg_nums: set[int] = {9998, 4000}  # Parrot + Disconnect always present
    for zs in zone_specs:
        for ch in zs["channels"]:
            if ch["ch_type"] == "digital":
                used_tg_nums.add(ch["tg_num"])

    # Build contacts
    contact_ids: dict[int, str] = {}
    for tg_num in sorted(used_tg_nums):
        tg_id = f"tg{tg_num}"
        tg_type = "PrivateCall" if tg_num in (9998, 4000) else "GroupCall"
        codeplug["contacts"].append({
            "dmr": {
                "id": tg_id,
                "name": tg_name(tg_num),
                "type": tg_type,
                "number": tg_num,
            }
        })
        contact_ids[tg_num] = tg_id

    # Group lists
    group_ids = [contact_ids[n] for n in sorted(used_tg_nums) if n not in (9998, 4000)]
    codeplug["groupLists"].append({"id": "gl_all", "name": "All TGs", "contacts": group_ids})
    local_tg_ids = [contact_ids[n] for n in [9, 8, 3100] if n in contact_ids]
    codeplug["groupLists"].append({"id": "gl_local", "name": "Local TGs", "contacts": local_tg_ids})

    # Build channels and zones with global deduplication
    ch_counter = 0
    seen_channels: dict[tuple, str] = {}  # dedup_key -> ch_id

    for zs in zone_specs:
        zone_ch_ids: list[str] = []
        zone_ch_id_set: set[str] = set()

        for ch in zs["channels"]:
            if ch["ch_type"] == "analog":
                dedup_key = (
                    "a",
                    round(ch["rx_freq"], 4),
                    round(ch["tx_freq"], 4),
                    ch.get("pl_tone"),
                )
            else:
                dedup_key = (
                    "d",
                    round(ch["rx_freq"], 4),
                    round(ch["tx_freq"], 4),
                    ch.get("time_slot", 1),
                    ch.get("tg_num"),
                )

            if dedup_key not in seen_channels:
                ch_counter += 1
                ch_id = f"ch{ch_counter}"
                seen_channels[dedup_key] = ch_id

                if ch["ch_type"] == "analog":
                    entry: dict = {
                        "analog": {
                            "id": ch_id,
                            "name": ch["name"],
                            "rxFrequency": ch["rx_freq"],
                            "txFrequency": ch["tx_freq"],
                            "power": "High",
                            "timeout": 180,
                            "rxOnly": False,
                            "admit": "Always",
                            "bandwidth": "Wide",
                        }
                    }
                    if ch.get("pl_tone"):
                        entry["analog"]["txTone"] = {"ctcss": ch["pl_tone"]}
                    if ch.get("tsq_tone"):
                        entry["analog"]["rxTone"] = {"ctcss": ch["tsq_tone"]}
                else:
                    tg_num = ch["tg_num"]
                    entry = {
                        "digital": {
                            "id": ch_id,
                            "name": ch["name"],
                            "rxFrequency": ch["rx_freq"],
                            "txFrequency": ch["tx_freq"],
                            "power": "High",
                            "timeout": 180,
                            "rxOnly": False,
                            "admit": "ColorCode",
                            "colorCode": ch.get("color_code", 1),
                            "timeSlot": f"TS{ch.get('time_slot', 1)}",
                            "radioID": callsign,
                            "contact": contact_ids.get(tg_num, f"tg{tg_num}"),
                            "groupList": "gl_all",
                        }
                    }
                codeplug["channels"].append(entry)

            ch_id = seen_channels[dedup_key]
            if ch_id not in zone_ch_id_set:
                zone_ch_ids.append(ch_id)
                zone_ch_id_set.add(ch_id)

        if zone_ch_ids:
            zone_id = f"zone_{zs['name'].replace(' ', '_').replace('/', '_')}"
            codeplug["zones"].append({
                "id": zone_id,
                "name": zs["name"][:CHANNEL_NAME_MAX],
                "A": zone_ch_ids,
            })

    n_ch = len(codeplug["channels"])
    if n_ch > MAX_CHANNELS:
        log.warning(f"Channel count {n_ch} exceeds radio limit of {MAX_CHANNELS}!")

    return codeplug
