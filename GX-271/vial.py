#############################################################################################
# Vial Class
#############################################################################################

class Vial:
    """Representation for a Vial within the flow setup."""
    def __init__(self, vial_volume_max, vial_usedvolume_max, vial_height, vial_free_depth):
        self.vial_volume_max = vial_volume_max          # volume in mL
        self.vial_usedvolume_max = vial_usedvolume_max  # volume in mL
        self.vial_height = vial_height                  # height in mm
        self.vial_free_depth = vial_free_depth          # depth in mm
        self.sum_liquid_level = 0
        self.current_volume = 0.0                       # current volume in mL
        self.contents = None                            # substance string (e.g., "0.5mM Reagent A")
        self.min_usable_fraction = 0.10                 
        self.vial_min_usable_volume = self.vial_volume_max * self.min_usable_fraction               # Defines a "functional empty" state, 10% of max volume

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def fill(self, volume, substance):
        """ Logs that the vial has been filled manually.

        Parameters
        ----------
        volume : float --- volume (mL) to record
        substance : str --- Name of substance being added
        """

        if self.contents is not None and self.contents != substance:
            raise ValueError(f"Vial contains {self.contents}. Empty before filling with {substance}.")

        if volume > self.vial_volume_max:
            print(f"Volume {volume} exceeds vial max ({self.vial_volume_max}). Setting volume to max...")
            volume = self.vial_volume_max

        self.current_volume = volume
        self.contents = substance
        print(f"Vial filled with {volume} mL of {substance}.")

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def empty(self):
        """Empty the vial and reset contents"""
        self.current_volume = 0.0
        self.contents = None
        print("Vial emptied - clean or replace before refill")

# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def consume_volume(self, volume):
        """Reduce the volume after withdrawal (used by Pump class)"""
        if self.current_volume == 0:
            raise ValueError("Vial is empty - cannot withdraw.")
            
        if self.current_volume - volume < self.vial_min_usable_volume:
            raise ValueError(f"Withdrawal of {volume} mL would drop the volume below safe working limit"
                             f"({self.vial_min_usable_volume:.2f} mL). Refill or replace vial.")

        self.current_volume -= volume
        print(f"Withdrawn {volume} mL. Remaining: {self.current_volume:.2f} mL of {self.contents}.")
        
# --------------------------------------------------------------------------------------------------------------------------------------------------------
    def is_usable(self):
        """Return True if vial still has sufficient volume for use"""
        return self.current_volume > self.vial_min_usable_volume

# -------------------------------------------------------------------------------------------------------------------------------------------------------   
    def get_vial_status(self):
        if self.contents:
            return f"Vial contains {self.current_volume} mL of {self.contents}."
        else:
            return "Vial is empty."