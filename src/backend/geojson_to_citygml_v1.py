import geojson
from lxml import etree
from lxml.etree import QName
import numpy as np

def read_geojson(file_path):
    with open(file_path, 'r') as file:
        data = geojson.load(file)
    return data

def create_citygml(geojson_data, default_height=9):

    ns_core = "http://www.opengis.net/citygml/2.0"
    ns_gml = "http://www.opengis.net/gml"
    ns_gen = "http://www.opengis.net/citygml/generics/2.0"

    # Create the CityModel element with namespaces
    city_model = etree.Element(
        QName(ns_core, "CityModel"),
        nsmap={
            None: ns_core,  # default namespace
            "gml": ns_gml,
            "gen": ns_gen
        }
    )
    
    # Create the boundedBy element
    envelope = etree.SubElement(city_model, QName(ns_gml, "boundedBy"))
    env = etree.SubElement(envelope, QName(ns_gml, "Envelope"), srsName="EPSG:4326", srsDimension="3")
    lower_corner = etree.SubElement(env, QName(ns_gml, "lowerCorner"))
    upper_corner = etree.SubElement(env, QName(ns_gml, "upperCorner"))

    current_bounding_box = {
                    "current_smallest_x":  np.inf,
                    "current_smallest_y":  np.inf,
                    "current_smallest_height":  np.inf,
                    "current_greatest_x": -np.inf,
                    "current_greatest_y": -np.inf,
                    "current_greatest_height": -np.inf,
                }
    
    for feature in geojson_data['features']:

        # initialize height with default height
        height = default_height

        # Add core:cityObjectMember with gen:GenericCityObject
        city_object_member = etree.SubElement(city_model, QName(ns_core, "cityObjectMember"))
        generic_city_object = etree.SubElement(city_object_member, QName(ns_gen, "GenericCityObject"))
        
        # Add properties as string attributes
        for key, value in feature['properties'].items():
            if key == "height":
                height = float(value)

            else:
                string_attribute = etree.SubElement(generic_city_object, QName(ns_gen, "stringAttribute"), name=key)
                gen_value = etree.SubElement(string_attribute, QName(ns_gen, "value"))
                gen_value.text = str(value)  # Ensure the value is converted to string

        # Set height for bounding box
        if height > current_bounding_box["current_greatest_height"]:
            current_bounding_box["current_greatest_height"] = height
        if height < current_bounding_box["current_smallest_height"]:
            current_bounding_box["current_smallest_height"] = height
                
        # Handle geometry based on type
        geometry_type = feature['geometry']['type']
        coordinates = feature['geometry']['coordinates']
        
        if geometry_type == 'Polygon' or geometry_type == 'MultiPolygon':
            lod4_geometry = etree.SubElement(generic_city_object, QName(ns_gen, "lod4Geometry"))
            multi_solid = etree.SubElement(lod4_geometry, QName(ns_gml, "MultiSolid"), srsDimension="3")
            
            polygons = coordinates if geometry_type == 'MultiPolygon' else [coordinates]
            
            for polygon in polygons:
                solid_member = etree.SubElement(multi_solid, QName(ns_gml, "solidMember"))
                solid = etree.SubElement(solid_member, QName(ns_gml, "Solid"))
                exterior = etree.SubElement(solid, QName(ns_gml, "exterior"))
                composite_surface = etree.SubElement(exterior, QName(ns_gml, "CompositeSurface"))

                # Create surfaces for the block (top, bottom, sides)
                current_bounding_box = create_block_surfaces(polygon, composite_surface, height, current_bounding_box)

        elif geometry_type == 'Point':
            # Handle Point geometry
            lod4_geometry = etree.SubElement(generic_city_object, QName(ns_gen, "lod4Geometry"))
            point = etree.SubElement(lod4_geometry, QName(ns_gml, "Point"), srsDimension="3")
            pos = etree.SubElement(point, QName(ns_gml, "pos"))
            x, y, *z = coordinates
            z = z[0] if z else 0
            pos.text = f"{x} {y} {z}"

    # Adding the computed bounding box
    lower_corner.text = f'{current_bounding_box["current_smallest_x"]} {current_bounding_box["current_smallest_y"]} {current_bounding_box["current_smallest_height"]}'
    upper_corner.text = f'{current_bounding_box["current_greatest_x"]} {current_bounding_box["current_greatest_y"]} {current_bounding_box["current_greatest_height"]}'

    return city_model

def create_block_surfaces(polygon, composite_surface, height, current_bounding_box):
    """
    Create top, bottom, and side surfaces to represent a block with given height.
    """
    ns_gml = "http://www.opengis.net/gml"
    
    # Top surface
    surface_member = etree.SubElement(composite_surface, QName(ns_gml, "surfaceMember"))
    top_poly = etree.SubElement(surface_member, QName(ns_gml, "Polygon"))
    top_exterior = etree.SubElement(top_poly, QName(ns_gml, "exterior"))
    top_ring = etree.SubElement(top_exterior, QName(ns_gml, "LinearRing"))
    
    pos_list_top = etree.SubElement(top_ring, QName(ns_gml, "posList"))
    pos_list_top.text = " ".join(f"{x} {y} {height}" for coord in polygon[0] for x, y in [coord])

    # Bottom surface
    surface_member = etree.SubElement(composite_surface, QName(ns_gml, "surfaceMember"))
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

        surface_member = etree.SubElement(composite_surface, QName(ns_gml, "surfaceMember"))
        side_poly = etree.SubElement(surface_member, QName(ns_gml, "Polygon"))
        side_exterior = etree.SubElement(side_poly, QName(ns_gml, "exterior"))
        side_ring = etree.SubElement(side_exterior, QName(ns_gml, "LinearRing"))
        
        pos_list_side = etree.SubElement(side_ring, QName(ns_gml, "posList"))
        pos_list_side.text = " ".join([
            f"{x1} {y1} 0",
            f"{x2} {y2} 0",
            f"{x2} {y2} {height}",
            f"{x1} {y1} {height}",
            f"{x1} {y1} 0"
        ])

    return current_bounding_box

def write_citygml(city_model, output_path):
    tree = etree.ElementTree(city_model)
    tree.write(output_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")

# Example usage
input_geojson = "c:/Users/mt/Desktop/test_geojson/wholekista.geojson"
output_citygml = "c:/Users/mt/Desktop/test_geojson/output.gml"
    

geojson_data = read_geojson(input_geojson)
city_model = create_citygml(geojson_data, default_height=9)  # Set the default height here
write_citygml(city_model, output_citygml)

print(f"Converted GeoJSON to CityGML successfully and saved to {output_citygml}")
