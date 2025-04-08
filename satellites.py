import geocoder
from skyfield.api import load, wgs84, utc
from datetime import datetime, timedelta
import time
import folium
from geopy.distance import geodesic


def display_menu():
    print("""
    ################################################
    #                                              #
    #             SATELLITE TRACKER                #
    #                                              #
    #                by Tim Digga                 #
    #    GitHub: https://github.com/timdigga       #
    #                                              #
    ################################################
    """)


def get_user_location():
    choice = input("\n🌍 Standort automatisch erkennen? (j/n): ").lower()
    if choice == 'j':
        g = geocoder.ip('me')
        if g.ok and g.latlng:
            return g.latlng
        else:
            print("⚠️ Konnte Standort nicht erkennen. Standard: Berlin.")
            return 52.5200, 13.4050
    else:
        try:
            lat = float(input("Breitengrad eingeben: "))
            lon = float(input("Längengrad eingeben: "))
            return lat, lon
        except:
            print("❌ Ungültige Eingabe. Standard: Berlin.")
            return 52.5200, 13.4050


def create_map(location):
    return folium.Map(
        location=location,
        zoom_start=4,
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='Map data © OpenStreetMap contributors'
    )


# Run program
display_menu()

# List of satellites to track
satellite_names = ["NOAA 15", "NOAA 18", "NOAA 19", "METEOR-M 2"]

# Load satellite data (TLEs)
stations_url = 'https://celestrak.org/NORAD/elements/weather.txt'
stations = load.tle_file(stations_url)
by_name = {sat.name: sat for sat in stations if sat.name in satellite_names}

# Load time scale
ts = load.timescale()

# Get user's location
latitude, longitude = get_user_location()
print(f"📍 Your location: {latitude:.4f}, {longitude:.4f}")
location = wgs84.latlon(latitude, longitude)

# Create map
m = create_map([latitude, longitude])
folium.Marker([latitude, longitude], tooltip="Your Location", icon=folium.Icon(color="blue")).add_to(m)

# Loop through each satellite
for name, sat in by_name.items():
    print(f"\n🔭 Checking satellite: {name}")
    difference = sat - location

    # Time window: now to 24 hours ahead
    t0 = ts.now()
    t1 = ts.utc((datetime.utcnow() + timedelta(hours=24)).replace(tzinfo=utc))

    # Find visible passes
    times, events = sat.find_events(location, t0, t1, altitude_degrees=10.0)

    for ti, event in zip(times, events):
        event_name = ('rise', 'culminate', 'set')[event]
        if event_name == "culminate":
            alt, az, _ = difference.at(ti).altaz()
            sat_position = wgs84.subpoint(sat.at(ti))
            sat_lat = sat_position.latitude.degrees
            sat_lon = sat_position.longitude.degrees
            distance_km = geodesic((latitude, longitude), (sat_lat, sat_lon)).km

            # Estimate signal strength
            if alt.degrees >= 60:
                strength = "Strong"
            elif alt.degrees >= 30:
                strength = "Moderate"
            else:
                strength = "Weak"

            print(f"  -> Peak pass at {ti.utc_strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"     Altitude: {alt.degrees:.1f}°, Distance: {distance_km:.1f} km, Signal: {strength}")

            # Add marker at peak location
            folium.Marker(
                [sat_lat, sat_lon],
                tooltip=f"{name} (Peak)",
                popup=f"{ti.utc_strftime('%Y-%m-%d %H:%M:%S')} UTC\nDistance: {distance_km:.1f} km\nSignal: {strength}",
                icon=folium.Icon(color="red", icon="satellite", prefix='fa')
            ).add_to(m)

            # Draw path around peak (±5 minutes, every 2 minutes)
            points = []
            for minutes in range(-5, 6, 2):
                t_fly = ts.utc((ti.utc_datetime() + timedelta(minutes=minutes)).replace(tzinfo=utc))
                pos = wgs84.subpoint(sat.at(t_fly))
                lat = pos.latitude.degrees
                lon = pos.longitude.degrees
                points.append((lat, lon))

                # Add circle marker with timestamp
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    color='green',
                    fill=True,
                    fill_opacity=0.7,
                    popup=f"{name}\n{t_fly.utc_strftime('%Y-%m-%d %H:%M:%S')} UTC"
                ).add_to(m)

            folium.PolyLine(points, color="red", weight=2.5, opacity=0.6).add_to(m)

# Save the interactive map
m.save("satellite_tracking_map.html")
print("\n🗺️ Map saved as 'satellite_tracking_map.html' — open it in your browser!")

print("Visit : https://github.com/timdigga")

# Keep script alive (like original)
while True:
    time.sleep(1)
