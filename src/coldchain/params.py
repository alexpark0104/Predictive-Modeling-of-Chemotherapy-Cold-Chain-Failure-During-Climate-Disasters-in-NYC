"""Parameter registry: every model input, with its provenance status.

Statuses
--------
SOURCED      value taken directly from a primary source you have read
ANCHORED     value derived from literature seen only as a snippet; VERIFY against the primary source
ASSUMED      modeling choice, not from a source; needs justification or a sensitivity range
PLACEHOLDER  illustrative only; must be replaced before any result is reported

`assert_publishable()` raises if any placeholder remains, so analysis scripts that
produce reported numbers should call it first.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

SOURCED, ANCHORED, ASSUMED, PLACEHOLDER = "SOURCED", "ANCHORED", "ASSUMED", "PLACEHOLDER"


@dataclass(frozen=True)
class Param:
    name: str
    value: Any
    unit: str
    status: str
    source: str
    note: str = ""


class PlaceholderError(RuntimeError):
    pass


_P = [
    # --- refrigerator thermal behavior (NIST vaccine-storage studies; seen as snippets) ---
    Param("breach_hr_pharmaceutical", (0.75, 2.25), "h", ANCHORED, "NIST (Chojnacky & Strouse 2012)",
          "Time after power-off until vial temperature exceeds 8 C. Verify test room temperature and load."),
    Param("breach_hr_freezerless", (1.5, 4.5), "h", ANCHORED, "NIST (Chojnacky & Strouse 2012)", ""),
    Param("breach_hr_dual_zone", (1.25, 4.75), "h", ANCHORED, "NIST (Chojnacky & Strouse 2012)", ""),
    Param("breach_hr_dorm", (0.75, 3.5), "h", ANCHORED, "NIST (Chojnacky & Strouse 2012)", ""),
    Param("nist_test_room_c", 22.0, "C", ASSUMED, "none", "Room temperature used to convert NIST breach times to time constants. Check NIST report."),
    Param("fridge_setpoint_range_c", (4.0, 6.0), "C", ASSUMED, "none", "Initial fridge temperature range."),
    Param("room_initial_c", 22.0, "C", ASSUMED, "prototype", "Indoor temperature at outage start."),
    Param("outdoor_c", 30.0, "C", ASSUMED, "prototype", "Hot-weather scenario; vary in sensitivity analysis."),
    Param("tau_room_hr", 4.0, "h", ASSUMED, "prototype", "Indoor warming time constant with HVAC off."),
    # --- degradation ---
    Param("ea_kj_mol", 100.0, "kJ/mol", PLACEHOLDER, "none",
          "ILLUSTRATIVE. Replace with Ea fitted to trastuzumab kinetic data (FDA BsUFA III models expected 2027; published studies)."),
    Param("t_ref_c", 25.0, "C", ASSUMED, "none", "Reference temperature for thermal-equivalent hours."),
    Param("budget_equiv_hr_range", (72.0, 504.0), "equiv h at t_ref", ANCHORED,
          "Trastuzumab biosimilar excursion study (72 h at 25 C, no destabilization) and a rituximab biosimilar (21 d ambient)",
          "Lower end is a no-change lower bound, not a measured failure point. Different molecules; verify both."),
    Param("policy_allowed_hr_above_8c", 0.0, "h", ASSUMED, "none", "Strict label rule. Verify current Herceptin and biosimilar labels."),
    # --- outages and backup (all placeholders until fitted to EAGLE-I / utility data) ---
    Param("outage_sigma", 1.0, "log-sd", PLACEHOLDER, "none", "Spread of lognormal outage duration; fit to data."),
    Param("p_backup_ok_nonflood", 0.0, "prob", PLACEHOLDER, "none", "Facility-type specific; community pharmacies ~29% had generators in Sandy-hit areas (snippet)."),
    Param("p_backup_ok_flood", 0.0, "prob", PLACEHOLDER, "none", "Generators failed under flooding at several NYC hospitals in Sandy."),
]

PARAMS = {p.name: p for p in _P}


def value(name: str) -> Any:
    return PARAMS[name].value


def placeholders(names: Optional[Iterable[str]] = None):
    names = list(PARAMS) if names is None else list(names)
    return [n for n in names if PARAMS[n].status == PLACEHOLDER]


def assert_publishable(names: Optional[Iterable[str]] = None) -> None:
    bad = placeholders(names)
    if bad:
        raise PlaceholderError("Placeholder parameters must be replaced before reporting results: " + ", ".join(bad))


def summary_table() -> str:
    rows = ["| name | value | unit | status | source |", "|---|---|---|---|---|"]
    for p in PARAMS.values():
        rows.append(f"| {p.name} | {p.value} | {p.unit} | {p.status} | {p.source} |")
    return "\n".join(rows)
