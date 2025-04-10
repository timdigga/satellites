import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
import webbrowser
import folium
from datetime import datetime, timedelta
from skyfield.api import load, wgs84, utc
from geopy.geocoders import Nominatim
from folium import Circle

CONFIG_FILE = "orbitron_style_config.json"

TLE_PRESETS = {
    "Weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "NOAA": "https://celestrak.org/NORAD/elements/gp.php?GROUP=noaa&FORMAT=tle",
    "ISS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
    "Starlink": "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
    "GPS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=gps-ops&FORMAT=tle",
    "GLONASS": "https://celestrak.org/NORAD/elements/gp.php?GROUP=glo-ops&FORMAT=tle",
    "Galileo": "https://celestrak.org/NORAD/elements/gp.php?GROUP=galileo&FORMAT=tle",
    "Iridium": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium&FORMAT=tle",
    "Science": "https://celestrak.org/NORAD/elements/gp.php?GROUP=science&FORMAT=tle",
    "Cubesats": "https://celestrak.org/NORAD/elements/gp.php?GROUP=cubesat&FORMAT=tle"
}

FILTERED_GROUPS = {
    "NOAA": ["NOAA 15", "NOAA 18", "NOAA 19"],
    "ISS": ["ISS (ZARYA)"],
    "Starlink": ["STARLINK"],
    "GPS": ["GPS"],
    "GLONASS": ["GLONASS"],
    "Galileo": ["GALILEO"],
    "Iridium": ["IRIDIUM"]
}

class SatelliteTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🛰️ Orbitron-style Satellite Tracker")
        self.geometry("1100x700")
        self.configure(bg="#0f172a")

        self.custom_location = None
        self.sat_objects = {}
        self.checkbox_vars = {}
        self.tle_group_vars = {}

        self.build_ui()
        self.load_configuration()
        self.auto_refresh_minutes = 5
        self.auto_refresh()

    def build_ui(self):
        sidebar = tk.Frame(self, bg="#1e293b", width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(sidebar, text="🛰️ TLE Groups", fg="white", bg="#1e293b", font=("Segoe UI", 12, "bold")).pack(pady=10)

        for group in TLE_PRESETS:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(sidebar, text=group, variable=var, fg="white", bg="#1e293b", anchor="w", selectcolor="#334155")
            chk.pack(anchor="w", padx=10)
            self.tle_group_vars[group] = var

        # DOWNLOAD BUTTON with loading behavior
        self.load_button = ttk.Button(
            sidebar,
            text="⬇️ Load TLEs",
            command=lambda: threading.Thread(target=self.download_tles).start()
        )
        self.load_button.pack(pady=10)

        tk.Label(sidebar, text="📡 Satellites", fg="white", bg="#1e293b", font=("Segoe UI", 12, "bold")).pack(pady=(20, 5))

        canvas = tk.Canvas(sidebar, bg="#1e293b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(sidebar, orient="vertical", command=canvas.yview)
        container = tk.Frame(canvas, bg="#1e293b")
        canvas.create_window((0, 0), window=container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.checkbox_vars_frame = container

        right = tk.Frame(self, bg="#0f172a")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.output = tk.Text(right, height=25, bg="#1e293b", fg="#f8fafc", font=("Courier New", 10))
        self.output.pack(fill=tk.BOTH, expand=True, pady=10)

        controls = tk.Frame(right, bg="#0f172a")
        controls.pack()

        self.loc_entry = ttk.Entry(controls, width=40)
        self.loc_entry.insert(0, "Enter city or lat,lng")
        self.loc_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(controls, text="📍 Set Location", command=self.set_location).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="🔁 Track Now", command=lambda: threading.Thread(target=self.track_satellites).start()).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="🌐 Map", command=lambda: webbrowser.open("satellite_map.html")).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="💾 Save", command=self.save_configuration).pack(side=tk.LEFT, padx=5)

    def log(self, msg):
        self.output.insert(tk.END, msg + "\n")
        self.output.see(tk.END)

    def set_location(self):
        val = self.loc_entry.get().strip()
        try:
            if "," in val:
                lat, lon = map(float, val.split(","))
            else:
                geo = Nominatim(user_agent="sat_tracker")
                loc = geo.geocode(val)
                if not loc:
                    raise ValueError("Location not found.")
                lat, lon = loc.latitude, loc.longitude
            self.custom_location = (lat, lon)
            self.log(f"📍 Location set: {lat:.4f}, {lon:.4f}")
        except Exception as e:
            self.log(f"❌ Location error: {e}")

    def download_tles(self):
        self.load_button.config(text="⏳ Downloading...", state=tk.DISABLED)
        self.log("📡 Downloading selected TLE groups...")
        self.sat_objects.clear()
        selected_groups = [name for name, var in self.tle_group_vars.items() if var.get()]
        if not selected_groups:
            self.log("⚠️ No TLE groups selected.")
            self.reset_download_button()
            return

        for group in selected_groups:
            url = TLE_PRESETS[group]
            try:
                sats = load.tle_file(url)
                group_count = 0
                for sat in sats:
                    if group in FILTERED_GROUPS:
                        if not any(sat.name.startswith(prefix) for prefix in FILTERED_GROUPS[group]):
                            continue
                    self.sat_objects[sat.name] = sat
                    group_count += 1
                self.log(f"✅ Loaded {group_count} satellites from {group}")
            except Exception as e:
                self.log(f"❌ Error loading {group}: {e}")

        self.refresh_satellite_checkboxes()
        self.load_button.config(text="✅ Done!")
        self.after(2000, self.reset_download_button)

    def reset_download_button(self):
        self.load_button.config(text="⬇️ Load TLEs", state=tk.NORMAL)

    def refresh_satellite_checkboxes(self):
        for widget in self.checkbox_vars_frame.winfo_children():
            widget.destroy()
        self.checkbox_vars.clear()
        for name in sorted(self.sat_objects.keys()):
            var = tk.BooleanVar()
            chk = tk.Checkbutton(self.checkbox_vars_frame, text=name, variable=var, fg="white", bg="#1e293b", anchor="w", selectcolor="#334155")
            chk.pack(fill="x", padx=10)
            self.checkbox_vars[name] = var

    def track_satellites(self):
        self.output.delete("1.0", tk.END)
        ts = load.timescale()

        if not self.custom_location:
            self.log("⚠️ Set a location first.")
            return

        lat, lon = self.custom_location
        location = wgs84.latlon(lat, lon)
        m = folium.Map(location=[lat, lon], zoom_start=3, tiles="cartodb dark_matter")
        folium.Marker([lat, lon], tooltip="Your Location").add_to(m)
        folium.Circle([lat, lon], radius=2500000, color='blue', fill=True, fill_opacity=0.05).add_to(m)

        selected = [name for name, var in self.checkbox_vars.items() if var.get()]
        if not selected:
            self.log("⚠️ No satellites selected.")
            return

        for name in selected:
            sat = self.sat_objects.get(name)
            if not sat:
                continue
            self.log(f"\n🔭 {name}")
            try:
                t0 = ts.now()
                pos = wgs84.subpoint(sat.at(t0))
                folium.Marker(
                    [pos.latitude.degrees, pos.longitude.degrees],
                    tooltip=f"{name} (Real-time)",
                    icon=folium.Icon(color="red")
                ).add_to(m)
                folium.Circle(
                    [pos.latitude.degrees, pos.longitude.degrees],
                    radius=2500e3,
                    color='orange',
                    fill=True,
                    fill_opacity=0.05
                ).add_to(m)
            except Exception as e:
                self.log(f"⚠️ {name} error: {e}")

        m.save("satellite_map.html")
        self.log("✅ Map saved: satellite_map.html")

    def save_configuration(self):
        config = {
            "location": self.custom_location,
            "selected": [name for name, var in self.checkbox_vars.items() if var.get()]
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
        self.log("💾 Config saved.")

    def load_configuration(self):
        if not os.path.exists(CONFIG_FILE):
            return
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        self.custom_location = tuple(cfg.get("location", ()))
        selected = cfg.get("selected", [])
        for name in selected:
            if name in self.checkbox_vars:
                self.checkbox_vars[name].set(True)
        self.log("📂 Config loaded.")

    def auto_refresh(self):
        threading.Thread(target=self.track_satellites).start()
        self.after(self.auto_refresh_minutes * 60 * 1000, self.auto_refresh)

if __name__ == "__main__":
    SatelliteTrackerApp().mainloop()
