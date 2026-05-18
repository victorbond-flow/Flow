from typing import Optional


def append_trace(
    trace,
    step: str,
    action: str,
    module: Optional[str] = None,
    vial: Optional[int] = None,
    volume_uL: Optional[float] = None,
    rate: Optional[float] = None,
    notes: Optional[str] = None,
):
    if trace is None:
        return

    entry = {
        "step": step,
        "action": action,
    }

    if module is not None:
        entry["module"] = module
    if vial is not None:
        entry["vial"] = vial
    if volume_uL is not None:
        entry["volume_uL"] = volume_uL
    if rate is not None:
        entry["rate"] = rate
    if notes is not None:
        entry["notes"] = notes

    trace.append(entry)
