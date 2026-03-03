"""Unit tests for metadata validation helpers."""

import pytest

from brimfile.metadata import metadata_validation
from brimfile.metadata.metadata_schema import Type, MetadataItem, ScanningStrategy


def test_validate_single_field_normalizes_known_field_name():
    key, value = metadata_validation.validate_single_field(
        Type.Experiment,
        "temperature",
        MetadataItem(22, "C"),
    )

    assert key == "Temperature"
    assert value.value == 22.0
    assert value.units == "C"


def test_validate_single_field_requires_units_for_schema_field():
    with pytest.raises(ValueError, match="requires units"):
        metadata_validation.validate_single_field(
            Type.Experiment,
            "Temperature",
            MetadataItem(22.0),
        )


def test_validate_single_field_raises_typed_error_for_invalid_primitive():
    with pytest.raises(metadata_validation.MetadataValidationError) as exc_info:
        metadata_validation.validate_single_field(
            Type.Experiment,
            "Temperature",
            MetadataItem("hot", "C"),
        )

    assert len(exc_info.value.errors) == 1
    assert exc_info.value.errors[0].field == "Temperature"
    assert "Expected float-like value" in exc_info.value.errors[0].message


def test_validate_single_field_coerces_enum_from_normalized_alias():
    key, value = metadata_validation.validate_single_field(
        Type.Acquisition,
        "Scanning_strategy",
        MetadataItem("line-scanning"),
    )

    assert key == "Scanning_strategy"
    assert value.value == ScanningStrategy.line_scanning


def test_validate_single_field_raises_typed_error_for_invalid_enum():
    with pytest.raises(metadata_validation.MetadataValidationError) as exc_info:
        metadata_validation.validate_single_field(
            Type.Acquisition,
            "Scanning_strategy",
            MetadataItem("totally-unknown-mode"),
        )

    assert len(exc_info.value.errors) == 1
    assert exc_info.value.errors[0].field == "Scanning_strategy"
    assert "is not a valid ScanningStrategy" in exc_info.value.errors[0].message


def test_validate_single_field_rejects_unknown_field_with_close_match():
    with pytest.raises(ValueError, match="Did you mean"):
        metadata_validation.validate_single_field(
            Type.Experiment,
            "Temprature",
            MetadataItem(22.0, "C"),
        )


def test_validate_single_field_allows_custom_field_with_warning():
    with pytest.warns(UserWarning, match="Unknown field 'CompletelyCustomField'"):
        key, value = metadata_validation.validate_single_field(
            Type.Experiment,
            "CompletelyCustomField",
            MetadataItem("abc"),
        )

    assert key == "CompletelyCustomField"
    assert value.value == "abc"
    assert value.units is None
