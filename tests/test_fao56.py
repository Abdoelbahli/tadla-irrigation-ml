"""FAO-56 implementation checked against the worked examples of FAO Irrigation and Drainage Paper 56.

Example 18 (Ch. 4): Brussels, 6 July, 50°48'N, 100 m. Tmax 21.5, Tmin 12.3 °C, RHmax 84 %, RHmin 63 %,
wind 10 km/h at 10 m, Rs = 22.07 MJ m-2 day-1 (from n = 9.25 h). Published results:
u2 2.078, Δ 0.122, γ 0.0666, es 1.997, ea 1.409, Ra 41.09, Rso 30.90, Rns 17.00, Rnl 3.71,
Rn 13.28 MJ m-2 day-1, ET0 = 3.9 mm/day.
Example 8 (Ch. 3): Ra on 3 September at 20°S = 32.2 MJ m-2 day-1.
"""
import numpy as np
import pytest

from tadla.irrigation import fao56 as f

LAT_BRUSSELS = np.deg2rad(50 + 48 / 60)


def test_example_18_daily_et0():
    tmax, tmin, z = 21.5, 12.3, 100.0
    ea = (f.sat_vapour_pressure(tmin) * 0.84 + f.sat_vapour_pressure(tmax) * 0.63) / 2   # Eq. 17
    u2 = f.wind_2m(10 / 3.6, 10)
    p = f.pressure_from_elevation(z)
    et0, t = f.et0_daily(tmax, tmin, ea, 22.07, u2, p, LAT_BRUSSELS, 187, z)
    assert u2 == pytest.approx(2.078, abs=0.002)
    assert p == pytest.approx(100.1, abs=0.05)
    assert ea == pytest.approx(1.409, abs=0.002)
    assert t["es"] == pytest.approx(1.997, abs=0.002)
    assert t["delta"] == pytest.approx(0.122, abs=0.001)
    assert t["gamma"] == pytest.approx(0.0666, abs=0.0001)
    assert t["ra"] == pytest.approx(41.09, abs=0.02)
    assert t["rso"] == pytest.approx(30.90, abs=0.02)
    assert t["rns"] == pytest.approx(17.00, abs=0.02)
    assert t["rnl"] == pytest.approx(3.71, abs=0.02)
    assert t["rn"] == pytest.approx(13.28, abs=0.03)
    assert et0 == pytest.approx(3.9, abs=0.05)


def test_example_8_ra_southern_hemisphere():
    assert f.extraterrestrial_radiation(np.deg2rad(-20.0), 246) == pytest.approx(32.2, abs=0.05)


def test_vectorised_and_no_negative_rnl_factor_above_one():
    rs = np.array([10.0, 40.0])          # second value above Rso -> Rs/Rso clipped to 1
    rso = np.array([20.0, 30.0])
    rnl = f.net_longwave(np.array([20.0, 20.0]), np.array([10.0, 10.0]), np.array([1.0, 1.0]), rs, rso)
    assert rnl.shape == (2,) and rnl[1] == pytest.approx(
        f.net_longwave(20.0, 10.0, 1.0, 30.0, 30.0))
