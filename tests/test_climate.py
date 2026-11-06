"""Unit conversions and reshaping of the daily climate table."""
import numpy as np
import pandas as pd
import pytest

from tadla.data import climate as c

RAW_DAY = {"tmax": 315.15, "tmin": 298.15, "tmean": 306.15, "tdew": 284.15, "sp": 95_000.0,
           "ssrd": 25.2e6, "te": -0.00024, "swvl1": 0.19, "swvl2": 0.22, "ws10": 2.0,
           "nhours": 24, "rain": 1.5}


def test_wide_to_long_and_units():
    wide = pd.DataFrame({"cell_id": ["X1_Y1", "X2_Y1"]})
    for v, val in RAW_DAY.items():
        for d in (1, 2):
            wide[f"{v}_d{d:02d}"] = val
    long = c.wide_to_long(wide, 2022, 7)
    assert len(long) == 4 and set(long.date.dt.day) == {1, 2}
    phys = c.to_physical(long)
    r = phys.iloc[0]
    assert r.tmax_c == pytest.approx(42.0) and r.tmin_c == pytest.approx(25.0)
    assert r.p_kpa == pytest.approx(95.0)
    assert r.rs_mj == pytest.approx(25.2)
    assert r.et_actual_mm == pytest.approx(0.24)          # evaporation positive
    assert r.u2_ms == pytest.approx(2.0 * 0.748, abs=0.001)
    assert r.ea_kpa == pytest.approx(1.312, abs=0.002)     # e°(11 °C), FAO-56 Annex 2 Table 2.3


def test_monthly_sums_and_means():
    dates = pd.date_range("2022-07-01", periods=31, freq="D")
    d = pd.DataFrame({"cell_id": "X1_Y1", "date": dates, "rain_mm": 1.0, "et0_mm": 5.0,
                      "et_actual_mm": 0.5, "tmean_c": 30.0, "tmax_c": 40.0, "tmin_c": 20.0,
                      "swvl1": 0.2, "swvl2": 0.25, "rs_mj": 25.0, "u2_ms": 1.5, "ea_kpa": 1.2})
    m = c.monthly(d).iloc[0]
    assert m.rain_mm == 31.0 and m.et0_mm == 155.0 and m.et_actual_mm == pytest.approx(15.5)
    assert m.t2m_c == 30.0 and m.n_days == 31


def test_add_et0_matches_fao56_directly():
    from tadla.irrigation import fao56
    daily = pd.DataFrame({"cell_id": ["X1_Y1"], "date": pd.to_datetime(["2022-07-15"]),
                          "tmax_c": [42.0], "tmin_c": [25.0], "ea_kpa": [1.228], "rs_mj": [25.2],
                          "u2_ms": [1.496], "p_kpa": [95.0]})
    cells = pd.DataFrame({"cell_id": ["X1_Y1"], "lat_deg": [32.3], "z_m": [420.0]})
    out = c.add_et0(daily, cells)
    ref, _ = fao56.et0_daily(42.0, 25.0, 1.228, 25.2, 1.496, 95.0, np.deg2rad(32.3), 196, 420.0)
    assert out.et0_mm.iloc[0] == pytest.approx(ref)
    assert 6.0 < ref < 10.0          # hot, dry July day in Tadla: plausible magnitude
