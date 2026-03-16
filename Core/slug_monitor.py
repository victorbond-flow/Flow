import serial
import time
import csv
import matplotlib.pyplot as plt
from IPython.display import display, clear_output

class SlugMonitor:

    def __init__(self, port="COM9", baudrate=115200):
        self.ser = serial.Serial(port, baudrate)
        self.ser.reset_input_buffer()   # This flushes any leftover data when starting a data stream
        self.running = False

        self.time = []
        self.signal = []

    def read_line(self):
        while True:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()  # ignore bad bytes
            except UnicodeDecodeError:
                continue  # skip completely unreadable lines
    
            if not line:  # skip empty lines
                continue
    
            try:
                t, val = line.split(",")
                t = int(t)
                val = int(val)
                self.time.append(t)
                self.signal.append(val)
                return t, val
            except ValueError:
                # skip malformed lines (e.g., incomplete lines)
                continue

    def read_n(self, n=100):
        data = []
        for _ in range(n):
            data.append(self.read_line())
        return data

    def close(self):
        self.ser.close()

# --- Higher level methods ---

    def get_last_seconds(self, seconds):
        """Return the last N seconds of data"""
        if not self.time:
            return [], []
        start_time = self.time[-1] - (seconds*1000)
        idx = 0
        while idx < len(self.time) and self.time[idx] < start_time:
            idx += 1
        return self.time[idx:], self.signal[idx:]

    def stream_to_file(self, filename, n_lines=None):
        """Stream readings continuously and save to CSV with timestamps starting at 0"""
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp_ms", "signal"])
            count = 0
            time_offset = None  # first timestamp becomes zero
    
            while True:
                t, v = self.read_line()
                
                if time_offset is None:
                    time_offset = t  # set first timestamp as zero reference
                t_adjusted = t - time_offset
    
                writer.writerow([t_adjusted, v])
                count += 1
                if n_lines and count >= n_lines:
                    break

    def live_plot(self, duration=15, update_every=0.5, csv_filename=None, y_limits=(0, 600)):
        """
        Live plot LLD signal for a given duration (seconds).
        Optionally save all readings to a CSV file.
        
        Parameters:
            duration (float): total live plotting time in seconds
            update_every (float): interval between redraws in seconds
            csv_filename (str or None): if provided, saves readings to this CSV
            y_limits (tuple): (ymin, ymax) for fixed y-axis
        Returns:
            times, signals: lists of timestamps (ms) and signal values
        """
    
        # Flush buffer at start to ensure only fresh readings
        self.ser.reset_input_buffer()
        
        times, signals = [], []
    
        # Prepare CSV if needed
        if csv_filename:
            f = open(csv_filename, "w", newline="")
            writer = csv.writer(f)
            writer.writerow(["timestamp_ms", "signal"])
        
        plt.ion()
        fig, ax = plt.subplots(figsize=(12, 4))
        line, = ax.plot([], [], lw=1)
        ax.set_xlabel("Time (ms)")
        ax.set_ylabel("LLD signal")
        ax.set_title("SlugMonitor Live Plot")
        ax.set_ylim(*y_limits)

        plt.show(block=False)
        
        start_time = time.time()
        last_update = start_time
    
        while time.time() - start_time < duration:
            t, v = self.read_line()

            if not times:
                t0 = t  # first timestamp becomes zero reference
            
            t_rel = t - t0
            
            times.append(t_rel)
            signals.append(v)
            
            if csv_filename:
                writer.writerow([t_rel, v])
    
            # Update plot at intervals
            if time.time() - last_update >= update_every:
                line.set_data(times, signals)
                ax.set_xlim(times[0], times[-1] + 10)
            
                clear_output(wait=True)
                display(fig)
            
                last_update = time.time()
    
        plt.ioff()
        line.set_data(times, signals)
        ax.set_xlim(times[0], times[-1]+10)
        fig.canvas.draw()
        fig.canvas.flush_events()
    
        if csv_filename:
            f.close()
        
        return times, signals

    def auto_capture(self, pre_trigger_s=3, capture_s=30, gas_threshold=300, cooldown_s=60, save_folder="Notebooks/Logs/LLD_CSVs"):
        """
        Automatically capture LLD signals around detected gas slugs.
        
        Parameters:
            pre_trigger_s (float): seconds of data to keep before trigger
            capture_s (float): seconds to capture after trigger
            gas_threshold (int): signal below this indicates gas
            cooldown_s (float): minimum seconds between captures
            save_folder (str): folder to save CSVs
        """
        import os
        from datetime import datetime
    
        print(f"Starting auto_capture. Buffer size = {int(pre_trigger_s*50)} readings (~{pre_trigger_s}s)")
    
        buffer_len = int(pre_trigger_s * 50)  # rough 50 Hz sample rate
        buffer_times, buffer_signals = [], []
        last_capture_time = -cooldown_s  # allow first capture immediately
        slug_count = 0
    
        while True:
            t, v = self.read_line()
            buffer_times.append(t)
            buffer_signals.append(v)
    
            # maintain rolling buffer
            if len(buffer_times) > buffer_len:
                buffer_times.pop(0)
                buffer_signals.pop(0)
    
            # check for gas trigger
            if v < gas_threshold and (time.time() - last_capture_time) >= cooldown_s:
                slug_count += 1
                slug_name = f"slug_{slug_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                print(f"GAS DETECTED at signal {v} - capturing slug {slug_name}")
    
                # gather pre-trigger data
                capture_times = buffer_times.copy()
                capture_signals = buffer_signals.copy()
                start_t0 = capture_times[0]
    
                # capture post-trigger
                t_end = time.time() + capture_s
                while time.time() < t_end:
                    t_new, v_new = self.read_line()
                    capture_times.append(t_new)
                    capture_signals.append(v_new)
    
                # adjust timestamps to start at 0
                t0 = capture_times[0]
                capture_times_rel = [ti - t0 for ti in capture_times]
    
                # ensure folder exists
                os.makedirs(save_folder, exist_ok=True)
                csv_path = os.path.join(save_folder, f"{slug_name}.csv")
    
                # save CSV
                with open(csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp_ms", "signal"])
                    for ti, si in zip(capture_times_rel, capture_signals):
                        writer.writerow([ti, si])
    
                print(f"Slug {slug_name} saved to {csv_path}")
    
                last_capture_time = time.time()  # start cooldown
        