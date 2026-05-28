"""Unit tests for schema._subclass_helpers.auto_pluralize edge cases."""

from craft.schema._subclass_helpers import auto_pluralize

# ─── basic cases (regression) ────────────────────────────────────────


def test_auto_pluralize_simple_noun():
    assert auto_pluralize("Battery") == "batteries"


def test_auto_pluralize_acronym():
    assert auto_pluralize("OBC") == "obcs"


def test_auto_pluralize_camel_case():
    assert auto_pluralize("SolarPanel") == "solar_panels"


# ─── -y ending rules ─────────────────────────────────────────────────


def test_auto_pluralize_consonant_y_to_ies():
    # ends with consonant + y → drop y, add ies
    assert auto_pluralize("Battery") == "batteries"


def test_auto_pluralize_vowel_y_kept():
    # ends with ay/ey/oy/uy → just add s
    assert auto_pluralize("Relay") == "relays"
    assert auto_pluralize("Trolley") == "trolleys"


# ─── -ch ending ──────────────────────────────────────────────────────


def test_auto_pluralize_ch_ending_simple():
    # "Notch" → "notch" → "notches"
    assert auto_pluralize("Notch") == "notches"


def test_auto_pluralize_ch_ending_compound():
    # "HeatPatch" → "heat_patch" → "heat_patches"
    assert auto_pluralize("HeatPatch") == "heat_patches"


def test_auto_pluralize_ch_ending_short():
    # "Batch" → "batch" → "batches"
    assert auto_pluralize("Batch") == "batches"


# ─── -sh ending ──────────────────────────────────────────────────────


def test_auto_pluralize_sh_ending_simple():
    # "Flash" → "flash" → "flashes"
    assert auto_pluralize("Flash") == "flashes"


def test_auto_pluralize_sh_ending_compound():
    # "PowerFlash" → "power_flash" → "power_flashes"
    assert auto_pluralize("PowerFlash") == "power_flashes"


def test_auto_pluralize_sh_ending_short():
    # "Dish" → "dish" → "dishes"
    assert auto_pluralize("Dish") == "dishes"


# ─── -x ending ───────────────────────────────────────────────────────


def test_auto_pluralize_x_ending_simple():
    # "Flux" → "flux" → "fluxes"
    assert auto_pluralize("Flux") == "fluxes"


def test_auto_pluralize_x_ending_compound():
    # "DataMux" → "data_mux" → "data_muxes"
    assert auto_pluralize("DataMux") == "data_muxes"


def test_auto_pluralize_x_ending_short():
    # "Box" → "box" → "boxes"
    assert auto_pluralize("Box") == "boxes"
