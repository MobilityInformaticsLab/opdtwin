import time
import requests
import geojson
import os
import sys
import argparse
from osm2geojson import json2geojson

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config import settings


class OSMBuildingDownloader:
    def __init__(
        self,
        overpass_url="https://overpass-api.de/api/interpreter",
        max_retries=5,
        backoff_factor=2,
        min_delay=1.0,
    ):
        """
        Initialize the downloader with retry and rate-limiting settings.

        Parameters
        ----------
        overpass_url : str
            Overpass API endpoint.
        max_retries : int
            Maximum number of retries if the request fails.
        backoff_factor : int
            Exponential backoff multiplier for retries.
        min_delay : float
            Minimum delay (seconds) between requests (rate limit).
        """
        self.overpass_url = overpass_url
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.min_delay = min_delay
        self._last_request_time = 0

    def build_query(self, bbox):
        """
        Build the Overpass query for buildings within a bounding box.
        bbox: (south, west, north, east)
        """
        south, west, north, east = bbox
        query = f"""
        [out:json][timeout:60];
        (
          way["building"]({south},{west},{north},{east});
          relation["building"]({south},{west},{north},{east});
        );
        out body;
        >;
        out skel qt;
        """
        return query

    def _respect_rate_limit(self):
        """Ensure a minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

    def download_buildings(self, bbox):
        """
        Download building data for a bounding box with retries and backoff.
        """
        query = self.build_query(bbox)
        attempt = 0

        while attempt < self.max_retries:
            self._respect_rate_limit()
            try:
                response = requests.post(
                    self.overpass_url, data={"data": query}, timeout=120
                )
                response.raise_for_status()
                self._last_request_time = time.time()
                return response.json()
            except (requests.exceptions.RequestException, ValueError) as e:
                wait_time = self.backoff_factor**attempt
                print(f"Request failed (attempt {attempt+1}/{self.max_retries}): {e}")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                attempt += 1

        raise RuntimeError("Failed to fetch data from Overpass API after retries")

    def osm_to_geojson(self, osm_json):
        """
        Convert Overpass JSON result to GeoJSON FeatureCollection.
        """
        features = json2geojson(osm_json)
        return geojson.FeatureCollection(features)

    def download_as_geojson(self, bbox, output_path):
        """
        Download OSM building data for bbox and save as GeoJSON file.
        """
        osm_data = self.download_buildings(bbox)
        geojson_data = self.osm_to_geojson(osm_data)

        with open(output_path, "w", encoding="utf-8") as f:
            geojson.dump(geojson_data, f, indent=2)

        print(f"Saved {len(geojson_data.features)} buildings to {output_path}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--output", help="")
    args = parser.parse_args()

    # Bounding box (south, west, north, east)
    bbox = (
        settings.osm_settings.bb_south_long,
        settings.osm_settings.bb_west_lat,
        settings.osm_settings.bb_north_long,
        settings.osm_settings.bb_east_lat,
    )

    downloader = OSMBuildingDownloader(max_retries=5, backoff_factor=2, min_delay=1.5)
    downloader.download_as_geojson(bbox, args.output)
