Cesium.Ion.defaultAccessToken = '';// Your API Key

var viewer = new Cesium.Viewer('cesiumContainer', {
  baseLayerPicker: true,
  // Use OpenStreetMaps
  baseLayer: new Cesium.ImageryLayer(new Cesium.OpenStreetMapImageryProvider({
    url: "https://tile.openstreetmap.org/"
  })),
});

async function loadData() {
  try {

    // Load CZML data for 3D models
    var czml3DModelsUrl = '../czml_3Dmodels_test20250422test.czml'; // Adjust the path as necessary
    var modelsDataSource = await Cesium.CzmlDataSource.load(czml3DModelsUrl);
    viewer.dataSources.add(modelsDataSource);
    viewer.zoomTo(modelsDataSource);

    // Load CZML data for road information
    var roadNoiseCzmlUrl = '../kistaroad_noise_visualization.czml'; // Adjust the path as necessary
    var roadNoiseDataSource = await Cesium.CzmlDataSource.load(roadNoiseCzmlUrl);
    viewer.dataSources.add(roadNoiseDataSource);
    viewer.zoomTo(roadNoiseDataSource);

    // Load and zoom to the first tileset (whole Kista citygml)
    const tileset1 = await Cesium.Cesium3DTileset.fromIonAssetId(2539914);// you should change the ID to your AssetID in Cesium ion
    viewer.scene.primitives.add(tileset1);
    await viewer.zoomTo(tileset1);
  } catch (error) {
    console.error("Failed to load data: ", error);
  }
}

loadData();



