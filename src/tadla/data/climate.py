"""Daily ERA5-Land + CHIRPS values per cell -> physical units -> FAO-56 ET0 -> monthly table.

Every unit conversion of the climate inputs happens here (raw values come from
tadla.data.gee_export.climate_month, see ERA5_DAILY_BANDS there for the raw units).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from tadla.irrigation import fao56

_COL = re.compile(r"^(?P<var>.+)_d(?P<day>\d{2})$")


def wide_to_long(wide: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """'tmax_d07'-style columns (one row per cell) -> one row per cell and day."""
    parts = []
    for col in wide.columns:
        m = _COL.match(col)
        if m:
            parts.append(pd.DataFrame({"cell_id": wide["cell_id"], "day": int(m["day"]),
                                       "var": m["var"], "value": wide[col]}))
    long = pd.concat(parts, ignore_index=True)
    out = long.pivot_table(index=["cell_id", "day"], columns="var", values="value", aggfunc="first",
                           dropna=False).reset_index()
    out["date"] = pd.to_datetime(dict(year=year, month=month, day=out.pop("day")))
    out.columns.name = None
    return out


def to_physical(raw: pd.DataFrame) -> pd.DataFrame:
    """Raw daily values -> physical units (one row per cell and day)."""
    out = raw[["cell_id", "date"]].copy()
    out["tmax_c"] = raw["tmax"] - 273.15            # K -> °C
    out["tmin_c"] = raw["tmin"] - 273.15            # K -> °C
    out["tmean_c"] = raw["tmean"] - 273.15          # K -> °C (daily mean of hourly 2 m temperature)
    out["tdew_c"] = raw["tdew"] - 273.15            # K -> °C (daily mean dew point)
    out["ea_kpa"] = fao56.sat_vapour_pressure(out["tdew_c"])   # FAO-56 Eq. 14: ea = e°(Tdew)
    out["p_kpa"] = raw["sp"] / 1000.0               # Pa -> kPa
    out["rs_mj"] = raw["ssrd"] / 1e6                # J m-2 day-1 -> MJ m-2 day-1
    out["ws10_ms"] = raw["ws10"]                    # m s-1 at 10 m (mean of hourly speeds)
    out["u2_ms"] = fao56.wind_2m(raw["ws10"], 10.0) # FAO-56 Eq. 47: 10 m -> 2 m (factor 0.748)
    # ERA5 total_evaporation is in metres of water equivalent with the ECMWF sign convention
    # (negative = evaporation, positive = condensation): ET_actual (mm, + = evaporation) = -1000 * te
    out["et_actual_mm"] = -1000.0 * raw["te"]
    out["swvl1"] = raw["swvl1"]                     # m3 m-3, layer 0–7 cm
    out["swvl2"] = raw["swvl2"]                     # m3 m-3, layer 7–28 cm
    out["rain_mm"] = raw["rain"]                    # CHIRPS, mm day-1
    out["nhours"] = raw["nhours"]                   # hourly ERA5 records behind ws10 (expect 24)
    return out


def add_et0(daily: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    """Daily FAO-56 ET0 (mm day-1). `cells` gives lat_deg and z_m (ALOS mean elevation) per cell_id;
    elevation only enters the clear-sky radiation Rso (Eq. 37); pressure comes from ERA5-Land."""
    d = daily.merge(cells[["cell_id", "lat_deg", "z_m"]], on="cell_id", how="left")
    et0, terms = fao56.et0_daily(
        tmax=d["tmax_c"].to_numpy(), tmin=d["tmin_c"].to_numpy(), ea=d["ea_kpa"].to_numpy(),
        rs=d["rs_mj"].to_numpy(), u2=d["u2_ms"].to_numpy(), p_kpa=d["p_kpa"].to_numpy(),
        lat_rad=np.deg2rad(d["lat_deg"].to_numpy()), doy=d["date"].dt.dayofyear.to_numpy(),
        z=d["z_m"].to_numpy())
    out = daily.copy()
    out["et0_mm"] = et0
    out["rn_mj"] = terms["rn"]
    out["ra_mj"] = terms["ra"]
    out["rso_mj"] = terms["rso"]
    return out


def monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly table per cell: sums for fluxes, means for states."""
    d = daily.copy()
    d["year"] = d["date"].dt.year
    d["month"] = d["date"].dt.month
    g = d.groupby(["cell_id", "year", "month"])
    out = pd.DataFrame({
        "rain_mm": g["rain_mm"].sum(min_count=1),
        "et0_mm": g["et0_mm"].sum(min_count=1),
        "et_actual_mm": g["et_actual_mm"].sum(min_count=1),
        "t2m_c": g["tmean_c"].mean(),
        "tmax_c": g["tmax_c"].mean(),
        "tmin_c": g["tmin_c"].mean(),
        "swvl1": g["swvl1"].mean(),
        "swvl2": g["swvl2"].mean(),
        "rs_mj": g["rs_mj"].mean(),
        "u2_ms": g["u2_ms"].mean(),
        "ea_kpa": g["ea_kpa"].mean(),
        "n_days": g["date"].count(),
        "n_days_with_et0": g["et0_mm"].count(),
    }).reset_index()
    return out
