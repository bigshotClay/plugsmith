"""Data models for repeaters and channels."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Repeater:
    """Represents a single repeater from RepeaterBook."""
    callsign: str
    frequency: float       # output (RX) frequency
    input_freq: float      # input (TX) frequency
    offset: float
    pl_tone: Optional[float]   # CTCSS encode tone
    tsq_tone: Optional[float]  # CTCSS decode tone (for squelch)
    city: str
    county: str
    state: str
    state_abbr: str
    lat: float
    lon: float
    use: str               # OPEN, CLOSED, PRIVATE
    status: str            # On-air, Off-air, Testing
    is_fm: bool
    is_dmr: bool
    is_dstar: bool
    is_fusion: bool
    is_nxdn: bool
    is_p25: bool
    dmr_color_code: Optional[int]
    dmr_id: Optional[str]
    is_m17: bool = False
    is_tetra: bool = False
    m17_can: Optional[str] = None    # M17 Channel Access Number
    p25_nac: Optional[str] = None    # APCO P-25 Network Access Code
    tetra_mcc: Optional[str] = None  # Tetra MCC
    tetra_mnc: Optional[str] = None  # Tetra MNC
    landmark: str = ""
    distance: float = 0.0  # calculated distance from reference point


@dataclass
class Channel:
    """A channel entry for the codeplug."""
    name: str
    rx_freq: float
    tx_freq: float
    power: str = "High"
    # Analog
    is_analog: bool = True
    tx_tone: Optional[float] = None  # CTCSS encode
    rx_tone: Optional[float] = None  # CTCSS decode
    bandwidth: str = "Wide"          # Wide (25kHz) or Narrow (12.5kHz)
    # Digital
    color_code: int = 1
    time_slot: int = 1
    contact: str = ""
    group_list: str = ""
    # Metadata
    repeater: Optional[Repeater] = None
