"""Shared fixtures for plugsmith tests."""

import pytest

from plugsmith.builder.models import Repeater


def make_repeater(
    callsign: str = "W0ABC",
    frequency: float = 146.520,
    input_freq: float = 146.520,
    state_abbr: str = "MO",
    city: str = "Springfield",
    is_fm: bool = True,
    is_dmr: bool = False,
    dmr_color_code: int | None = None,
    pl_tone: float | None = 100.0,
    distance: float = 50.0,
) -> Repeater:
    """Return a minimal Repeater for testing."""
    return Repeater(
        callsign=callsign,
        frequency=frequency,
        input_freq=input_freq,
        offset=round(input_freq - frequency, 3),
        pl_tone=pl_tone,
        tsq_tone=None,
        city=city,
        county="Test County",
        state="Missouri",
        state_abbr=state_abbr,
        lat=37.2,
        lon=-93.3,
        use="OPEN",
        status="On-air",
        is_fm=is_fm,
        is_dmr=is_dmr,
        is_dstar=False,
        is_fusion=False,
        is_nxdn=False,
        is_p25=False,
        dmr_color_code=dmr_color_code,
        dmr_id=None,
        distance=distance,
    )


@pytest.fixture
def fm_repeater():
    return make_repeater()


@pytest.fixture
def dmr_repeater():
    return make_repeater(
        callsign="W0DMR",
        frequency=444.100,
        input_freq=449.100,
        is_fm=False,
        is_dmr=True,
        dmr_color_code=1,
        pl_tone=None,
    )


@pytest.fixture
def minimal_analog_zone():
    return {
        "name": "Test Zone",
        "tier": "home",
        "state": "MO",
        "channels": [
            {
                "ch_type": "analog",
                "name": "Test FM",
                "rx_freq": 146.520,
                "tx_freq": 146.520,
                "pl_tone": None,
                "tsq_tone": None,
            }
        ],
    }


@pytest.fixture
def minimal_digital_zone():
    return {
        "name": "DMR Zone",
        "tier": "home",
        "state": "MO",
        "channels": [
            {
                "ch_type": "digital",
                "name": "W0DMR Local",
                "rx_freq": 444.100,
                "tx_freq": 449.100,
                "color_code": 1,
                "time_slot": 1,
                "tg_num": 9,
                "tg_name": "Local",
            }
        ],
    }
