import time
from enum import Enum, auto
from typing import Optional
from core.tracing import append_trace


def _trace_print(trace, *args, **kwargs):
    if trace is None:
        print(*args, **kwargs)


class RSGState(Enum):
    IDLE = auto()
    RUNNING = auto()
    ERROR = auto()


# TODO - move away from time.sleep and toward real monitoring for pump completion.
class RSG:
    """
    Reaction Segment Generation (RSG)

    Orchestrates high-level liquid handling actions using:
    - GilsonEthernet (autosampler, owns all motion + safety)
    - syringe pump
    - DIM (when slug creation is required)

    Design rules:
    - No rack geometry here
    - No vial maps
    - No Z logic
    - No mirroring of Gilson internals
    """

    def __init__(self, gilson, pump, dim=None, probe=None, wash_safety_margin_ul=3.0):
        self.gilson = gilson
        self.pump = pump
        self.dim = dim
        self.probe = probe
        self.wash_safety_margin_ul = wash_safety_margin_ul
        self.state = RSGState.IDLE
        self.initial_air_gap_uL = None
        self.initial_air_gap_rate_mL_min = None

    # ------------------------------------------------------------------
    # Primitive actions
    # ------------------------------------------------------------------
    def _require_idle(self):
        if self.state != RSGState.IDLE:
            raise RuntimeError(f"RSG is busy or in error state: {self.state}")

    def _require_dim(self):
        if self.dim is None:
            raise RuntimeError(
                "RSG requires a DIM instance for this operation. "
                "Instantiate as RSG(gilson, pump, dim)."
            )

    def _normalise_reaction_plan(self, reaction_plan):
        if not isinstance(reaction_plan, list):
            raise TypeError("reaction_plan must be a list of dicts.")

        normalised = []

        for component in reaction_plan:
            if not isinstance(component, dict):
                raise TypeError("Each reaction component must be a dict.")

            try:
                module = component["module"]
                vial = component["vial"]
            except KeyError as exc:
                raise ValueError(
                    "Each reaction component must contain 'module' and 'vial'."
                ) from exc

            volume = component.get(
                "volume",
                component.get("volume_uL", component.get("volume_ul")),
            )
            if volume is None:
                raise ValueError(
                    "Each reaction component must contain 'volume' or 'volume_uL'."
                )

            volume = float(volume)
            if volume <= 0:
                raise ValueError("Component volumes must be positive.")

            normalised.append(
                {
                    "module": module,
                    "vial": vial,
                    "volume_uL": volume,
                    "rate_ml_min": float(component.get("rate", 0.05)),
                }
            )

        return normalised

    def _reaction_plan_from_slug(self, slug_plan):
        if not isinstance(slug_plan, dict):
            raise TypeError("slug_plan must be a dict.")

        if "reaction_plan" in slug_plan:
            return self._normalise_reaction_plan(slug_plan["reaction_plan"])

        if all(key in slug_plan for key in ("module", "vial")):
            volume = slug_plan.get("volume_uL", slug_plan.get("volume"))
            if volume is None:
                raise ValueError(
                    "Single-source slug plans must define 'volume_uL' or 'volume'."
                )

            return self._normalise_reaction_plan(
                [
                    {
                        "module": slug_plan["module"],
                        "vial": slug_plan["vial"],
                        "volume_uL": volume,
                        "rate": slug_plan.get("pickup_rate", 0.05),
                    }
                ]
            )

        raise ValueError(
            "slug_plan must define either 'reaction_plan' or "
            "'module'/'vial' plus 'volume_uL'."
        )

    def initialise(self, air_gap: float = 20.0, rate_wdr: float = 0.25, dry_run=False, trace=None):
        _trace_print(trace, "[Initialise] Setting up start condition")

        self._require_idle()
        self.state = RSGState.RUNNING

        try:
            # First, reset logical state
            if self.probe is not None:
                self.probe.reset()

            # Then, physical action
            self.take_air_gap(volume=air_gap, rate=rate_wdr, dry_run=dry_run, trace=trace)
            self.initial_air_gap_uL = float(air_gap)
            self.initial_air_gap_rate_mL_min = float(rate_wdr)

            self.state = RSGState.IDLE
            _trace_print(trace, "[Initialise] Ready - air gap in place")

        except Exception:
            self.state = RSGState.ERROR
            raise

    def pickup_from_vial(
    self,
    module_name: str,
    vial_pos: int,
    volume: float,
    rate: float = 0.05,
    dry_run=False,
    trace=None,
):
        _trace_print(trace, f"[Pickup] {volume}uL from {module_name} vial {vial_pos} @ {rate}mL/min")
    
        append_trace(
            trace,
            step="rsg",
            action="pickup_from_vial",
            module=module_name,
            vial=vial_pos,
            volume_uL=volume,
            rate=rate,
        )
    
        if dry_run:
            self.pump.withdraw_volume(volume, rate, dry_run=True, trace=trace)
        else:
            self.gilson.go_into_vial(module_name, vial_pos)
            self.pump.withdraw_volume(volume, rate)
    
            wait_time = (volume / (rate * 1000)) * 60
            time.sleep(wait_time + 1)
    
        if self.probe is not None:
            self.probe.add("sample", volume)
    
            append_trace(
                trace,
                step="probe",
                action="add",
                volume_uL=volume,
                notes="sample",
            )
    
            # NEW: probe snapshot after pump + state mutation
            append_trace(
                trace,
                step="probe",
                action="snapshot",
                notes=self.probe.status(),
            )
    
            _trace_print(trace, f"[Probe] {self.probe.status()}")

    def dispense_in_vial(
        self,
        module_name: str,
        vial_pos: int,
        volume: float,
        rate: float = 0.5,
        dry_run=False,
        trace=None,
    ):
        _trace_print(trace, f"[Dispense] {volume}uL in {module_name} vial {vial_pos} @ {rate}mL/min")

        append_trace(
            trace,
            step="rsg",
            action="dispense_in_vial",
            module=module_name,
            vial=vial_pos,
            volume_uL=volume,
            rate=rate,
        )

        if dry_run:
            self.pump.infuse_volume(volume, rate, dry_run=True, trace=trace)
        else:
            self.gilson.go_into_vial(module_name, vial_pos)
            self.pump.infuse_volume(volume, rate)

            wait_time = (volume / (rate * 1000)) * 60
            time.sleep(wait_time + 1)

        if self.probe is not None:
            self.probe.consume(volume)
            append_trace(
                trace,
                step="probe",
                action="consume",
                volume_uL=volume,
            )
            _trace_print(trace, f"[Probe] {self.probe.status()}")

    def dispense_in_waste(self, volume: float, rate: float = 0.5, dry_run=False, trace=None):
        _trace_print(trace, f"[Waste] {volume}uL to waste @ {rate}mL/min")

        module_name = "rack2"
        vial_pos = 2

        append_trace(
            trace,
            step="rsg",
            action="dispense_in_waste",
            module=module_name,
            vial=vial_pos,
            volume_uL=volume,
            rate=rate,
        )

        if dry_run:
            self.pump.infuse_volume(volume, rate, dry_run=True, trace=trace)
        else:
            self.gilson.go_to_vial(module_name, vial_pos)
            self.gilson.go_into_vial(module_name, vial_pos)
            self.pump.infuse_volume(volume, rate)

            wait_time = (volume / (rate * 1000)) * 60
            time.sleep(wait_time + 1)

            self.gilson.ensure_z_safe()

        if self.probe is not None:
            self.probe.consume(volume)
            append_trace(
                trace,
                step="probe",
                action="consume",
                volume_uL=volume,
            )
            _trace_print(trace, f"[Probe] {self.probe.status()}")

    def dispense_in_dim(
    self,
    rate: float = 0.5,
    volume: Optional[float] = None,
    front_air_use: float = 5.0,
    dry_run=False,
    trace=None,
):
        # ------------------------------------------------------------
        # TEMPORARY MANUAL-ORCHESTRATION VERSION
        #
        # Goal:
        # Preserve original topology/tracing logic for future recovery,
        # but temporarily reduce this method to a deterministic physical
        # dispense primitive suitable for reliable experimental runs.
        #
        # Current philosophy:
        # - explicit choreography in notebook script
        # - explicit topology management by user
        # - minimal hidden logic
        # - no automatic probe movement
        # ------------------------------------------------------------
    
        _trace_print(
            trace,
            f"[DIM Dispense] {volume}uL @ {rate}mL/min"
        )
    
        # ------------------------------------------------------------
        # ORIGINAL TRACE LOGIC
        # TEMPORARILY DISABLED
        # ------------------------------------------------------------
    
        """
        append_trace(
            trace,
            step="rsg",
            action="dispense_in_dim",
            module="dim",
            volume_uL=volume,
            rate=rate,
        )
        """
    
        # ------------------------------------------------------------
        # ORIGINAL TOPOLOGY INFERENCE LOGIC
        # TEMPORARILY DISABLED
        # ------------------------------------------------------------
    
        """
        if self.probe is None:
            raise RuntimeError("Probe required for deterministic DIM dispense")
    
        _trace_print(trace, "[Step 1] Reading probe state...")
        _trace_print(trace, f"         Current: {self.probe.status()}")
    
        contents = self.probe.contents
    
        if len(contents) < 3:
            raise RuntimeError("Probe state too short for DIM dispense")
    
        # ------------------------------------------------------------
        # 1. Find POST AIR (must be last air)
        # ------------------------------------------------------------
        post_air_index = None
        for i in range(len(contents) - 1, -1, -1):
            if contents[i]["type"] == "air":
                post_air_index = i
                break
    
        if post_air_index is None:
            raise RuntimeError("No post-air segment found")
    
        post_air = contents[post_air_index]
    
        # ------------------------------------------------------------
        # 2. Find SAMPLE (must be before post-air)
        # ------------------------------------------------------------
        sample_index = None
        for i in range(post_air_index - 1, -1, -1):
            if contents[i]["type"] == "sample":
                sample_index = i
                break
    
        if sample_index is None:
            raise RuntimeError("No sample segment found before post-air")
    
        sample = contents[sample_index]
    
        # ------------------------------------------------------------
        # 3. Find FRONT AIR (air before sample)
        # ------------------------------------------------------------
        front_air_index = None
        for i in range(sample_index - 1, -1, -1):
            if contents[i]["type"] == "air":
                front_air_index = i
                break
    
        if front_air_index is None:
            raise RuntimeError("No front air segment found before sample")
    
        front_air = contents[front_air_index]
    
        # ------------------------------------------------------------
        # DEBUG OUTPUT
        # ------------------------------------------------------------
        _trace_print(trace, "\n==============================")
        _trace_print(trace, "[RSG DISPENSE DEBUG ENTRY]")
        _trace_print(trace, "==============================")
    
        for i, s in enumerate(contents):
            _trace_print(trace, i, s)
    
        _trace_print(trace, "\n[IDENTIFIED STRUCTURE]")
        _trace_print(trace, "front_air:", front_air)
        _trace_print(trace, "sample:", sample)
        _trace_print(trace, "post_air:", post_air)
    
        # ------------------------------------------------------------
        # 4. Compute volume
        # ------------------------------------------------------------
        sample_vol = sample["volume_ul"]
        post_air_vol = post_air["volume_ul"]
    
        derived_volume = sample_vol + post_air_vol + front_air_use
        inject_volume = derived_volume if volume is None else volume
    
        if inject_volume < sample_vol + post_air_vol:
            raise ValueError("Inject volume too small for payload + post-air")
        """
    
        # ------------------------------------------------------------
        # TEMPORARY SIMPLE DISPENSE BEHAVIOUR
        # ------------------------------------------------------------
    
        if volume is None:
            raise ValueError(
                "Manual orchestration mode requires explicit dispense volume"
            )
    
        inject_volume = volume
    
        # ------------------------------------------------------------
        # PHYSICAL INFUSION
        # ------------------------------------------------------------
    
        if dry_run:
    
            self.pump.infuse_volume(
                inject_volume,
                rate,
                dry_run=True,
                trace=trace,
            )
    
        else:
    
            self.gilson.go_into_dim()
    
            self.pump.infuse_volume(inject_volume, rate)
    
            wait_time = (inject_volume / (rate * 1000)) * 60
    
            time.sleep(wait_time + 1)
    
        _trace_print(trace, "[DIM] Physical infusion complete")
    
        # ------------------------------------------------------------
        # TEMPORARY SIMPLE PROBE BOOKKEEPING
        # ------------------------------------------------------------
    
        # We intentionally consume ONLY the explicitly
        # dispensed volume.
        #
        # No topology inference.
        # No front/post air interpretation.
        # No automatic structural reasoning.
        #
        # The notebook orchestration script is now responsible
        # for defining topology deterministically.
    
        if self.probe is not None:
    
            self.probe.consume(inject_volume)
    
            # --------------------------------------------------------
            # ORIGINAL TRACE LOGIC
            # TEMPORARILY DISABLED
            # --------------------------------------------------------
    
            """
            append_trace(
                trace,
                step="probe",
                action="consume",
                volume_uL=inject_volume,
            )
            """
    
            _trace_print(
                trace,
                f"[Probe] {self.probe.status()}"
            )
    
        # ------------------------------------------------------------
        # ORIGINAL DETERMINISTIC TOPOLOGY CONSUMPTION LOGIC
        # TEMPORARILY DISABLED
        # ------------------------------------------------------------
    
        """
        _trace_print(trace, "[Step 4] Updating probe state...")
    
        # post_air
        self.probe.consume(post_air_vol)
    
        append_trace(
            trace,
            step="probe",
            action="consume",
            volume_uL=post_air_vol,
            notes="post_air",
        )
    
        append_trace(
            trace,
            step="probe",
            action="snapshot",
            notes=self.probe.status(),
        )
    
        # sample
        self.probe.consume(sample_vol)
    
        append_trace(
            trace,
            step="probe",
            action="consume",
            volume_uL=sample_vol,
            notes="sample",
        )
    
        append_trace(
            trace,
            step="probe",
            action="snapshot",
            notes=self.probe.status(),
        )
    
        # front air
        self.probe.consume(front_air_use)
    
        append_trace(
            trace,
            step="probe",
            action="consume",
            volume_uL=front_air_use,
            notes="front_air",
        )
    
        append_trace(
            trace,
            step="probe",
            action="snapshot",
            notes=self.probe.status(),
        )
    
        _trace_print(trace, "[Step 5] Post-consume state:")
        _trace_print(trace, f"         {self.probe.status()}")
        """
    
        # ------------------------------------------------------------
        # IMPORTANT:
        # DO NOT RETRACT PROBE HERE
        #
        # Probe must remain seated during:
        # - valve switching
        # - slug launch
        # - launch dwell
        #
        # Probe movement should occur ONLY AFTER
        # the launch dwell completes.
        # ------------------------------------------------------------
    
        """
        if not dry_run:
            self.gilson.ensure_z_safe()
        """
    
        _trace_print(trace, "[DIM] ================= COMPLETE =================")

    def take_air_gap(self, volume: float, rate: float = 0.05, dry_run=False, trace=None):
        _trace_print(trace, f"[Air Gap] {volume}uL @ {rate}mL/min")

        append_trace(
            trace,
            step="rsg",
            action="take_air_gap",
            volume_uL=volume,
            rate=rate,
        )

        if dry_run:
            self.pump.withdraw_volume(volume, rate, dry_run=True, trace=trace)
        else:
            self.gilson.ensure_z_safe()
            self.pump.withdraw_volume(volume, rate)

            wait_time = (volume / (rate * 1000)) * 60
            time.sleep(wait_time + 1)

        if self.probe is not None:
            self.probe.add("air", volume)
            append_trace(
                trace,
                step="probe",
                action="add",
                volume_uL=volume,
                notes="air",
            )
            _trace_print(trace, f"[Probe] {self.probe.status()}")

    def prepickup(self, volume: float = 10.0, rate: float = 0.05, dry_run=False, trace=None):
        _trace_print(trace, f"[Pre-pickup] {volume}uL from rack2 vial 1 @ {rate} mL/min")

        module_name = "rack2"
        vial_pos = 1

        append_trace(
            trace,
            step="rsg",
            action="prepickup",
            module=module_name,
            vial=vial_pos,
            volume_uL=volume,
            rate=rate,
        )

        if dry_run:
            self.pump.withdraw_volume(volume, rate, dry_run=True, trace=trace)
        else:
            self.gilson.go_into_vial(module_name, vial_pos)
            self.pump.withdraw_volume(volume, rate)

            wait_time = (volume / (rate * 1000)) * 60
            time.sleep(wait_time + 1)

            self.gilson.ensure_z_safe()

    # ------------------------------------------------------------------
    # Washes
    # ------------------------------------------------------------------
    def needle_wash(
        self,
        wash_solvent_volume: float,
        rate_wdr: float = 0.25,
        rate_inf: float = 0.5,
        safety_margin_ul: float = 10.0,
        dry_run=False,
        trace=None,
    ):
        _trace_print(trace, "\n[Needle Wash] ================= START =================")
    
        # ------------------------------------------------------------
        # 0. Safety positioning
        # ------------------------------------------------------------
        _trace_print(trace, "[Step 0] Ensuring Z safe...")
        if not dry_run:
            self.gilson.ensure_z_safe()
    
        if self.probe is None:
            raise RuntimeError("Probe required for deterministic wash")
    
        _trace_print(trace, "[Step 1] Reading probe state...")
        _trace_print(trace, f"         Current: {self.probe.status()}")
    
        # ------------------------------------------------------------
        # 1. quantify what is currently in probe (from state model)
        # ------------------------------------------------------------
        air_remaining = sum(
            x["volume_ul"]
            for x in self.probe.contents
            if x["type"] == "air"
        )
    
        _trace_print(trace, f"[Step 2] Air remaining (from state): {air_remaining:.2f} uL")
    
        # ------------------------------------------------------------
        # 2. acquire wash solvent using REAL pickup method
        # ------------------------------------------------------------
        _trace_print(trace, f"[Step 3] Picking up wash solvent: {wash_solvent_volume} uL")
    
        self.pickup_from_vial(
            module_name="rack2",
            vial_pos=1,
            volume=wash_solvent_volume,
            rate=rate_wdr,
            dry_run=dry_run,
            trace=trace,
        )
    
        # ------------------------------------------------------------
        # 3. compute purge requirement
        # ------------------------------------------------------------
        purge_volume = wash_solvent_volume + air_remaining + safety_margin_ul
    
        _trace_print(trace, f"[Step 4] Purge calculation:")
        _trace_print(trace, f"         wash solvent: {wash_solvent_volume}")
        _trace_print(trace, f"         air remaining: {air_remaining}")
        _trace_print(trace, f"         safety margin: {safety_margin_ul}")
        _trace_print(trace, f"         => purge total: {purge_volume} uL")
    
        # ------------------------------------------------------------
        # 4. infuse to waste
        # ------------------------------------------------------------
        _trace_print(trace, "[Step 5] Infusing to waste...")
    
        append_trace(
            trace,
            step="rsg",
            action="needle_wash_purge",
            module="rack2",
            vial=2,
            volume_uL=purge_volume,
            rate=rate_inf,
        )

        if dry_run:
            self.pump.infuse_volume(purge_volume, rate_inf, dry_run=True, trace=trace)
        else:
            self.gilson.go_into_vial("rack2", 2)
            self.pump.infuse_volume(purge_volume, rate_inf)

            time.sleep((purge_volume / (rate_inf * 1000)) * 60 + 1)
    
        _trace_print(trace, "[Step 6] Infusion complete")
    
        # ------------------------------------------------------------
        # 5. reset probe state (clean slate after deterministic purge)
        # ------------------------------------------------------------
        _trace_print(trace, "[Step 7] Resetting probe state...")
        self.probe.reset()
        append_trace(
            trace,
            step="probe",
            action="reset",
            notes="needle_wash",
        )
    
        if not dry_run:
            self.gilson.ensure_z_safe()
    
        _trace_print(trace, "[Needle Wash] ================= COMPLETE =================\n")
        _trace_print(trace, f"[Final Probe State] {self.probe.status()}")

    def between_slug_wash(self, rate_wdr: float = 0.25, rate_inf: float = 0.5, dry_run=False, trace=None):
        _trace_print(trace, "[Between Slug Wash] Starting")

        self._require_idle()
        self.state = RSGState.RUNNING

        try:
            self.needle_wash(rate_wdr=rate_wdr, rate_inf=rate_inf, dry_run=dry_run, trace=trace)
            self.dim_wash(rate_wdr=rate_wdr, rate_inf=rate_inf, dry_run=dry_run, trace=trace)
            self.state = RSGState.IDLE
            _trace_print(trace, "[Between Slug Wash] Complete")
        except Exception:
            self.state = RSGState.ERROR
            raise

    def assemble_reaction(
        self,
        reaction_plan,
        air_gap_between: float = 5.0,
        post_pickup_air_gap: float = 5.0,
        front_air_gap: float = 5.0,
        withdraw_rate: float = None,
        dry_run=False,
        trace=None,
    ):
        self._require_idle()
        self.state = RSGState.RUNNING

        try:
            reaction_plan = self._normalise_reaction_plan(reaction_plan)

            total_volume = 0.0
            n = len(reaction_plan)

            # ---------------------------------------------------
            # 0. FRONT AIR (CRITICAL FIX)
            # ---------------------------------------------------
            if front_air_gap > 0:
                self.take_air_gap(front_air_gap, dry_run=dry_run, trace=trace)
                total_volume += front_air_gap

            # ---------------------------------------------------
            # 1. BUILD CORE STREAM
            # ---------------------------------------------------
            _trace_print(trace, "\n[ASSEMBLE REACTION INPUT]")
            _trace_print(trace, reaction_plan)
            
            for i, component in enumerate(reaction_plan):
                _trace_print(trace, f"[COMPONENT {i}] {component}")
            for i, component in enumerate(reaction_plan):

                self.pickup_from_vial(
                    module_name=component["module"],
                    vial_pos=component["vial"],
                    volume=component["volume_uL"],
                    rate=(
                        withdraw_rate
                        if withdraw_rate is not None
                        else component["rate_ml_min"]
                    ),
                    dry_run=dry_run,
                    trace=trace,
                )

                total_volume += component["volume_uL"]

                if i < n - 1 and air_gap_between > 0:
                    self.take_air_gap(air_gap_between, dry_run=dry_run, trace=trace)
                    total_volume += air_gap_between

            # ---------------------------------------------------
            # 2. POST AIR (kept as terminal buffer)
            # ---------------------------------------------------
            if post_pickup_air_gap > 0:
                self.take_air_gap(post_pickup_air_gap, dry_run=dry_run, trace=trace)
                total_volume += post_pickup_air_gap

            self.state = RSGState.IDLE

            return {
                "total_volume_ul": total_volume,
                "num_components": n,
            }

        except Exception:
            self.state = RSGState.ERROR
            raise

    def build_reaction(self, reaction_plan, air_gap_between: float = 5.0, dry_run=False, trace=None):
        return self.assemble_reaction(
            reaction_plan=reaction_plan,
            air_gap_between=air_gap_between,
            dry_run=dry_run,
            trace=trace,
        )

    def build_rxn_segment(
        self,
        slug_plan,
        air_gap_between: float = 5.0,
        dispense_rate: float = 0.5,
        withdraw_rate: float = None,
        dry_run=False,
        trace=None,
    ):
        self._require_dim()

        reaction_plan = self._reaction_plan_from_slug(slug_plan)
        slug_id = slug_plan.get("slug_id", "untracked-segment")

        _trace_print(trace, f"[Build Reaction Segment] {slug_id}")

        if dry_run:
            self.dim.assert_load(dry_run=True, trace=trace)
        else:
            self.dim.assert_load()

        result = self.assemble_reaction(
            reaction_plan=reaction_plan,
            air_gap_between=air_gap_between,
            withdraw_rate=withdraw_rate,
            dry_run=dry_run,
            trace=trace,
        )

        self.dispense_in_dim(
            volume=result["total_volume_ul"],
            rate=dispense_rate,
            dry_run=dry_run,
            trace=trace,
        )

        return {
            "slug_id": slug_id,
            "dispensed_volume_ul": result["total_volume_ul"],
            "num_components": result["num_components"],
            "air_gap_between_ul": air_gap_between,
        }

    def abort(self, dry_run=False, trace=None):
        if dry_run:
            append_trace(trace, step="rsg", action="abort")
        else:
            self.pump.stop()
            self.gilson.ensure_z_safe()
        self.state = RSGState.ERROR

        if self.probe is not None:
            self.probe.invalidate()
