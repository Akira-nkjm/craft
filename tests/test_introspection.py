"""Unit tests for core.introspection summary functions."""

from unittest.mock import MagicMock, patch

from core.introspection import (
    AnalysisSummary,
    ComponentSummary,
    ConfigSummary,
    list_analyses_summary,
    list_components_summary,
    list_configs_summary,
)


def _mock_comp(
    system="power",
    name="battery",
    plural="batteries",
    cardinality="multi",
    traits=("MultiInstance",),
):
    m = MagicMock()
    m.system = system
    m.name = name
    m.plural = plural
    m.cardinality = cardinality
    m.traits = traits
    return m


def _mock_cfg(system="power", name="power_budget", plural="power_budgets", cardinality="single"):
    m = MagicMock()
    m.system = system
    m.name = name
    m.plural = plural
    m.cardinality = cardinality
    return m


def _mock_analysis(system="power", name="total_pdm_power_w", verify=False, desc="PDM power total"):
    m = MagicMock()
    m.system = system
    m.name = name
    m.verify = verify
    m.desc = desc
    return m


# ─── list_components_summary ─────────────────────────────────────────


def test_list_components_summary_returns_component_summaries():
    comp = _mock_comp()

    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.components.return_value = [comp]
        result = list_components_summary()

    assert len(result) == 1
    s = result[0]
    assert isinstance(s, ComponentSummary)
    assert s.system == "power"
    assert s.name == "battery"
    assert s.plural == "batteries"
    assert s.cardinality == "multi"
    assert s.traits == ("MultiInstance",)


def test_list_components_summary_filters_by_system():
    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.components.return_value = []
        list_components_summary(system="power")

    mock_reg.components.assert_called_once_with(system="power")


def test_list_components_summary_no_filter_passes_none():
    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.components.return_value = []
        list_components_summary()

    mock_reg.components.assert_called_once_with(system=None)


def test_list_components_summary_multiple_entries():
    comps = [
        _mock_comp(system="power", name="battery"),
        _mock_comp(system="cdh", name="obc", plural="obcs", cardinality="single", traits=()),
    ]

    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.components.return_value = comps
        result = list_components_summary()

    assert len(result) == 2
    names = {s.name for s in result}
    assert names == {"battery", "obc"}


# ─── list_configs_summary ─────────────────────────────────────────────


def test_list_configs_summary_returns_config_summaries():
    cfg = _mock_cfg()

    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.configs.return_value = [cfg]
        result = list_configs_summary()

    assert len(result) == 1
    s = result[0]
    assert isinstance(s, ConfigSummary)
    assert s.system == "power"
    assert s.name == "power_budget"
    assert s.plural == "power_budgets"
    assert s.cardinality == "single"


def test_list_configs_summary_filters_by_system():
    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.configs.return_value = []
        list_configs_summary(system="mission")

    mock_reg.configs.assert_called_once_with(system="mission")


def test_list_configs_summary_empty_registry():
    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.configs.return_value = []
        result = list_configs_summary()

    assert result == []


# ─── list_analyses_summary ───────────────────────────────────────────


def test_list_analyses_summary_returns_analysis_summaries():
    analysis = _mock_analysis()

    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.analyses.return_value = [analysis]
        result = list_analyses_summary()

    assert len(result) == 1
    s = result[0]
    assert isinstance(s, AnalysisSummary)
    assert s.system == "power"
    assert s.name == "total_pdm_power_w"
    assert s.verify is False
    assert s.desc == "PDM power total"


def test_list_analyses_summary_verify_flag_preserved():
    analyses = [
        _mock_analysis(name="verify_capacity", verify=True, desc="capacity check"),
        _mock_analysis(name="total_power", verify=False, desc=None),
    ]

    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.analyses.return_value = analyses
        result = list_analyses_summary()

    verify_flags = {s.name: s.verify for s in result}
    assert verify_flags["verify_capacity"] is True
    assert verify_flags["total_power"] is False


def test_list_analyses_summary_filters_by_system():
    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.analyses.return_value = []
        list_analyses_summary(system="power")

    mock_reg.analyses.assert_called_once_with(system="power")


def test_list_analyses_summary_none_system_preserved():
    analysis = _mock_analysis(system=None)

    with patch("core.introspection.default_registry") as mock_reg:
        mock_reg.analyses.return_value = [analysis]
        result = list_analyses_summary()

    assert result[0].system is None
