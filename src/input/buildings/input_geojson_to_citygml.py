import geojson
from lxml import etree
from lxml.etree import QName
import numpy as np
import re
import argparse
import os
import sys

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config import settings


class CityGMLConverter:
    def __init__(self, missing_height_imputation="average"):
        self.missing_height_imputation = missing_height_imputation
        self.default_height = 9
        self.default_level_height = 3  # default height per level in meters
        self.ns_core = "http://www.opengis.net/citygml/2.0"
        self.ns_gml = "http://www.opengis.net/gml"
        self.ns_gen = "http://www.opengis.net/citygml/generics/2.0"
        self.ns_app = "http://www.opengis.net/citygml/appearance/2.0"

    def read_geojson(self, file_path):
        with open(file_path, "r") as file:
            data = geojson.load(file)
        return data

    def create_citygml(self, geojson_data):
        # Create the CityModel element with namespaces
        city_model = etree.Element(
            QName(self.ns_core, "CityModel"),
            nsmap={
                None: self.ns_core,  # default namespace
                "gml": self.ns_gml,
                "gen": self.ns_gen,
                "app": self.ns_app,
            },
        )

        # Create the boundedBy element
        envelope = etree.SubElement(city_model, QName(self.ns_gml, "boundedBy"))
        env = etree.SubElement(
            envelope,
            QName(self.ns_gml, "Envelope"),
            srsName="EPSG:4326",
            srsDimension="3",
        )
        lower_corner = etree.SubElement(env, QName(self.ns_gml, "lowerCorner"))
        upper_corner = etree.SubElement(env, QName(self.ns_gml, "upperCorner"))

        current_bounding_box = {
            "current_smallest_x": np.inf,
            "current_smallest_y": np.inf,
            "current_smallest_height": np.inf,
            "current_greatest_x": -np.inf,
            "current_greatest_y": -np.inf,
            "current_greatest_height": -np.inf,
        }

        # Determine default height if needed
        if self.missing_height_imputation == "average":
            avg_height = []
            for feature in geojson_data["features"]:
                height = None
                for key, value in feature["properties"]["tags"].items():
                    if key == "height":

                        # Find the first numeric part
                        match = re.search(r"[-+]?\d*[.,]?\d+", value)

                        if match:
                            height_value = match.group().replace(
                                ",", "."
                            )  # normalize decimal separator
                            height_value = float(height_value)
                            avg_height.append(height_value)

                    elif height is None and key == "building:levels":
                        height = float(value) * self.default_level_height
                        avg_height.append(height)

            self.default_height = (
                np.mean(avg_height) if len(avg_height) > 0 else self.default_height
            )
        elif isinstance(self.missing_height_imputation, (int, float)):
            self.default_height = float(self.missing_height_imputation)

        for feature in geojson_data["features"]:
            # initialize height with default height
            height = self.default_height

            city_object_member = etree.SubElement(
                city_model, QName(self.ns_core, "cityObjectMember")
            )
            generic_city_object = etree.SubElement(
                city_object_member, QName(self.ns_gen, "GenericCityObject")
            )

            height = None
            for key, value in feature["properties"]["tags"].items():
                if key == "height":
                    match = re.search(r"[-+]?\d*[.,]?\d+", value)

                    if match:
                        height_value = match.group().replace(
                            ",", "."
                        )  # normalize decimal separator
                        height_value = float(height_value)
                        avg_height.append(height_value)

                elif height is None and key == "building:levels":
                    height = float(value) * self.default_level_height

            if height is None:
                height = self.default_height

            for key, value in feature["properties"].items():

                string_attribute = etree.SubElement(
                    generic_city_object, QName(self.ns_gen, "stringAttribute"), name=key
                )
                gen_value = etree.SubElement(
                    string_attribute, QName(self.ns_gen, "value")
                )
                gen_value.text = str(value)

            # Set height for bounding box
            if height > current_bounding_box["current_greatest_height"]:
                current_bounding_box["current_greatest_height"] = height
            if height < current_bounding_box["current_smallest_height"]:
                current_bounding_box["current_smallest_height"] = height

            geometry_type = feature["geometry"]["type"]
            coordinates = feature["geometry"]["coordinates"]

            if geometry_type in ("Polygon", "MultiPolygon"):
                lod4_geometry = etree.SubElement(
                    generic_city_object, QName(self.ns_gen, "lod4Geometry")
                )
                multi_solid = etree.SubElement(
                    lod4_geometry, QName(self.ns_gml, "MultiSolid"), srsDimension="3"
                )

                polygons = (
                    coordinates if geometry_type == "MultiPolygon" else [coordinates]
                )

                for polygon in polygons:
                    solid_member = etree.SubElement(
                        multi_solid, QName(self.ns_gml, "solidMember")
                    )
                    solid = etree.SubElement(solid_member, QName(self.ns_gml, "Solid"))
                    exterior = etree.SubElement(solid, QName(self.ns_gml, "exterior"))
                    composite_surface = etree.SubElement(
                        exterior, QName(self.ns_gml, "CompositeSurface")
                    )

                    current_bounding_box = self.create_block_surfaces(
                        polygon, composite_surface, height, current_bounding_box
                    )

            elif geometry_type == "Point":
                # Handle Point geometry
                lod4_geometry = etree.SubElement(
                    generic_city_object, QName(self.ns_gen, "lod4Geometry")
                )
                point = etree.SubElement(
                    lod4_geometry, QName(self.ns_gml, "Point"), srsDimension="3"
                )
                pos = etree.SubElement(point, QName(self.ns_gml, "pos"))
                x, y, *z = coordinates
                z = z[0] if z else 0
                pos.text = f"{x} {y} {z}"

        # Adding the computed bounding box
        lower_corner.text = (
            f'{current_bounding_box["current_smallest_x"]} '
            f'{current_bounding_box["current_smallest_y"]} '
            f'{current_bounding_box["current_smallest_height"]}'
        )
        upper_corner.text = (
            f'{current_bounding_box["current_greatest_x"]} '
            f'{current_bounding_box["current_greatest_y"]} '
            f'{current_bounding_box["current_greatest_height"]}'
        )

        return city_model

    def create_block_surfaces(
        self, polygon, composite_surface, height, current_bounding_box
    ):
        """
        Create top, bottom, and side surfaces to represent a block with given height.
        """
        ns_gml = self.ns_gml

        # Top surface
        surface_member = etree.SubElement(
            composite_surface, QName(ns_gml, "surfaceMember")
        )
        top_poly = etree.SubElement(surface_member, QName(ns_gml, "Polygon"))
        top_exterior = etree.SubElement(top_poly, QName(ns_gml, "exterior"))
        top_ring = etree.SubElement(top_exterior, QName(ns_gml, "LinearRing"))

        pos_list_top = etree.SubElement(top_ring, QName(ns_gml, "posList"))
        pos_list_top.text = " ".join(
            f"{x} {y} {height}" for coord in polygon[0] for x, y in [coord]
        )

        # Bottom surface
        surface_member = etree.SubElement(
            composite_surface, QName(ns_gml, "surfaceMember")
        )
        bottom_poly = etree.SubElement(surface_member, QName(ns_gml, "Polygon"))
        bottom_exterior = etree.SubElement(bottom_poly, QName(ns_gml, "exterior"))
        bottom_ring = etree.SubElement(bottom_exterior, QName(ns_gml, "LinearRing"))

        pos_list_bottom = etree.SubElement(bottom_ring, QName(ns_gml, "posList"))
        bottom_text = []
        for coord in polygon[0]:
            for x, y in [coord]:
                bottom_text.append(f"{x} {y} 0")
                if x < current_bounding_box["current_smallest_x"]:
                    current_bounding_box["current_smallest_x"] = x
                if y < current_bounding_box["current_smallest_y"]:
                    current_bounding_box["current_smallest_y"] = y
                if x > current_bounding_box["current_greatest_x"]:
                    current_bounding_box["current_greatest_x"] = x
                if y > current_bounding_box["current_greatest_y"]:
                    current_bounding_box["current_greatest_y"] = y

        pos_list_bottom.text = " ".join(bottom_text)

        # Side surfaces
        num_vertices = len(polygon[0])
        for i in range(num_vertices):
            x1, y1 = polygon[0][i]
            x2, y2 = polygon[0][(i + 1) % num_vertices]

            surface_member = etree.SubElement(
                composite_surface, QName(ns_gml, "surfaceMember")
            )
            side_poly = etree.SubElement(surface_member, QName(ns_gml, "Polygon"))
            side_exterior = etree.SubElement(side_poly, QName(ns_gml, "exterior"))
            side_ring = etree.SubElement(side_exterior, QName(ns_gml, "LinearRing"))

            pos_list_side = etree.SubElement(side_ring, QName(ns_gml, "posList"))
            pos_list_side.text = " ".join(
                [
                    f"{x1} {y1} 0",
                    f"{x2} {y2} 0",
                    f"{x2} {y2} {height}",
                    f"{x1} {y1} {height}",
                    f"{x1} {y1} 0",
                ]
            )

        return current_bounding_box

    def write_citygml(self, city_model, output_path):
        tree = etree.ElementTree(city_model)
        tree.write(
            output_path, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )

    def convert(self, input_geojson, output_citygml):
        geojson_data = self.read_geojson(input_geojson)
        city_model = self.create_citygml(geojson_data)
        self.write_citygml(city_model, output_citygml)
        print(
            f"Converted GeoJSON to CityGML successfully and saved to {output_citygml}"
        )

def parse_missing_height_imputation(val):
        if isinstance(val, str) and val.lower() == "average":
            return "average"
        try:
            return float(val)
        except (TypeError, ValueError):
            raise argparse.ArgumentTypeError(
                "missing_height_imputation must be 'average' or a numeric value"
            )

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Convert GeoJSON to CityGML")

    parser.add_argument("--geojson_input", required=True, help="Path to input GeoJSON")
    parser.add_argument(
        "--missing_height_imputation",
        type=parse_missing_height_imputation,
        default="average",
        help="Either 'average' or a numeric height (e.g. 12.5)",
    )
    parser.add_argument("--citygml_output", required=True, help="Path to output CityGML file")
    args = parser.parse_args()

    converter = CityGMLConverter(missing_height_imputation=args.missing_height_imputation)
    converter.convert(args.geojson_input, args.citygml_output)
