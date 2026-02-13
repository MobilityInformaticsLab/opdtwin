import xml.etree.ElementTree as ET
import csv
import json
import os
from datetime import datetime, timedelta
import math
import numpy as np
import pandas as pd
import argparse
from collections import Counter

# Define a function to convert SUMO FCD output to the requested CSV format
def sumo_output_to_csv(xml_path, csv_path):
    # Parse the XML file
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Open the CSV file for writing
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Write the headers to the CSV file
        writer.writerow(['timestep', 'id', 'x', 'y', 'z', 'type', 'slope', 'angle'])

        # Iterate over each timestep in the XML file
        for timestep in root.findall('timestep'):
            time = timestep.get('time')

            # Iterate over each vehicle in the timestep
            for vehicle in timestep.findall('vehicle'):
                # Extract the required attributes from the vehicle element
                id = vehicle.get('id')
                x = vehicle.get('x')
                y = vehicle.get('y')
                z = vehicle.get('z') if vehicle.get('z') else '0'  # Default to 0 if not present
                vtype = vehicle.get('type') if vehicle.get('type') else 'vehicle'
                slope = vehicle.get('slope')
                angle = vehicle.get('angle')
                # Write the data to the CSV file, each attribute in its own column
                writer.writerow([time, id, x, y, z, vtype, slope, angle])

# Define a function to convert CSV to the vehilce-level CZML format
def convert_to_czml_3Dmodel(input_file, output_file, start_date, current_time):
    with open(input_file, 'r') as input_csv:
        reader = csv.DictReader(input_csv)

        czml = [{
            "id": "document",
            "version": "1.0",
            "name": "SUMOTrafficSimulationOutput",
            "clock": {
                "interval": f"{start_date.isoformat()}Z/{start_date.isoformat()}Z",
                "currentTime": (start_date + timedelta(seconds=current_time)).isoformat() + "Z",
                "multiplier": 1,
            }
        }]
        vehicle_positions = {}
        max_timestep = 0.0
        for row in reader:
            vehicle_id = row['id']
            vehicle_type = row['type']
            if vehicle_type not in ['tram', 'train', 'DEFAULT_VEHTYPE','bus']:
                print(f"Skipping type: {vehicle_type}")
                continue 
            timestep = float(row['timestep'])
            if timestep > max_timestep:
                max_timestep = timestep
            if vehicle_id not in vehicle_positions:
                if vehicle_type == 'tram':
                    model_link = './tram.glb'
                elif vehicle_type == 'train':
                    model_link = './train.glb'
                elif vehicle_type == 'bus':
                    model_link = './bus.glb'
                elif vehicle_type == 'DEFAULT_VEHTYPE':
                    model_link = './car.glb' 
                else:
                    print("No GLB data")
                vehicle_positions[vehicle_id] = {
                    "id": vehicle_id,
                    "name": vehicle_id,
                    "description": "",
                    "model": {
                        "gltf": model_link,
                    },
                    "position": {
                        "epoch": start_date.isoformat() + 'Z',
                        "cartographicDegrees": []
                    },
                    "orientation": {
                        "epoch": start_date.isoformat() + 'Z',
                        "unitQuaternion": []
                    }
                }

            # Set the z value based on the presence of the 'z' column in the CSV
            if 'z' in row:
                vehicle_positions[vehicle_id]['position']['cartographicDegrees'].extend(
                    [float(row['timestep']), float(row['x']), float(row['y']), float(row['z'])])
            else:
                vehicle_positions[vehicle_id]['position']['cartographicDegrees'].extend(
                    [float(row['timestep']), float(row['x']), float(row['y']), 0])

            # Set the orientation based on the corresponding longitude, latitude, slope (if available) and angle values in the CSV
            if 'slope' in row:
                q = get_orientation(float(row['y']), (float(row['x'])), 0, -(float(row['slope'])), (float(row['angle']))+180) #depends on orientation of 3d model in local (model) frame
                vehicle_positions[vehicle_id]['orientation']['unitQuaternion'].extend([float(row['timestep']), *q])
            else:
                q = get_orientation(float(row['y']), (float(row['x'])), 0, 0, (float(row['angle'])) + 180)  # depends on orientation of 3d model in local (model) frame
                vehicle_positions[vehicle_id]['orientation']['unitQuaternion'].extend([float(row['timestep']), *q])

        # Update the end time of the interval to the maximum timestep value
        end_date = start_date + timedelta(seconds=max_timestep)
        czml[0]['clock']['interval'] = f"{start_date.isoformat()}Z/{end_date.isoformat()}Z"

        czml.extend(vehicle_positions.values())

    with open(output_file, 'w') as output_czml:
        json.dump(czml, output_czml, indent=1)
    type_counter = Counter()
    for v in vehicle_positions.values():
        model_link = v['model']['gltf']
        if 'bus' in model_link:
            type_counter['bus'] += 1
        elif 'tram' in model_link:
            type_counter['tram'] += 1
        elif 'train' in model_link:
            type_counter['train'] += 1
        else:
            type_counter['other'] += 1

    print("Vehicle type counts in CZML output:")
    for t, count in type_counter.items():
        print(f"  {t}: {count}")
    return max_timestep

def get_orientation(lat, lon, heading, pitch, roll):
    # Convert angles to radians
    heading = np.deg2rad(heading)
    pitch = np.deg2rad(pitch)
    roll = np.deg2rad(roll)

    lat = np.deg2rad(lat)
    lon = np.deg2rad(lon)

    # Compute rotation matrix
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    R = np.array([[-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
                  [-sin_lon, cos_lon, 0],
                  [-cos_lat * cos_lon, -cos_lat * sin_lon, -sin_lat]])

    # Compute Euler angles from rotation matrix
    heading1, pitch1, roll1, heading2, pitch2, roll2 = rotationmatrix2eulerangles(R)

    # Convert to quaternions
    q_pos = euler2quaternion(heading1, pitch1, roll2)
    q_hpr = euler2quaternion(heading, pitch, roll)

    # Multiply quaternions
    quat = quaternion_multiply(q_hpr, q_pos)

    return quat

def rotationmatrix2eulerangles(R):
    r11 = R[0, 0]
    r12 = R[0, 1]
    r13 = R[0, 2]
    r21 = R[1, 0]
    r22 = R[1, 1]
    r23 = R[1, 2]
    r31 = R[2, 0]
    r32 = R[2, 1]
    r33 = R[2, 2]

    # Convert rotation matrix to Euler angles
    pitch1 = -np.arcsin(r13)
    pitch2 = math.pi - pitch1
    if np.abs(np.cos(pitch1)) < 1e-6:
        # Gimbal lock: pitch is close to +/-90 degrees
        roll1 = np.arctan2(-r21, r22)
        roll2 = np.arctan2(-r21, r22)
        heading1 = 0
        heading2 = 0
    else:
        cos_roll1 = r11 / np.cos(pitch1)
        sin_roll1 = r12 / np.cos(pitch1)
        roll1 = np.arctan2(sin_roll1, cos_roll1)
        cos_heading1 = r33 / np.cos(pitch1)
        sin_heading1 = r23 / np.cos(pitch1)
        heading1 = np.arctan2(sin_heading1, cos_heading1)

        cos_roll2 = r11 / np.cos(pitch2)
        sin_roll2 = r12 / np.cos(pitch2)
        roll2 = np.arctan2(sin_roll2, cos_roll2)
        cos_heading2 = r33 / np.cos(pitch2)
        sin_heading2 = r23 / np.cos(pitch2)
        heading2 = np.arctan2(sin_heading2, cos_heading2)

    # Return the Euler angles as individual variables
    return heading1, pitch1, roll1, heading2, pitch2, roll2

def euler2quaternion(h, p, r):
    # Convert Euler angles to quaternions
    cy_pos = math.cos(h * 0.5)
    sy_pos = math.sin(h * 0.5)
    cp_pos = math.cos(p * 0.5)
    sp_pos = math.sin(p * 0.5)
    cr_pos = math.cos(r * 0.5)
    sr_pos = math.sin(r * 0.5)

    q = np.empty((4,))
    q[0] = cy_pos * cp_pos * cr_pos + sy_pos * sp_pos * sr_pos
    q[1] = cy_pos * cp_pos * sr_pos - sy_pos * sp_pos * cr_pos
    q[2] = sy_pos * cp_pos * sr_pos + cy_pos * sp_pos * cr_pos
    q[3] = sy_pos * cp_pos * cr_pos - cy_pos * sp_pos * sr_pos

    return q

def quaternion_multiply(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + z1*w2 + x1*y2 - y1*x2

    return np.array([w, x, y, z])

def _resolve_metric_column(df, metric_name):
    if metric_name in df.columns:
        return metric_name
    lowered = {c.lower(): c for c in df.columns}
    if metric_name.lower() in lowered:
        return lowered[metric_name.lower()]
    return None


def _interpolate_color(c1, c2, t):
    return [
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
        255
    ]


def _metric_color(value, vmin, vmax):
    if value is None or math.isnan(value):
        return [150, 150, 150, 255]
    if vmax <= vmin:
        return [0, 255, 0, 255]
    t = (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))

    # Green -> Yellow -> Red
    if t < 0.5:
        return _interpolate_color([0, 255, 0], [255, 255, 0], t * 2)
    return _interpolate_color([255, 255, 0], [255, 0, 0], (t - 0.5) * 2)


def create_czml(csv_path, geojson_path, czml_path, start_date, end_date, current_time, metric_name, metric_min=None, metric_max=None):
    # Load CSV data
    csv_data = pd.read_csv(csv_path)
    csv_data['id'] = csv_data['id'].astype(str).str.strip()  # Ensure ID is a string and strip any whitespace
    metric_col = _resolve_metric_column(csv_data, metric_name)
    if not metric_col:
        raise ValueError(f"Metric column '{metric_name}' not found in CSV.")

    csv_data[metric_col] = pd.to_numeric(csv_data[metric_col], errors='coerce')
    data_min = float(csv_data[metric_col].min()) if metric_min is None else float(metric_min)
    data_max = float(csv_data[metric_col].max()) if metric_max is None else float(metric_max)

    # Load GeoJSON data
    with open(geojson_path, 'r') as file:
        geojson_data = json.load(file)

    # Initialize the CZML document with a header and a clock
    czml = [{
        "id": "document",
        "version": "1.0",
        "name": "SUMOTrafficSimulationOutput",
        "clock": {
            "interval": f"{start_date.isoformat()}Z/{end_date.isoformat()}Z",
            "currentTime": (start_date + timedelta(seconds=current_time)).isoformat() + "Z",
            "multiplier": 1,
        }
    }]

    # Process each road in GeoJSON
    for feature in geojson_data['features']:
        edge_id = str(feature['properties']['id'])
        coordinates = feature['geometry']['coordinates']
        # Ensure that every coordinate pair includes a height, here assumed to be 0
        flat_coords = [coord for pair in coordinates for coord in (pair + [0])]  # Add height 0

        # Prepare the CZML packet for this road
        czml_packet = {
            "id": edge_id,
            "name": edge_id,
            "polyline": {
                "positions": {
                    "cartographicDegrees": flat_coords
                },
                "material": {
                    "solidColor": {
                        "color": {
                            "epoch": start_date.isoformat() + "Z",
                            "rgba": []
                        }
                    }
                },
                "width": 6
            }
        }

        # If this road has corresponding noise data
        if edge_id in csv_data['id'].values:
            road_data = csv_data[csv_data['id'] == edge_id].sort_values('timestep')
            color_samples = []

            for _, row in road_data.iterrows():
                tsec = float(row['timestep'])
                metric_value = row[metric_col]
                color = _metric_color(metric_value, data_min, data_max)
                color_samples.extend([tsec,*color])
            czml_packet['polyline']['material']['solidColor']['color'] = {
                "epoch": start_date.isoformat() + "Z",
                "rgba": color_samples
            }
            czml_packet["description"] = f"edge_id: {edge_id}"
        else:
            print(f"No data for road ID {edge_id}")

        czml.append(czml_packet)

    # Save CZML to file
    with open(czml_path, 'w') as f:
        json.dump(czml, f, indent=1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process SUMO output and convert to CZML format.')
    parser.add_argument('--xml', type=str, help='Input SUMO FCD (vehicle trajectory) XML file path.')
    parser.add_argument('--csv', type=str, help='Intermediate/output CSV path for vehicle data (timestep, ID, location, etc.).')
    parser.add_argument('--road-csv', type=str, help='Input CSV path for road noise data (timestep, road ID, noise value).')
    parser.add_argument('--geojson', type=str, help='Input GeoJSON path for road data (ID, shape, coordinates).')
    parser.add_argument('--vehicles-czml', type=str, help='Output CZML path for vehicle 3D trajectory animation.')
    parser.add_argument('--roads-czml', type=str, help='Path to the output roads CZML file.')
    parser.add_argument('--start-date', type=str, help='Simulation start date (format: YYYY-MM-DD)')
    parser.add_argument('--current-time', type=int, default=0, help='Initial cursor time on Cesium timeline (seconds since start date).')
    parser.add_argument('--road-metric', type=str, default='noise', help='Road metric column to visualize (e.g., noise, speed, fuel_abs, CO2_abs).')
    parser.add_argument('--metric-min', type=float, help='Override metric minimum for color scaling.')
    parser.add_argument('--metric-max', type=float, help='Override metric maximum for color scaling.')
    # In the code, both CZMLs (vehicle and road) use the same 'current Time' (passed through command-line arguments). When two CZMLs are loaded into Cesium simultaneously, their timelines will start synchronously at the same time point.
    # currentTime: The time point displayed during the initialization of the timeline. For example, if set as the start time, the scene will play from the start time; If set to a middle point in time, the scene will start playing from that point in time.
    args = parser.parse_args()
    vehicle_max_time = 0
    if args.xml and args.csv:
        sumo_output_to_csv(args.xml, args.csv)
        print(f'The CSV file has been saved at: {args.csv}')

    if args.csv and args.vehicles_czml:
        start_date = datetime.fromisoformat(args.start_date)
        vehicle_max_time = convert_to_czml_3Dmodel(args.csv, args.vehicles_czml, start_date, args.current_time)
        print(f'3D model data extracted to {args.vehicles_czml}')
        print(f"Vehicle max time: {vehicle_max_time} seconds")

    if args.road_csv and args.geojson and args.roads_czml:
        start_date = datetime.fromisoformat(args.start_date)
        try:
            road_df = pd.read_csv(args.road_csv)
            max_road_time = road_df['timestep'].max()
            print(f"Road max time from CSV: {max_road_time} seconds")
        except Exception as e:
            print(f"Error reading road CSV: {e}")
            max_road_time = 0
        
        if vehicle_max_time > max_road_time:
            end_date = start_date + timedelta(seconds=vehicle_max_time)
            print(f"Using vehicle max time for road end_date: {vehicle_max_time} seconds")
        else:
            end_date = start_date + timedelta(seconds=max_road_time)
            print(f"Using road max time for road end_date: {max_road_time} seconds")
        create_czml(
            args.road_csv,
            args.geojson,
            args.roads_czml,
            start_date,
            end_date,
            args.current_time,
            args.road_metric,
            args.metric_min,
            args.metric_max
        )
        print(f'Road data extracted to {args.roads_czml}')




