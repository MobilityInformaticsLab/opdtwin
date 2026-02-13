from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pymongo import MongoClient
import requests
import threading
import time
import gtfs_realtime_pb2
import math
from datetime import datetime, timezone
import argparse

app = Flask(__name__, static_folder='static')
CORS(app)

API_KEY = ""  
VEHICLE_POSITIONS_URL = f"https://opendata.samtrafiken.se/gtfs-rt/sl/VehiclePositions.pb?key={API_KEY}"

client = MongoClient('mongodb://localhost:27017/')
db = client.gtfs_database
vehicle_collection = db.vehicle_positions

latest_vehicle_positions = []
attempts = 0
max_attempts = 100

#Modify preview_positions to a dictionary structure, saving the previous position information and the continuous avail_start
#Format: {vehicle_id: {'lat ': lat,' lon ': lon,' ts': timestamp,'avain start ': timestamp}
previous_positions = {}

def bearing_to_quaternion(bearing_deg):
    """Convert bearings (degrees) to quaternions"""
    if bearing_deg is None:
        return [0, 0, 0, 1]  # Default no rotation
    
    # Convert the bearing to radians and adjust the direction (0 degrees is due north, increasing clockwise)
    bearing_rad = math.radians(bearing_deg)
    
    # Adjust the direction of the bearing: subtract 90 degrees to make 0 degrees point due east, in accordance with the ENU coordinate system
    # converted to quaternion representation (rotating around the Z-axis)
    adjusted_bearing = bearing_rad - math.pi / 2
    
    # Calculate quaternions
    cy = math.cos(adjusted_bearing * 0.5)
    sy = math.sin(adjusted_bearing * 0.5)
    
    # Only rotate around the Z-axis (the vehicle currently does not pitch or roll)
    return [0, 0, sy, cy]  # [x, y, z, w]

def vehicles_to_czml(vehicles, realtime=True):
    """
   Generate CZML data:
-Ensure continuous availability of the same vehicle by using continuous avail_start
-Using interpolation method (adding repeated sampling points) to extend display time
    """
    czml = [{"id": "document", "name": "CZML Data", "version": "1.0"}]
    
    # Buffer time (seconds), extend visible window
    buffer_time = 10  
    for vehicle in vehicles:
        vid = vehicle.get("id", "unknown")
        current_ts = vehicle.get("timestamp", time.time())
        current_ts_iso = datetime.fromtimestamp(current_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Directly obtain bearings from vehicle data and convert them into quaternions
        bearing = vehicle.get("bearing")
        quat = bearing_to_quaternion(bearing)
        
        # Use continuous avail_start; If it does not exist, use the current time
        avail_start_ts = vehicle.get("avail_start", current_ts)
        availability_start = datetime.fromtimestamp(avail_start_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        availability_end = datetime.fromtimestamp(current_ts + buffer_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        packet = {
            "id": vid,
            "name": f"Vehicle {vid}",
            "model": {"gltf": "/static/vehicle.glb", "scale": 1.0},
            "orientation": {"unitQuaternion": quat},
            "label": {
                "text": f"{'Real-time' if realtime else 'Historical'}: {vid}\n{current_ts_iso}",
                "font": "12pt sans-serif",
                "fillColor": {"rgba": [255, 255, 255, 255]},
                "outlineColor": {"rgba": [0, 0, 0, 255]},
                "outlineWidth": 2
            },
            "availability": f"{availability_start}/{availability_end}"
        }
        
        # When there is a previous sampling point, perform interpolation
        if all(key in vehicle for key in ("prev_lat", "prev_lon", "prev_ts")):
            # dt is based on continuous avail_start calculation
            dt = current_ts - avail_start_ts
            packet["position"] = {
                "epoch": availability_start,
                "interpolationAlgorithm": "LINEAR",
                "interpolationDegree": 1,
                "cartographicDegrees": [
                    0, vehicle["prev_lon"], vehicle["prev_lat"], 0,
                    dt, vehicle["longitude"], vehicle["latitude"], 0,
                    dt + 1, vehicle["longitude"], vehicle["latitude"], 0  # Repeat the current sampling point and maintain stability
                ]
            }
        else:
            # If there is no previous sampling, only static position will be provided
            packet["position"] = {"cartographicDegrees": [vehicle["longitude"], vehicle["latitude"], 0]}
        
        czml.append(packet)
    return czml

def fetch_gtfs_rt_data():
    """
    Continuously capture GTFS data:
    -For each vehicle, record avail_start during the first sampling and keep it unchanged during subsequent updates
    -Directly use the bearing information provided by the API
    """
    global latest_vehicle_positions, attempts
    while attempts < max_attempts:
        try:
            response = requests.get(VEHICLE_POSITIONS_URL)
            response.raise_for_status()
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(response.content)
            
            vehicle_positions = []
            for entity in feed.entity:
                if entity.HasField("vehicle"):
                    v = entity.vehicle
                    cur_lat = v.position.latitude
                    cur_lon = v.position.longitude
                    vid = v.vehicle.id
                    cur_ts = time.time()
                    
                    # Obtain bearing information (if present)
                    bearing = v.position.bearing if v.position.HasField("bearing") else None
                    
                    # If the vehicle appears for the first time, set avail_start to the current time
                    if vid not in previous_positions:
                        avail_start = cur_ts
                        previous_positions[vid] = {
                            'lat': cur_lat, 
                            'lon': cur_lon, 
                            'ts': cur_ts, 
                            'avail_start': cur_ts,
                            'bearing': bearing  # Save the bearing
                        }
                    else:
                        prev_data = previous_positions[vid]
                        avail_start = prev_data.get('avail_start', cur_ts)
                    
                    data = {
                        "id": vid,
                        "latitude": cur_lat,
                        "longitude": cur_lon,
                        "timestamp": cur_ts,
                        "bearing": bearing,  # Directly store bearings
                        "avail_start": avail_start
                    }
                    # Save the previous sampling data for interpolation
                    if vid in previous_positions:
                        data.update({
                            "prev_lat": previous_positions[vid]['lat'],
                            "prev_lon": previous_positions[vid]['lon'],
                            "prev_ts": previous_positions[vid]['ts']
                        })
                    
                    # Update vehicle information, retain original avail_start and bearings
                    previous_positions[vid] = {
                        'lat': cur_lat, 
                        'lon': cur_lon, 
                        'ts': cur_ts, 
                        'avail_start': avail_start,
                        'bearing': bearing  # Save current bearing
                    }
                    
                    vehicle_collection.insert_one(data.copy())  # save to database
                    vehicle_positions.append(data)
            
            latest_vehicle_positions = vehicle_positions
            print(f"Fetched {len(vehicle_positions)} vehicles")
            attempts += 1
        except Exception as e:
            print(f"Fetch error: {e}")
        time.sleep(3)

@app.route("/vehicles")
def get_vehicles_czml():
    """Return real-time CZML data"""
    return jsonify(vehicles_to_czml(latest_vehicle_positions, realtime=True))

@app.route("/historical")
def get_historical_czml():
    """Return historical data"""
    start = request.args.get("start", type=float)
    end = request.args.get("end", type=float)
    if not start or not end:
        return jsonify({"error": "Missing start/end parameters"}), 400
    data = list(vehicle_collection.find({"timestamp": {"$gte": start, "$lte": end}}))
    return jsonify(vehicles_to_czml(data, realtime=False))

@app.route("/")
def serve_index():
    return send_from_directory("static", "index.html")

@app.route("/history_page")
def serve_history_page():
    return send_from_directory("static", "history.html")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='GTFS-RT to Cesium CZML Flask Service')
    parser.add_argument('--api-key', type=str, required=True, 
                        help='API key for accessing Samtrafiken GTFS-RT data (required)')
    args = parser.parse_args()
    
    API_KEY = args.api_key
    print(f"API key loaded successfully. Service starting...")
    import os
    # To avoid multi process startup issues in Flask Debug mode, only start the capture thread in overloaded child processes
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=fetch_gtfs_rt_data, daemon=True).start()
    app.run(debug=True)