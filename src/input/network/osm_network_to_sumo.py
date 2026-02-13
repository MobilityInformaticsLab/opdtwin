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


class SUMONetworkBuilder:
    def __init__(self, sumo_home=None):
        self.sumo_home = sumo_home or os.environ.get("SUMO_HOME")
        if not self.sumo_home:
            raise RuntimeError("SUMO_HOME not set. Please install SUMO and set the SUMO_HOME environment variable.")

    def build_network(
        self,
        osm_file,
        output_folder,
        vehicle_classes="all",
        type_file=None,
        netconvert_options=None,
    ):
        """
        Build a SUMO network from an OSM file using osmBuild.py.

        Parameters
        ----------
        osm_file : str
            Path to the OSM file (downloaded with osmGet.py).
        vehicle_classes : str
            Vehicle classes to include (all|road|publicTransport|passenger).
        type_file : str or None
            Optional typemap file for converting OSM road types.
        netconvert_options : list[str] or None
            Extra options passed to netconvert.
        """
        osm_build_path = os.path.join(self.sumo_home, "tools", "osmBuild.py")

        cmd = [
            "python", osm_build_path,
            "--osm-file", osm_file,
            "--vehicle-classes", vehicle_classes,
            "-d", output_folder,
        ]

        if type_file:
            cmd += ["--type-file", type_file]

        if netconvert_options:
            cmd += ["--netconvert-options", ",".join(netconvert_options)]

        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--input_osm_net", help="")
    parser.add_argument("--output_folder", help="")
    args = parser.parse_args()


    network_builder = SUMONetworkBuilder()
    network_result = network_builder.build_network(
        osm_file=args.input_osm_net,
        output_folder=args.output_folder,
        vehicle_classes="all",
    )
