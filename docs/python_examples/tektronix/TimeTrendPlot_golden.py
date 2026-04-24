import pyvisa
import time
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize

# === Configuration ===
VISA_ADDRESS = "TCPIP::192.168.0.160::INSTR"
PLOT_FILES_DIR = "./plot_data"
CSV_FILENAME = "freq_trend_data.csv"
MAX_CSV_FILENAME = "max_acquisition_data.csv"

# === Prompt User to Select Channel (CH1 to CH8 or 1 to 8) ===
valid_channels = [f"CH{i}" for i in range(1, 9)]
while True:
    print("\nMake sure T1 Time Trend plot is enabled and active by touching the T1 waveform display\n")
    raw_input_channel = input("Enter the scope channel for frequency measurement (CH1–CH8 or 1–8): ").strip().upper()
    if raw_input_channel in valid_channels:
        user_channel = raw_input_channel
        break
    elif raw_input_channel.isdigit() and 1 <= int(raw_input_channel) <= 8:
        user_channel = f"CH{raw_input_channel}"
        break
    else:
        print("Invalid input. Please enter CH1 to CH8 or a number from 1 to 8.")

# === Prompt for acquisition mode ===
mode = input("Enter number of acquisitions (or press Enter to run continuously until Stop button is pressed on front panel): ").strip()
try:
    total_runs = int(mode)
    run_forever = False
except ValueError:
    run_forever = True
    total_runs = None
    print("Running continuously. Press Ctrl+C to stop...\n")

os.makedirs(PLOT_FILES_DIR, exist_ok=True)

rm = pyvisa.ResourceManager()
scope = rm.open_resource(VISA_ADDRESS)
scope.timeout = 70000

scope.write("*CLS")
scope.write("MEASUrement:MEAS1:TYPe FREQuency")
scope.write(f"MEASUrement:MEAS1:SOURce1 {user_channel}")
scope.write("MEASUrement:MEAS1:STATE ON")
scope.write("TRIGGER:A:MODE NORMAL")
#scope.write("MEASUrement:MEAS1:CLEar")
#scope.write("ACQUIRE:STATE Run")
scope.write('FILESystem:CWD "C:\\Temp"')

plt.ion()
fig, ax = plt.subplots(figsize=(10, 6))
ax.set_xlabel("Time (s)")
ax.set_ylabel("Frequency (MHz)")
ax.grid(True)

# === Initialize Data & State ===
df_all = pd.DataFrame({
    "Time": pd.Series(dtype="float64"),
    "Frequency": pd.Series(dtype="float64"),
    "Frequency_MHz": pd.Series(dtype="float64"),
    "AcqID": pd.Series(dtype="int64")
})
global_ymin = float('inf')
global_ymax = float('-inf')
global_max_freq = float('-inf')
global_max_time = None
max_acquisition_df = None
max_acq_id = None

csv_remote_path = CSV_FILENAME
csv_local_path = os.path.join(PLOT_FILES_DIR, CSV_FILENAME)
max_csv_path = os.path.join(PLOT_FILES_DIR, MAX_CSV_FILENAME)
acquisition_count = 0

try:
    while True:
        if not run_forever and acquisition_count >= total_runs:
            break
        scope.write("MEASUrement:MEAS1:CLEar")
        scope.write("ACQUIRE:STATE Run")
        trigger_state = scope.query("TRIGger:STATE?").strip()
        acquire_state = scope.query("ACQuire:STATE?").strip()

        if acquire_state == "0" and run_forever:
            print("[STOP] Scope has stopped acquiring. Exiting loop.")
            break

        if trigger_state == "TRIGGER":
            acquisition_count += 1
            print(f"\nStarting acquisition {acquisition_count}...")

            scope.write("PLOT:PLOT1:TYPe MEASUREMENTTREND")
            scope.write("DISplay:SELect:VIEW PLOTVIEW1")
            scope.query("*OPC?")

            scope.write(f'SAVe:PLOTData "{csv_remote_path}"')

            while scope.query("BUSY?").strip() == "1":
                time.sleep(0.1)

            scope.query("*OPC?")
            scope.write(f'FILESystem:READFile "{csv_remote_path}"')
            raw_data = scope.read_raw()

            with open(csv_local_path, "wb") as f:
                f.write(raw_data)
            print(f"Saved and retrieved: {csv_local_path}")

            try:
                if os.path.getsize(csv_local_path) == 0:
                    print("⚠️ CSV file is empty. Skipping this acquisition.")
                    continue

                df = pd.read_csv(csv_local_path)
                df.columns = [col.strip() for col in df.columns]
                df.rename(columns={"X: (s)": "Time", "Y: (Hz)": "Frequency"}, inplace=True)
                df["Time"] = pd.to_numeric(df["Time"], errors="coerce")
                df["Frequency"] = pd.to_numeric(df["Frequency"], errors="coerce")
                df.dropna(subset=["Time", "Frequency"], inplace=True)
                df["Frequency_MHz"] = df["Frequency"] / 1e6
                df["AcqID"] = acquisition_count
                if not df.empty:
                    df_all = pd.concat([df_all, df], ignore_index=True)

                ax.clear()
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Frequency (MHz)")
                ax.grid(True)

                # === Plot each acquisition separately to avoid connecting lines ===
                for aid in df_all["AcqID"].unique():
                    df_segment = df_all[df_all["AcqID"] == aid]
                    x = df_segment["Time"].values
                    y = df_segment["Frequency_MHz"].values
                    if len(x) > 1:
                        points = np.array([x, y]).T.reshape(-1, 1, 2)
                        segments = np.concatenate([points[:-1], points[1:]], axis=1)
                        lc = LineCollection(segments, cmap='plasma', norm=Normalize(y.min(), y.max()))
                        lc.set_array(y[:-1])
                        lc.set_linewidth(2)
                        ax.add_collection(lc)

                ax.plot([], [], color='black', label=f"Total acquisitions: {acquisition_count}")

                new_max_idx = df["Frequency_MHz"].idxmax()
                new_max_freq = df.at[new_max_idx, "Frequency_MHz"]
                new_max_time = df.at[new_max_idx, "Time"]

                # Check if this frequency is the global max and preserve full acquisition
                if new_max_freq > global_max_freq and not df.empty and new_max_freq in df["Frequency_MHz"].values:
                    global_max_freq = new_max_freq
                    global_max_time = new_max_time
                    max_acq_id = acquisition_count
                    max_acquisition_df = df_all[df_all["AcqID"] == max_acq_id].copy()
                    max_acquisition_df.to_csv(max_csv_path, index=False)

                    # === Save max acquisition info only ===
                    print(f"📁 Saved acquisition with global max to {max_csv_path}")
                    print(f"📁 Saved acquisition with global max to {max_csv_path}")

                ax.axhline(global_max_freq, color='red', linestyle='--', linewidth=1.5,
                           label=f"Global Max: {global_max_freq:.2f} MHz")

                ymin = df_all["Frequency_MHz"].min()
                ymax = df_all["Frequency_MHz"].max()
                y_margin = (ymax - ymin) * 0.2 or 1
                ymin = round(ymin - y_margin, 2)
                ymax = round(ymax + y_margin, 2)

                global_ymin = min(global_ymin, ymin)
                global_ymax = max(global_ymax, ymax)
                ax.set_ylim(global_ymin, global_ymax)

                xmin = df_all["Time"].min()
                xmax = df_all["Time"].max()
                x_margin = (xmax - xmin) * 0.1 or 1e-9
                ax.set_xlim(round(xmin - x_margin, 10), round(xmax + x_margin, 10))

                ax.set_title(f"Live Frequency Trend from {user_channel} | Total acquisitions: {acquisition_count}")
                ax.legend()
                plt.pause(0.1)

                # Save full cumulative plot after every acquisition
                full_plot_path = os.path.join(PLOT_FILES_DIR, "frequency_trend_plot.png")
                fig.savefig(full_plot_path)
                print(f"📊 Saved full trend plot to: {full_plot_path}")

            except Exception as e:
                print(f"Error processing CSV data: {e}")
        else:
            time.sleep(0.05)

except Exception as ex:
    print(f"Unexpected error: {ex}")

finally:
    plt.ioff()
    plt.tight_layout()
    plot_filename = os.path.join(PLOT_FILES_DIR, "frequency_trend_plot.png")
    plt.savefig(plot_filename)
    plt.show()

    # === Show max acquisition plot once at end ===
    if max_acquisition_df is not None:
        max_acquisition_df = max_acquisition_df[max_acquisition_df["AcqID"] == max_acq_id]
        fig_max, ax_max = plt.subplots(figsize=(10, 6))
        ax_max.set_xlabel("Time (s)")
        ax_max.set_ylabel("Frequency (MHz)")
        ax_max.grid(True)

        x_max = max_acquisition_df["Time"].values
        y_max = max_acquisition_df["Frequency_MHz"].values

        if len(x_max) > 1:
            points_max = np.array([x_max, y_max]).T.reshape(-1, 1, 2)
            segments_max = np.concatenate([points_max[:-1], points_max[1:]], axis=1)
            lc_max = LineCollection(segments_max, cmap='plasma', norm=Normalize(y_max.min(), y_max.max()))
            lc_max.set_array(y_max[:-1])
            lc_max.set_linewidth(2)
            ax_max.add_collection(lc_max)
        ax_max.plot(x_max, y_max, color='gray', linestyle='-', linewidth=1, alpha=0.6)

        ax_max.axhline(global_max_freq, color='red', linestyle='--', linewidth=1.5,
                       label=f"Global Max: {global_max_freq:.2f} MHz (Acq {max_acq_id})")
        ax_max.set_title(f"Max Acquisition Frequency Trend (Acq {max_acq_id})")
        ax_max.legend()
        plt.tight_layout()
        max_plot_path = os.path.join(PLOT_FILES_DIR, "max_acquisition_plot.png")
        fig_max.savefig(max_plot_path)
        fig_max.show()
    print(f"📊 Full trend plot saved to: {plot_filename}")
    print(f"📁 Plot saved to: {plot_filename}")
    plt.show()
    scope.close()
    rm.close()




