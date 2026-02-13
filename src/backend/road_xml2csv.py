import xml.etree.ElementTree as ET
import csv
import argparse
import os
from collections import defaultdict


def _detect_edge_attributes(root):
    for interval in root.findall('interval'):
        for edge in interval.findall('edge'):
            attrs = list(edge.attrib.keys())
            if 'id' in attrs:
                attrs.remove('id')
            return attrs
    return []


def extract_complete_edge_matrix(xml_file_path, csv_file_path, fields=None):
    """
    Convert SUMO edge-based XML to a complete CSV matrix.
    Each row represents a timestep (taken as interval 'end'), and includes every edge_id.
    Missing edges are filled with 0s for requested fields.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Failed to parse XML: {e}")
        return

    if not fields:
        fields = _detect_edge_attributes(root)
        if not fields:
            print("No edge attributes found in XML.")
            return

    all_edge_ids = set()
    timestep_data = defaultdict(dict)  # {timestep -> {edge_id -> {field -> value}}}
    all_timesteps = set()

    # First pass: collect all edges and all timestep->edge mappings
    for interval in root.findall('interval'):
        timestep = float(interval.get('end'))  # Use 'end' as representative timestamp
        all_timesteps.add(timestep)

        for edge in interval.findall('edge'):
            edge_id = edge.get('id')
            all_edge_ids.add(edge_id)

            row = {}
            for field in fields:
                row[field] = edge.get(field, '0')
            timestep_data[timestep][edge_id] = row

    sorted_edge_ids = sorted(all_edge_ids)
    sorted_timesteps = sorted(all_timesteps)

    # Write CSV
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['timestep', 'id', *fields])

        for timestep in sorted_timesteps:
            for edge_id in sorted_edge_ids:
                if edge_id in timestep_data[timestep]:
                    row = timestep_data[timestep][edge_id]
                    values = [row.get(field, '0') for field in fields]
                else:
                    values = ['0' for _ in fields]

                writer.writerow([timestep, edge_id, *values])

    print(f"CSV saved to {csv_file_path}")
    print(f"Total times interval: {len(sorted_timesteps)}")
    print(f"Total unique edges: {len(sorted_edge_ids)}")
    print(f"Total rows written: {len(sorted_timesteps) * len(sorted_edge_ids)}")

# Optional CLI interface
def main():
    parser = argparse.ArgumentParser(description='Convert SUMO edge-based XML to full CSV matrix with missing values filled.')
    parser.add_argument('-i', '--input', required=True, help='Path to input XML file.')
    parser.add_argument('-o', '--output', help='Path to output CSV file.')
    parser.add_argument(
        '-f',
        '--fields',
        nargs='+',
        help='Edge attributes to include (e.g., noise speed fuel_abs CO2_abs). If omitted, all edge attributes are used.'
    )
    args = parser.parse_args()

    xml_file_path = args.input
    csv_file_path = args.output or os.path.splitext(xml_file_path)[0] + '_edge_matrix.csv'

    extract_complete_edge_matrix(xml_file_path, csv_file_path, fields=args.fields)

if __name__ == '__main__':
    main()
