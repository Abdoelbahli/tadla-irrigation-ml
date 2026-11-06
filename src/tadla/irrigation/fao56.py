"""FAO-56 Penman-Monteith reference evapotranspiration (daily time step).

Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). Crop evapotranspiration — Guidelines for
computing crop water requirements. FAO Irrigation and Drainage Paper 56. Equation numbers below
refer to that paper. All functions are vectorised (numpy arrays or scalars).

Units: temperature °C, pressure kPa, vapour pressure kPa, radiation MJ m-2 day-1, wind m s-1,
elevation m, latitude radians, ET0 mm day-1.
"""
from __future__ import annotations

import numpy as np

GSC = 0.0820            # solar constant, MJ m-2 min-1
SIGMA = 4.903e-9        # Stefan-Boltzmann constant, MJ K-4 m-2 day-1
ALBEDO_REF = 0.23       # albedo of the hypothetical grass reference crop
KELVIN = 273.16         # FAO-56 uses 273.16 in the radiation terms (Eq. 39)


def sat_vapour_pressure(t):
    """e°(T), kPa (Eq. 11)."""
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def slope_svp(t):
    """Δ, slope of the saturation vapour pressure curve at T, kPa °C-1 (Eq. 13)."""
    return 4098.0 * sat_vapour_pressure(t) / (t + 237.3) ** 2


def pressure_from_elevation(z):
    """Atmospheric pressure from elevation, kPa (Eq. 7). Used only when no pressure data."""
    return 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26


def psychrometric_constant(p_kpa):
    """γ, kPa °C-1 (Eq. 8)."""
    return 0.665e-3 * p_kpa


def wind_2m(u_z, z_m=10.0):
    """Wind speed at 2 m from speed measured at z_m metres (Eq. 47)."""
    return u_z * 4.87 / np.log(67.8 * z_m - 5.42)


def extraterrestrial_radiation(lat_rad, doy):
    """Ra, MJ m-2 day-1 (Eqs. 21, 23, 24, 25)."""
    doy = np.asarray(doy, dtype=float)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0)
    decl = 0.409 * np.sin(2.0 * np.pi * doy / 365.0 - 1.39)
    ws = np.arccos(np.clip(-np.tan(lat_rad) * np.tan(decl), -1.0, 1.0))
    return (24.0 * 60.0 / np.pi) * GSC * dr * (
        ws * np.sin(lat_rad) * np.sin(decl) + np.cos(lat_rad) * np.cos(decl) * np.sin(ws))


def clear_sky_radiation(ra, z):
    """Rso, MJ m-2 day-1 (Eq. 37)."""
    return (0.75 + 2e-5 * z) * ra


def net_shortwave(rs, albedo=ALBEDO_REF):
    """Rns, MJ m-2 day-1 (Eq. 38)."""
    return (1.0 - albedo) * rs


def net_longwave(tmax, tmin, ea, rs, rso):
    """Rnl, MJ m-2 day-1 (Eq. 39). Rs/Rso is limited to 1.0 as in FAO-56."""
    rel = np.clip(rs / rso, 0.0, 1.0)
    tk4 = (np.power(tmax + KELVIN, 4) + np.power(tmin + KELVIN, 4)) / 2.0
    return SIGMA * tk4 * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rel - 0.35)


def et0_daily(tmax, tmin, ea, rs, u2, p_kpa, lat_rad, doy, z, g=0.0):
    """Daily FAO-56 Penman-Monteith ET0, mm day-1 (Eq. 6).

    tmax, tmin : daily max / min air temperature at 2 m, °C
    ea         : actual vapour pressure, kPa (e.g. e°(Tdew), Eq. 14)
    rs         : incoming shortwave radiation, MJ m-2 day-1
    u2         : mean daily wind speed at 2 m, m s-1
    p_kpa      : atmospheric pressure, kPa
    lat_rad    : latitude, radians;  doy: day of year;  z: elevation, m (for Rso)
    g          : soil heat flux, MJ m-2 day-1 (≈ 0 for daily steps, Eq. 42)
    Returns ET0 and a dict with the intermediate terms (for checks).
    """
    tmean = (tmax + tmin) / 2.0
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2.0   # Eq. 12
    delta = slope_svp(tmean)
    gamma = psychrometric_constant(p_kpa)
    ra = extraterrestrial_radiation(lat_rad, doy)
    rso = clear_sky_radiation(ra, z)
    rns = net_shortwave(rs)
    rnl = net_longwave(tmax, tmin, ea, rs, rso)
    rn = rns - rnl                                                        # Eq. 40
    num = 0.408 * delta * (rn - g) + gamma * (900.0 / (tmean + 273.0)) * u2 * (es - ea)
    den = delta + gamma * (1.0 + 0.34 * u2)
    et0 = num / den
    terms = {"tmean": tmean, "es": es, "delta": delta, "gamma": gamma, "ra": ra, "rso": rso,
             "rns": rns, "rnl": rnl, "rn": rn}
    return et0, terms
