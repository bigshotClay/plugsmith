"""Tests for plugsmith.builder.export."""

from __future__ import annotations

import csv
import os

import pytest
import yaml

from plugsmith.builder.export import write_qdmr_yaml, write_anytone_csv, write_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_codeplug(**overrides) -> dict:
    cp = {
        "version": "0.12.0",
        "channels": [],
        "zones": [],
        "contacts": [],
    }
    cp.update(overrides)
    return cp


def _analog_channel(name: str = "Test FM", rx: float = 146.520, tx: float = 146.520) -> dict:
    return {
        "analog": {
            "name": name,
            "rxFrequency": rx,
            "txFrequency": tx,
        }
    }


def _analog_channel_with_tones(name: str = "Toned FM", rx: float = 146.520, tx: float = 147.120) -> dict:
    return {
        "analog": {
            "name": name,
            "rxFrequency": rx,
            "txFrequency": tx,
            "rxTone": {"ctcss": 100.0},
            "txTone": {"ctcss": 100.0},
        }
    }


def _digital_channel(name: str = "Test DMR", rx: float = 444.100, tx: float = 449.100) -> dict:
    return {
        "digital": {
            "name": name,
            "rxFrequency": rx,
            "txFrequency": tx,
            "colorCode": 1,
            "timeSlot": "TS1",
            "contact": "Local",
        }
    }


def _zone(name: str = "Test Zone", channels: list | None = None) -> dict:
    return {"name": name, "A": channels or []}


# ---------------------------------------------------------------------------
# write_qdmr_yaml
# ---------------------------------------------------------------------------


class TestWriteQdmrYaml:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "out.yaml")
        cp = _minimal_codeplug()
        write_qdmr_yaml(cp, path)
        assert os.path.exists(path)

    def test_file_is_valid_yaml(self, tmp_path):
        path = str(tmp_path / "out.yaml")
        cp = _minimal_codeplug(version="0.12.0")
        write_qdmr_yaml(cp, path)
        with open(path) as f:
            loaded = yaml.safe_load(f)
        assert loaded["version"] == "0.12.0"

    def test_channels_round_trip(self, tmp_path):
        path = str(tmp_path / "out.yaml")
        cp = _minimal_codeplug(channels=[_analog_channel(), _digital_channel()])
        write_qdmr_yaml(cp, path)
        with open(path) as f:
            loaded = yaml.safe_load(f)
        assert len(loaded["channels"]) == 2

    def test_unicode_content_preserved(self, tmp_path):
        path = str(tmp_path / "out.yaml")
        cp = _minimal_codeplug()
        cp["settings"] = {"introLine1": "W0RRK — test"}
        write_qdmr_yaml(cp, path)
        with open(path) as f:
            content = f.read()
        assert "W0RRK" in content


# ---------------------------------------------------------------------------
# write_anytone_csv
# ---------------------------------------------------------------------------


class TestWriteAnytoneCsv:
    def test_creates_channel_csv(self, tmp_path):
        cp = _minimal_codeplug(channels=[_analog_channel()])
        write_anytone_csv(cp, str(tmp_path / "csv_out"))
        assert os.path.exists(tmp_path / "csv_out" / "Channel.csv")

    def test_creates_output_dir(self, tmp_path):
        outdir = str(tmp_path / "nested" / "csv")
        cp = _minimal_codeplug(channels=[_analog_channel()])
        write_anytone_csv(cp, outdir)
        assert os.path.isdir(outdir)

    def test_header_row_written(self, tmp_path):
        cp = _minimal_codeplug(channels=[_analog_channel()])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert "Channel Name" in header
        assert "Channel Type" in header

    def test_analog_channel_row(self, tmp_path):
        cp = _minimal_codeplug(channels=[_analog_channel("2m Simplex", 146.520, 146.520)])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            next(reader)  # header
            row = next(reader)
        assert row[1] == "2m Simplex"
        assert row[4] == "A-Analog"
        assert "146.52000" in row[2]

    def test_analog_channel_ctcss_tones(self, tmp_path):
        cp = _minimal_codeplug(channels=[_analog_channel_with_tones()])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        assert row[7] == "100.0"   # decode
        assert row[8] == "100.0"   # encode

    def test_analog_channel_no_ctcss_empty(self, tmp_path):
        cp = _minimal_codeplug(channels=[_analog_channel()])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        assert row[7] == ""
        assert row[8] == ""

    def test_digital_channel_row(self, tmp_path):
        cp = _minimal_codeplug(channels=[_digital_channel("W0TST Local")])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        assert row[1] == "W0TST Local"
        assert row[4] == "D-Digital"
        assert row[11] == "1"       # color code
        assert row[12] == "1"       # time slot (TS1 → 1)

    def test_row_numbers_sequential(self, tmp_path):
        cp = _minimal_codeplug(channels=[_analog_channel("FM1"), _digital_channel("DMR1")])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)
        assert rows[0][0] == "1"
        assert rows[1][0] == "2"

    def test_empty_channels_no_data_rows(self, tmp_path):
        cp = _minimal_codeplug(channels=[])
        write_anytone_csv(cp, str(tmp_path))
        with open(tmp_path / "Channel.csv") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 1  # header only


# ---------------------------------------------------------------------------
# write_summary
# ---------------------------------------------------------------------------


class TestWriteSummary:
    def _make_codeplug(self, n_analog: int = 2, n_digital: int = 1) -> dict:
        channels = []
        for i in range(n_analog):
            channels.append({"analog": {"name": f"FM{i}", "rxFrequency": 146.520, "txFrequency": 146.520}})
        for i in range(n_digital):
            channels.append({"digital": {"name": f"DMR{i}", "rxFrequency": 444.1, "txFrequency": 449.1}})
        zones = [{"name": f"Zone{i}", "A": ["ch1"] * (i + 1)} for i in range(2)]
        contacts = [{"name": f"TG{i}"} for i in range(5)]
        return {"channels": channels, "zones": zones, "contacts": contacts}

    def test_returns_string(self):
        cp = self._make_codeplug()
        result = write_summary(cp)
        assert isinstance(result, str)

    def test_contains_channel_counts(self):
        cp = self._make_codeplug(n_analog=3, n_digital=2)
        result = write_summary(cp)
        assert "3" in result
        assert "2" in result

    def test_contains_zone_count(self):
        cp = self._make_codeplug()
        result = write_summary(cp)
        assert "2" in result  # 2 zones

    def test_contains_contact_count(self):
        cp = self._make_codeplug()
        result = write_summary(cp)
        assert "5" in result  # 5 contacts

    def test_writes_to_file(self, tmp_path):
        path = str(tmp_path / "summary.txt")
        cp = self._make_codeplug()
        result = write_summary(cp, output_path=path)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert content == result

    def test_no_output_path_returns_string_only(self, tmp_path):
        cp = self._make_codeplug()
        result = write_summary(cp)  # no output_path
        assert result  # non-empty
        # No file created in cwd for this
        assert isinstance(result, str)

    def test_with_zone_specs_shows_tiers(self):
        cp = self._make_codeplug()
        zone_specs = [
            {"tier": "home", "state": "MO", "channels": [1, 2, 3]},
            {"tier": "adjacent", "state": "KS", "channels": [1]},
            {"tier": "shallow", "state": "", "channels": []},
        ]
        result = write_summary(cp, zone_specs=zone_specs)
        assert "MO" in result
        assert "KS" in result
        assert "Home" in result or "home" in result

    def test_with_zone_specs_states_covered(self):
        cp = self._make_codeplug()
        zone_specs = [
            {"tier": "home", "state": "MO", "channels": []},
            {"tier": "home", "state": "IL", "channels": []},
            {"tier": "adjacent", "state": "", "channels": []},  # empty state ignored
        ]
        result = write_summary(cp, zone_specs=zone_specs)
        assert "2" in result   # 2 states with non-empty state abbr

    def test_header_present(self):
        cp = self._make_codeplug()
        result = write_summary(cp)
        assert "CODEPLUG" in result.upper()
