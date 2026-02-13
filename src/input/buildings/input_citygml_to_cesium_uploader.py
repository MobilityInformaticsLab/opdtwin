import os
import time
import requests
import boto3
from botocore.credentials import Credentials

class CesiumIonUploader:
    def __init__(self, access_token, asset_name, description="", attribution="", asset_type="3DTILES", options=None):
        """
        Initialize uploader for Cesium ion.

        Parameters
        ----------
        access_token : str
            Your Cesium ion REST API token with sufficient scopes (assets:write, etc.).
        asset_name : str
            Name of the asset to create in ion.
        description : str
            Optional description in markdown.
        attribution : str
            Optional attribution string.
        asset_type : str
            Type of data: e.g. "3DTILES", "GEOJSON", "KML", etc. Supported by ion.
        options : dict or None
            Additional options for uploading (sourceType, clampToTerrain, baseTerrainId, etc.).
        """
        self.base_url = "https://api.cesium.com/v1"
        self.headers = {"Authorization": f"Bearer {access_token}"}
        self.asset_name = asset_name
        self.description = description
        self.attribution = attribution
        self.asset_type = asset_type
        self.options = options or {}
        self.asset_id = None
        self.upload_location = None
        self.on_complete = None

    def create_asset(self):
        """Step 1: Provide ion information about your data by creating the asset."""
        url = f"{self.base_url}/assets"
        body = {
            "name": self.asset_name,
            "description": self.description,
            "attribution": self.attribution,
            "type": self.asset_type,
            "options": self.options
        }
        resp = requests.post(url, headers=self.headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        self.asset_id = data["assetMetadata"]["id"]
        self.upload_location = data.get("uploadLocation")
        self.on_complete = data.get("onComplete")
        return data

    def upload_file(self, local_file_path, remote_file_path=None):
        """
        Step 2: Upload your file to the S3 location Cesium provided.
        """
        if self.upload_location is None:
            raise RuntimeError("Need to create asset first (call create_asset())")

        if remote_file_path is None:
            remote_file_path = os.path.basename(local_file_path)

        # Get S3 info from Cesium response
        bucket = self.upload_location["bucket"]
        prefix = self.upload_location["prefix"]
        access_key = self.upload_location["accessKey"]
        secret_key = self.upload_location["secretAccessKey"]
        session_token = self.upload_location["sessionToken"]
        endpoint = self.upload_location.get("endpoint", "https://s3.amazonaws.com")

        # Initialize boto3 S3 client with temporary credentials
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
        s3 = session.client("s3", endpoint_url=endpoint)

        # Full key path in S3
        key = f"{prefix}{remote_file_path}"

        # Upload file
        s3.upload_file(local_file_path, bucket, key)
        print(f"Uploaded {local_file_path} to S3 at {bucket}/{key}")

    def notify_asset_complete(self):
        """Step 3: Notify Cesium ion that the upload is complete."""
        if self.on_complete is None:
            raise RuntimeError("No onComplete data; cannot notify completion")

        method = self.on_complete.get("method", "POST")
        url = self.on_complete.get("url")
        if not url:
            raise RuntimeError("onComplete URL missing")

        body = self.on_complete.get("fields", {})
        resp = requests.request(method, url, headers=self.headers, json=body)
        resp.raise_for_status()

        # Handle empty responses gracefully
        if resp.status_code == 204 or not resp.content:
            return {"status": "success", "message": "Upload marked complete; no content returned."}

        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError:
            # If not JSON, return raw text
            return {"status": "success", "message": resp.text}

    def get_asset_status(self):
        """Optional: check tiling / upload status of the asset."""
        if self.asset_id is None:
            raise RuntimeError("Asset not yet created")

        url = f"{self.base_url}/assets/{self.asset_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def upload(self, local_file_path, remote_file_path=None):
        """
        Convenience method to perform the full flow: create asset, upload to S3, notify completion, check status.
        """
        self.create_asset()
        self.upload_file(local_file_path, remote_file_path)
        result = self.notify_asset_complete()
        status = self.get_asset_status()
        return {
            "asset_metadata": status,
            "upload_complete_response": result
        }


# Example usage
if __name__ == "__main__":
    ACCESS_TOKEN = "YOUR_CESIUM_ION_TOKEN"
    uploader = CesiumIonUploader(
        access_token=ACCESS_TOKEN,
        asset_name="My CityGML Asset",
        description="CityGML uploaded via script",
        attribution="My Attribution",
        asset_type="3DTILES",  # Must be 3DTILES for CityGML
        options={
            "sourceType": "CITYGML",
            "clampToTerrain": True,
            "baseTerrainId": 1
        }
    )
    local_path = "path/to/your/city_model.gml"
    result = uploader.upload(local_path)
    print("Upload flow completed. Asset metadata:")
    print(result["asset_metadata"])
