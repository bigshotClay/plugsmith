"""Tests for state-selection refactor: LOWER_48_STATES and estimate_channels_uncapped."""

import pytest

from plugsmith.builder.build_config import DEFAULT_CONFIG, LOWER_48_STATES
from plugsmith.builder.zones import estimate_channels_uncapped
from tests.conftest import make_repeater


# ---------------------------------------------------------------------------
# LOWER_48_STATES constant
# ---------------------------------------------------------------------------

class TestLower48States:
    def test_has_48_states(self):
        assert len(LOWER_48_STATES) == 48

    def test_excludes_alaska(self):
        assert "AK" not in LOWER_48_STATES

    def test_excludes_hawaii(self):
        assert "HI" not in LOWER_48_STATES

    def test_all_two_letter_uppercase(self):
        for code in LOWER_48_STATES:
            assert len(code) == 2 and code.isupper(), f"Invalid code: {code!r}"

    def test_no_duplicates(self):
        assert len(LOWER_48_STATES) == len(set(LOWER_48_STATES))

    def test_contains_common_states(self):
        for state in ("MO", "IL", "TX", "CA", "NY", "FL", "WA", "ME"):
            assert state in LOWER_48_STATES

    def test_default_config_uses_lower_48(self):
        assert DEFAULT_CONFIG["states"] is LOWER_48_STATES


# ---------------------------------------------------------------------------
# estimate_channels_uncapped()
# ---------------------------------------------------------------------------

def _make_state_tiers(*states: str, tier: str = "home") -> dict[str, str]:
    return {s: tier for s in states}


class TestEstimateChannelsUncapped:
    def test_empty_repeaters_returns_simplex_count(self):
        config = {"simplex": {"channels": [{"name": "2m", "freq": 146.52}]}}
        est = estimate_channels_uncapped([], {}, config)
        assert est == 1

    def test_empty_everything_returns_zero(self):
        assert estimate_channels_uncapped([], {}, {}) == 0

    def test_single_fm_repeater(self):
        rpts = [make_repeater(state_abbr="MO", is_fm=True, is_dmr=False)]
        tiers = _make_state_tiers("MO")
        est = estimate_channels_uncapped(rpts, tiers, {})
        assert est == 1

    def test_single_dmr_repeater_counts_tgs(self):
        rpts = [make_repeater(state_abbr="MO", is_fm=False, is_dmr=True)]
        tiers = _make_state_tiers("MO")
        config = {"home_region": {"dmr_talkgroups_per_repeater": 7}}
        est = estimate_channels_uncapped(rpts, tiers, config)
        assert est == 7

    def test_dual_mode_repeater_counted_for_both(self):
        rpts = [make_repeater(state_abbr="MO", is_fm=True, is_dmr=True)]
        tiers = _make_state_tiers("MO")
        config = {"home_region": {"dmr_talkgroups_per_repeater": 7}}
        est = estimate_channels_uncapped(rpts, tiers, config)
        assert est == 1 + 7  # 1 FM + 7 DMR TGs

    def test_repeater_not_in_tiers_excluded(self):
        rpts = [
            make_repeater(state_abbr="MO", is_fm=True),
            make_repeater(state_abbr="WA", is_fm=True),  # WA not in tiers
        ]
        tiers = _make_state_tiers("MO")
        est = estimate_channels_uncapped(rpts, tiers, {})
        assert est == 1  # only MO counts

    def test_multiple_states_summed(self):
        rpts = [
            make_repeater(state_abbr="MO", is_fm=True),
            make_repeater(state_abbr="MO", is_fm=True),
            make_repeater(state_abbr="IL", is_fm=True),
        ]
        tiers = _make_state_tiers("MO", "IL")
        est = estimate_channels_uncapped(rpts, tiers, {})
        assert est == 3

    def test_default_tgs_per_repeater_is_7(self):
        rpts = [make_repeater(state_abbr="MO", is_fm=False, is_dmr=True)]
        tiers = _make_state_tiers("MO")
        # No tgs config → defaults to 7
        est = estimate_channels_uncapped(rpts, tiers, {})
        assert est == 7

    def test_simplex_channels_added(self):
        rpts = [make_repeater(state_abbr="MO", is_fm=True)]
        tiers = _make_state_tiers("MO")
        config = {"simplex": {"channels": [{}, {}, {}]}}  # 3 simplex
        est = estimate_channels_uncapped(rpts, tiers, config)
        assert est == 1 + 3

    def test_state_abbr_unknown_skipped(self):
        rpts = [make_repeater(state_abbr="??", is_fm=True)]
        tiers = _make_state_tiers("MO")
        est = estimate_channels_uncapped(rpts, tiers, {})
        assert est == 0

    def test_large_dataset_is_upper_bound(self):
        """For 5 FM states, estimate should equal number of FM repeaters."""
        rpts = [make_repeater(state_abbr=s, is_fm=True) for s in ["MO", "IL", "KS", "AR", "TN"]]
        tiers = _make_state_tiers("MO", "IL", "KS", "AR", "TN")
        est = estimate_channels_uncapped(rpts, tiers, {})
        assert est == 5
