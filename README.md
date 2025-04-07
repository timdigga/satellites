# 🛰️ Satellite Tracker

> Real-time weather satellite tracker with interactive map visualization  
> Created by [Tim Digga](https://github.com/timdigga)

---

## 🌐 Overview

**Satellite Tracker** is a Python tool that predicts upcoming passes of popular weather satellites (like NOAA 15/18/19 and METEOR-M 2) over your current location (auto-detected via IP) and displays peak visibility moments on an interactive map.

### What it does:

- Tracks weather satellites in real time
- Calculates altitude, distance, and signal strength at pass peak
- Auto-detects your location using IP
- Generates a beautiful `HTML` map with satellite paths & markers

---

## 🖼️ Preview

Your output will look like this (open in browser):

- 📍 Blue: Your Location  
- 🔴 Red: Satellite peak pass (culmination)  
- 🟢 Green: Path ±5 min around peak  

![map-preview](https://user-images.githubusercontent.com/yourimage.png) <!-- Optional: replace with real image -->

---

## 🚀 Getting Started

### 1. Clone the Repo

```bash
git clone https://github.com/timdigga/satellite-tracker.git
cd satellite-tracker
```
### 2. Install the requirements
```
pip install -r requirements.txt
```
or 
```
pip install skyfield geocoder geopy folium
```
### 3. Run the python code

```
python satellites.py
```


