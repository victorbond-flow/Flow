import pandas as pd

class HPLCReader:
    def __init__(self, directory):
        self.directory = directory

    def read_latest_measurement(self):
        # Logic to read the latest measurement
        csv_files = self._get_csv_files(self.directory)
        latest_file = max(csv_files, key=os.path.getctime)
        return pd.read_csv(latest_file)

    def _parse_hplc_csv(self, file_path):
        # Placeholder for the method to parse HPLC CSV files
        pass

    def _get_csv_files(self, directory):
        import os
        return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.csv')]