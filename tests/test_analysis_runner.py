"""Unit tests for core/analysis_runner.py."""

import pytest

from core.discovery import discover_systems

# Populate the registry (analyses, components, configs) before any test runs.
# API/MCP tests handle this via TestClient lifespan or build_server(); direct
# runner tests must do it explicitly.
discover_systems()

from core.analysis_runner import (  # noqa: E402
    AnalysisArgumentError,
    AnalysisNotFound,
    AnalysisRunResult,
    extract_analysis_value,
    run_analysis,
)

# ─── ad-hoc (battery_eol_capacity, cache=True, system=None) ──────────


def test_run_adhoc_returns_correct_value():
    result = run_analysis(None, "battery_eol_capacity", {"initial_capacity_wh": 100.0})
    assert isinstance(result, AnalysisRunResult)
    assert result.name == "battery_eol_capacity"
    assert result.system is None
    # default years=5, cycles_per_day=1: 5*365*1=1825 → 0.1825 → 100*(1-0.1825)=81.75
    assert abs(result.value - 81.75) < 0.01


def test_run_adhoc_cache_miss_then_hit(clean_generated_dir):
    payload = {"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 2.0}
    first = run_analysis(None, "battery_eol_capacity", payload)
    second = run_analysis(None, "battery_eol_capacity", payload)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert first.value == second.value


def test_run_adhoc_use_cache_false_bypasses_cache(clean_generated_dir):
    payload = {"initial_capacity_wh": 100.0, "years": 5.0, "cycles_per_day": 1.0}
    first = run_analysis(None, "battery_eol_capacity", payload)
    # prime cache
    assert first.cache_hit is False

    # use_cache=False: should recompute (not read from cache) and not store
    second = run_analysis(None, "battery_eol_capacity", payload, use_cache=False)
    assert second.cache_hit is False
    assert second.value == first.value

    # cache was not updated by use_cache=False call; original entry still exists
    third = run_analysis(None, "battery_eol_capacity", payload)
    assert third.cache_hit is True


def test_run_adhoc_different_inputs_both_miss(clean_generated_dir):
    r1 = run_analysis(None, "battery_eol_capacity", {"initial_capacity_wh": 100.0, "years": 3.0})
    r2 = run_analysis(None, "battery_eol_capacity", {"initial_capacity_wh": 100.0, "years": 4.0})
    assert r1.cache_hit is False
    assert r2.cache_hit is False


def test_run_adhoc_argument_error_raises():
    with pytest.raises(AnalysisArgumentError):
        # unexpected keyword argument triggers TypeError in bind_partial
        run_analysis(
            None,
            "battery_eol_capacity",
            {"initial_capacity_wh": 100.0, "unexpected_param": "bad"},
        )


def test_run_analysis_not_found_raises():
    with pytest.raises(AnalysisNotFound):
        run_analysis(None, "nonexistent_analysis", {})

    with pytest.raises(AnalysisNotFound):
        run_analysis("power", "nonexistent_analysis", {})


# ─── veriq-backed analyses ────────────────────────────────────────────


def test_run_veriq_calculation(clean_generated_dir):
    result = run_analysis("power", "total_pdm_power_w", {})
    assert result.name == "total_pdm_power_w"
    assert result.system == "power"
    assert result.verify is False
    assert result.cache_hit is None  # veriq path has no cache
    assert result.value == 8.0


def test_run_veriq_verification(clean_generated_dir):
    result = run_analysis("power", "verify_battery_capacity", {})
    assert result.verify is True
    assert result.cache_hit is None
    assert result.value is True


# ─── extract_analysis_value ──────────────────────────────────────────


def test_extract_analysis_value_calculation(clean_generated_dir):
    from core.pipeline.veriq_project import evaluate_project_from_merged

    _, vq_result = evaluate_project_from_merged()
    value = extract_analysis_value(vq_result, "power", "total_pdm_power_w", verify=False)
    assert value == 8.0


def test_extract_analysis_value_verification(clean_generated_dir):
    from core.pipeline.veriq_project import evaluate_project_from_merged

    _, vq_result = evaluate_project_from_merged()
    value = extract_analysis_value(vq_result, "power", "verify_battery_capacity", verify=True)
    assert value is True


def test_extract_analysis_value_missing_scope(clean_generated_dir):
    from core.pipeline.veriq_project import evaluate_project_from_merged

    _, vq_result = evaluate_project_from_merged()
    value = extract_analysis_value(vq_result, "nonexistent_scope", "some_analysis", verify=False)
    assert value is None


def test_extract_analysis_value_missing_node(clean_generated_dir):
    from core.pipeline.veriq_project import evaluate_project_from_merged

    _, vq_result = evaluate_project_from_merged()
    value = extract_analysis_value(vq_result, "power", "nonexistent_node", verify=False)
    assert value is None
