import json
from pathlib import Path


class ExperimentValidator:

    # ------------------------------------------------------------
    # PLAN VALIDATION
    # ------------------------------------------------------------

    def validate_plan(self, plan):

        errors = []
        warnings = []

        if "experiment_id" not in plan:
            errors.append("Missing experiment_id")

        gc = plan.get("global_conditions", {})

        if "flowrate_ul_min" not in gc:
            errors.append("Missing global_conditions.flowrate_ul_min")

        if "gas_prime_s" not in gc:
            errors.append("Missing global_conditions.gas_prime_s")

        slugs = plan.get("slugs", [])

        if not slugs:
            errors.append("No slugs defined")

        slug_ids = []

        for i, slug in enumerate(slugs, start=1):

            slug_id = slug.get("slug_id", f"<missing:{i}>")
            slug_ids.append(slug_id)

            rp = slug.get("reaction_plan", [])

            if not rp:
                errors.append(f"{slug_id}: empty reaction_plan")

            total_vol = 0

            for comp in rp:

                if "module" not in comp:
                    errors.append(f"{slug_id}: component missing module")

                if "vial" not in comp:
                    errors.append(f"{slug_id}: component missing vial")

                vol = comp.get("volume_uL", 0)

                if vol <= 0:
                    errors.append(f"{slug_id}: invalid volume {vol}")

                total_vol += vol

            if total_vol <= 0:
                errors.append(f"{slug_id}: total volume <= 0")

        if len(set(slug_ids)) != len(slug_ids):
            errors.append("Duplicate slug_id values detected")

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "slug_count": len(slugs),
        }

    # ------------------------------------------------------------
    # PREFLIGHT
    # ------------------------------------------------------------

    def validate_preflight(self, manager, seg):

        errors = []

        if manager.context is None:
            errors.append("No experiment loaded")

        else:
            if manager.context.state != "armed":
                errors.append(
                    f"Manager state must be armed, got {manager.context.state}"
                )

        if hasattr(seg, "state"):
            phase = seg.state.phase.name
            if phase not in ("READY", "GAS_PRIMED"):
                errors.append(
                    f"Segmentation phase unsuitable for start: {phase}"
                )

        return {
            "passed": len(errors) == 0,
            "errors": errors,
        }

    # ------------------------------------------------------------
    # POST RUN
    # ------------------------------------------------------------

    def validate_post_run(self, manager, results):

        errors = []
        warnings = []

        if manager.context is None:
            errors.append("No experiment context")

            return {
                "passed": False,
                "errors": errors,
                "warnings": warnings,
            }

        planned = len(manager.context.plan["slugs"])
        actual = len(results)

        if planned != actual:
            errors.append(
                f"Planned {planned} slugs but got {actual} results"
            )

        if manager.context.state != "completed":
            errors.append(
                f"Manager state = {manager.context.state}, expected completed"
            )

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "planned_slugs": planned,
            "executed_slugs": actual,
        }

    # ------------------------------------------------------------
    # LOG VALIDATION
    # ------------------------------------------------------------

    def validate_log(self, log_path):

        errors = []

        path = Path(log_path)

        if not path.exists():
            return {
                "passed": False,
                "errors": ["Log file missing"]
            }

        with open(path, "r") as f:
            log = json.load(f)

        events = log.get("events", [])

        completed = any(
            e["event_type"] == "experiment_completed"
            for e in events
        )

        if not completed:
            errors.append("Missing experiment_completed event")

        return {
            "passed": len(errors) == 0,
            "errors": errors,
            "event_count": len(events),
        }