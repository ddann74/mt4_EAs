"""Extreme-alarm decision logic: evaluate_extremes() covers every branch
(each alarm firing alone, both stochastic lines required together, no
false fire on a partial/None reading), then extremes()/extremes_update()
are checked to agree with each other and with evaluate_extremes() on real
computed indicator values from a synthetic series - not just engineered
numbers in isolation."""
import math

from tests.fixtures import df_to_bars, synthetic_series_df
from xauusd_indicators.alarms.extremes import (
    ExtremeAlarm,
    ExtremesState,
    evaluate_extremes,
    extremes,
    extremes_update,
)


def test_stochastic_overbought_requires_both_k_and_d():
    # %K alone past 90 - %D still inside the band - should NOT fire
    # (user's explicit choice: both lines must agree).
    assert evaluate_extremes(95.0, 85.0, 0.0) == []
    # %D alone past 90 - %K still inside the band - should NOT fire either.
    assert evaluate_extremes(85.0, 95.0, 0.0) == []
    # Both past 90 - fires.
    assert evaluate_extremes(95.0, 92.0, 0.0) == [ExtremeAlarm.STOCHASTIC_OVERBOUGHT]


def test_stochastic_oversold_requires_both_k_and_d():
    assert evaluate_extremes(5.0, 15.0, 0.0) == []
    assert evaluate_extremes(15.0, 5.0, 0.0) == []
    assert evaluate_extremes(5.0, 2.0, 0.0) == [ExtremeAlarm.STOCHASTIC_OVERSOLD]


def test_stochastic_exactly_at_threshold_does_not_fire():
    # ">" / "<" per the user's stated limits ("over 90 and under 10"),
    # not ">=" / "<=" - landing exactly on the line is not "over" it.
    assert evaluate_extremes(90.0, 90.0, 0.0) == []
    assert evaluate_extremes(10.0, 10.0, 0.0) == []


def test_force_index_high_and_low():
    assert evaluate_extremes(50.0, 50.0, 71.0) == [ExtremeAlarm.FORCE_INDEX_HIGH]
    assert evaluate_extremes(50.0, 50.0, -71.0) == [ExtremeAlarm.FORCE_INDEX_LOW]
    assert evaluate_extremes(50.0, 50.0, 70.0) == [], "exactly at the threshold should not fire"
    assert evaluate_extremes(50.0, 50.0, -70.0) == [], "exactly at the threshold should not fire"
    assert evaluate_extremes(50.0, 50.0, 0.0) == []


def test_both_stochastic_and_force_index_can_fire_together():
    result = evaluate_extremes(95.0, 92.0, 80.0)
    assert set(result) == {ExtremeAlarm.STOCHASTIC_OVERBOUGHT, ExtremeAlarm.FORCE_INDEX_HIGH}


def test_none_inputs_never_fire():
    assert evaluate_extremes(None, None, None) == []
    assert evaluate_extremes(95.0, None, None) == [], "a missing %D (still warming up) should not fire on %K alone"
    assert evaluate_extremes(None, 95.0, None) == []


def test_extremes_dataframe_and_incremental_agree_with_each_other_and_with_evaluate_extremes():
    df = synthetic_series_df(n=150)
    df_result = extremes(df)
    bars = df_to_bars(df)

    state = ExtremesState()
    incremental_alarms = []
    for bar in bars:
        alarms, state = extremes_update(state, bar)
        incremental_alarms.append(alarms)

    # Not asserting a *specific* alarm fires anywhere in this series -
    # synthetic_series_df's random walk has no guarantee of ever reaching
    # |70|/beyond-90/under-10. What this proves instead: the dataframe
    # path, the incremental path, and the pure decision function all agree
    # with each other on every bar of real computed data, warmup region
    # included - not just on the hand-picked numbers in the tests above,
    # which prove each alarm's condition actually fires when engineered to.
    for i in range(len(bars)):
        vectorized_alarms = df_result["alarms"].iloc[i]
        assert set(vectorized_alarms) == set(incremental_alarms[i]), f"bar {i}: vectorized vs incremental mismatch"

        k = df_result["stochastic_k"].iloc[i]
        d = df_result["stochastic_d"].iloc[i]
        fi = df_result["force_index"].iloc[i]
        direct = evaluate_extremes(
            None if math.isnan(k) else k,
            None if math.isnan(d) else d,
            None if math.isnan(fi) else fi,
        )
        assert set(direct) == set(vectorized_alarms), f"bar {i}: direct evaluate_extremes() mismatch"
