"""A bit more coordinator coverage — handle_result."""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_coord():
    from custom_components.basic_ha.coordinator import BasicHaCoordinator

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test"
    coord = BasicHaCoordinator(hass, entry)
    coord.async_set_updated_data = MagicMock()
    return coord


def test_handle_result_stores_last():
    coord = _make_coord()
    coord.handle_state("dev1", {"value": 1})
    coord.handle_result("dev1", {"action": "ping", "status": "ok"})
    assert coord.data["dev1"]["last_result"]["status"] == "ok"
    assert coord.data["dev1"]["value"] == 1  # previous state kept


def test_make_coord_available():
    coord = _make_coord()
    assert coord.data == {}
