"""pipeline.py is pure composition/dispatch - these tests check it
routes to and shapes output from the already-tested underlying
functions correctly, not indicator/signal correctness itself (that's
covered by each module's own tests)."""
import pandas as pd

from tests.fixtures import synthetic_series_df
from xauusd_indicators.alarms.extremes import evaluate_extremes
from xauusd_indicators.indicators.adx import adx
from xauusd_indicators.indicators.stochastic import stochastic
from xauusd_indicators.pipeline import Variant, compute_all_indicators, entry_signal, exit_fired
from xauusd_indicators.signals.section2 import entry_signal as section2_entry
from xauusd_indicators.types import PositionState, Signal


def test_compute_all_indicators_adds_expected_columns_without_mutating_input():
    df = synthetic_series_df(n=250)
    original_columns = list(df.columns)
    result = compute_all_indicators(df)

    expected_new_columns = {
        "atr",
        "volatility_ratio",
        "adx",
        "rvi",
        "rvi_trigger",
        "roc",
        "obv",
        "obv_slope",
        "macd_histogram",
        "parabolic_sar",
        "parabolic_sar_direction",
        "stochastic_k",
        "stochastic_d",
        "force_index",
        "extreme_alarms",
    }
    assert expected_new_columns.issubset(set(result.columns))
    assert list(df.columns) == original_columns, "compute_all_indicators must not mutate its input"
    assert len(result) == len(df)


def test_compute_all_indicators_adx_column_matches_calling_adx_directly():
    df = synthetic_series_df(n=100)
    result = compute_all_indicators(df)
    expected = adx(df)
    pd.testing.assert_series_equal(result["adx"], expected, check_names=False)


def test_compute_all_indicators_extreme_alarms_column_matches_calling_extremes_directly():
    df = synthetic_series_df(n=100)
    result = compute_all_indicators(df)
    expected_k, expected_d = stochastic(df)
    pd.testing.assert_series_equal(result["stochastic_k"], expected_k, check_names=False)
    pd.testing.assert_series_equal(result["stochastic_d"], expected_d, check_names=False)
    for i in range(len(df)):
        assert set(result["extreme_alarms"].iloc[i]) == set(
            evaluate_extremes(
                None if pd.isna(expected_k.iloc[i]) else expected_k.iloc[i],
                None if pd.isna(expected_d.iloc[i]) else expected_d.iloc[i],
                None if pd.isna(result["force_index"].iloc[i]) else result["force_index"].iloc[i],
            )
        )


def test_entry_signal_dispatches_to_section2_for_variant_section_2():
    df = synthetic_series_df(n=250)
    via_pipeline = entry_signal(df, Variant.SECTION_2)
    direct = section2_entry(df)
    for a, b in zip(via_pipeline, direct):
        assert a == b


def test_entry_signal_section_7_matches_section_2_entry():
    # Section 7 uses the same entry as Section 2 (report: "same entry as
    # Section 2") - the pipeline should route both to the same result.
    df = synthetic_series_df(n=250)
    section2_result = entry_signal(df, Variant.SECTION_2)
    section7_result = entry_signal(df, Variant.SECTION_7)
    for a, b in zip(section2_result, section7_result):
        assert a == b


def test_exit_fired_dispatches_correctly_per_variant():
    df = synthetic_series_df(n=10)
    position = PositionState(direction=Signal.LONG, entry_price=df["close"].iloc[0], entry_bar_index=0)
    no_trigger = pd.Series([None] * len(df))
    # Just checks it runs and returns a bool for every variant - the
    # underlying exit logic itself is tested in test_signals_section*.py.
    for variant in Variant:
        result = exit_fired(df, variant, position, current_bar_index=5, atr_at_entry=1.0, rvi_triggers=no_trigger)
        assert isinstance(result, bool)
