"""strings.json against the entities and enums that need it.

``script/generate_strings.py`` writes both translation files from the
library's enums. These tests fail if someone edits an entity without
re-running it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from custom_components.brink_flair import (
    binary_sensor,
    button,
    number,
    select,
    sensor,
)
from custom_components.brink_flair.const import (
    DOMAIN,
    TRANSPORT_GATEWAY,
    TRANSPORT_SERIAL,
    TRANSPORT_SERIAL_SERVER,
)

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "brink_flair"


@pytest.fixture(scope="module")
def strings() -> dict[str, Any]:
    """The integration's strings.json."""
    return json.loads((COMPONENT / "strings.json").read_text())


def test_the_two_translation_files_agree(strings: dict[str, Any]) -> None:
    """English is generated from strings.json, so they are the same file."""
    english = json.loads((COMPONENT / "translations" / "en.json").read_text())
    assert english == strings


@pytest.mark.parametrize(
    ("platform", "descriptions"),
    [
        ("sensor", sensor.ALL_SENSORS + sensor.TOTAL_SENSORS),
        ("binary_sensor", binary_sensor.BINARY_SENSORS),
        ("button", button.BUTTONS),
        ("select", select.SELECTS),
    ],
)
def test_every_entity_has_a_name(
    strings: dict[str, Any], platform: str, descriptions: tuple[Any, ...]
) -> None:
    translations = strings["entity"][platform]
    for description in descriptions:
        key = description.translation_key
        assert key in translations, f"{platform}.{key} has no name in strings.json"
        assert translations[key]["name"]


@pytest.mark.parametrize(
    ("platform", "descriptions"),
    [
        ("sensor", sensor.ALL_SENSORS),
        ("select", select.SELECTS),
    ],
)
def test_every_option_has_a_state_label(
    strings: dict[str, Any], platform: str, descriptions: tuple[Any, ...]
) -> None:
    """An option with no label shows as a raw enum name in the UI."""
    translations = strings["entity"][platform]
    for description in descriptions:
        if not description.options:
            continue
        labels = translations[description.translation_key].get("state", {})
        assert set(description.options) == set(labels), description.translation_key


def test_the_placeholders_the_repeated_entities_pass_are_in_their_names(
    strings: dict[str, Any],
) -> None:
    """A name with {index} needs the placeholder, and one without must not."""
    for platform, descriptions in (
        ("sensor", sensor.ALL_SENSORS),
        ("binary_sensor", binary_sensor.BINARY_SENSORS),
    ):
        for description in descriptions:
            name = strings["entity"][platform][description.translation_key]["name"]
            placeholders = description.translation_placeholders or {}
            assert ("{index}" in name) == ("index" in placeholders), description.key


def test_the_number_has_a_name(strings: dict[str, Any]) -> None:
    """It is one entity, so it declares its key on the class.

    The fan needs no entry at all: it is the appliance's only ventilation, so
    it carries the device's own name.
    """
    assert strings["entity"]["number"][number.TRANSLATION_KEY]["name"]


def test_the_write_failure_message_takes_the_error(strings: dict[str, Any]) -> None:
    """Every platform raises it through ``entity.write_error``."""
    message = strings["exceptions"]["write_failed"]["message"]
    assert "{error}" in message


def test_the_config_flow_errors_are_the_ones_the_flow_raises(
    strings: dict[str, Any],
) -> None:
    assert set(strings["config"]["error"]) == {"cannot_connect", "link_conflict"}


def test_every_way_of_reaching_the_appliance_is_offered_and_described(
    strings: dict[str, Any],
) -> None:
    """A menu entry with no step behind it dead-ends the flow."""
    transports = {TRANSPORT_SERIAL, TRANSPORT_SERIAL_SERVER, TRANSPORT_GATEWAY}
    step = strings["config"]["step"]

    assert set(step["user"]["menu_options"]) == transports
    assert transports <= set(step)
    for transport in transports:
        assert step[transport]["description"]


def test_the_manifest(strings: dict[str, Any]) -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    # `async_get_unit` lives in the modbus integration, and modbus-connection
    # comes in as its requirement.
    assert manifest["dependencies"] == ["modbus"]
    # The library is vendored, so nothing is installed from PyPI.
    assert manifest["requirements"] == []
