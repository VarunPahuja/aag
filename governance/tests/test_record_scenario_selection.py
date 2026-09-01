"""`--scenario` narrows the recording run.

Recording is the one thing in this lane that costs quota, so a partial run has to be a
subset of the full run and nothing else — same prompts, same cache keys, same order.
"""

from __future__ import annotations

import pytest

from governance.record import select_scenarios
from governance.scenarios import SCENARIOS


def test_no_names_means_every_scenario():
    assert select_scenarios(None) == tuple(SCENARIOS)
    assert select_scenarios([]) == tuple(SCENARIOS)


def test_one_name_selects_one():
    chosen = select_scenarios(["thin_sample"])

    assert [s.name for s in chosen] == ["thin_sample"]


def test_an_unknown_name_raises_rather_than_recording_nothing():
    """A typo must not look like "everything was already recorded"."""
    with pytest.raises(ValueError, match="unknown scenario"):
        select_scenarios(["thin_sampel"])

    with pytest.raises(ValueError, match="unknown scenario"):
        select_scenarios(["thin_sample", "nope"])


def test_selection_keeps_scenarios_order_not_argument_order():
    """A subset run must be a slice of the full run, so ordering cannot drift."""
    forwards = select_scenarios(["healthy_increase", "at_ceiling"])
    backwards = select_scenarios(["at_ceiling", "healthy_increase"])

    assert forwards == backwards
    assert [s.name for s in forwards] == [
        s.name for s in SCENARIOS if s.name in {"healthy_increase", "at_ceiling"}
    ]


def test_a_repeated_name_is_recorded_once():
    """Repeating `--scenario x` must not double the quota spend."""
    assert len(select_scenarios(["thin_sample", "thin_sample"])) == 1
