import os
import subprocess
import sys
import argparse

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config import settings

class SUMOOSMDownloader:
    def __init__(self, sumo_home=None):
        self.sumo_home = sumo_home or os.environ.get("SUMO_HOME")
        if not self.sumo_home:
            raise RuntimeError("SUMO_HOME not set. Please install SUMO and set the SUMO_HOME environment variable.")

    def download_osm(self, bbox, output_folder):
        """
        Download OSM data for SUMO using osmGet.py.

        Parameters
        ----------
        bbox : tuple (min_lon, min_lat, max_lon, max_lat)
            Bounding box to download.
        output_file : str
            File where OSM data should be saved.
        """
        osmget_path = os.path.join(self.sumo_home, "tools", "osmGet.py")
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

        cmd = [
            "python", osmget_path,
            "--bbox", bbox_str,
            "--output-dir", os.path.join(os.getcwd(), output_folder),
        ]
        print(f"Running: {' '.join(cmd)}")
        print(os.getcwd())
        result = subprocess.run(cmd, check=True)
        print(result.stdout)
        print(result.stderr)
        print(f"OSM data saved to {os.path.join(os.getcwd(), output_folder)}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--output_folder", help="")
    args = parser.parse_args()

    # Bounding box (south, west, north, east)
    bbox = (
        settings.osm_settings.bb_south_long, 
        settings.osm_settings.bb_west_lat,
        settings.osm_settings.bb_north_long,
        settings.osm_settings.bb_east_lat,
    )

    downloader = SUMOOSMDownloader()
    downloader.download_osm(bbox, args.output_folder)