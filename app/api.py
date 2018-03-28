from flask import Flask, jsonify, redirect, request
import flask_cors
from flasgger import Swagger
import ee

import error_handler

# import connexion

# app = connexion.App(__name__, specification_dir='.')
# app.add_api('api.yaml')

# create app
app = Flask(__name__)

app.register_blueprint(error_handler.error_handler)

# register specs
Swagger(app, template_file='api.yaml')

band_names = {
    's2': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B10',
           'B11', 'B12'],
    'readable': ['coastal', 'blue', 'green', 'red', 'red2', 'red3', 'red4',
                 'nir', 'nir2', 'water_vapour', 'cirrus', 'swir', 'swir2']
}

# style using legger colors
legger_style = '\
  <RasterSymbolizer>\
    <ColorMap  type="intervals" extended="false" >\
      <ColorMapEntry color="#BDEEFF" quantity="1" label="Water"/>\
      <ColorMapEntry color="#FF817E" quantity="2" label="Verhard oppervlak"/>\
      <ColorMapEntry color="#EEFAD4" quantity="3" label="Gras en Akker"/>\
      <ColorMapEntry color="#DEBDDE" quantity="4" label="Riet en Ruigte"/>\
      <ColorMapEntry color="#73BF73" quantity="5" label="Bos"/>\
      <ColorMapEntry color="#D97A36" quantity="6" label="Struweel"/>\
      <ColorMapEntry color="#000000" quantity="10" label="Unknown"/>\
    </ColorMap>\
  </RasterSymbolizer>'

legger_classes = {
    'Water': 1,
    'Verhard oppervlak': 2,
    'Gras en Akker': 3,
    'Riet en Ruigte': 4,
    'Bos': 5,
    'Struweel': 6,
    '': 0
}

legger_classes = ee.Dictionary(legger_classes)

classes_legger = ee.Dictionary.fromLists(
  legger_classes.values().map(lambda o: ee.Number(o).format('%d')),
  legger_classes.keys()
)

# style using legger colors
legger_style = '\
  <RasterSymbolizer>\
    <ColorMap  type="intervals" extended="false" >\
      <ColorMapEntry color="#BDEEFF" quantity="1" label="Water"/>\
      <ColorMapEntry color="#FF817E" quantity="2" label="Verhard oppervlak"/>\
      <ColorMapEntry color="#EEFAD4" quantity="3" label="Gras en Akker"/>\
      <ColorMapEntry color="#DEBDDE" quantity="4" label="Riet en Ruigte"/>\
      <ColorMapEntry color="#73BF73" quantity="5" label="Bos"/>\
      <ColorMapEntry color="#D97A36" quantity="6" label="Struweel"/>\
      <ColorMapEntry color="#000000" quantity="10" label="Unknown"/>\
    </ColorMap>\
  </RasterSymbolizer>'

legger_classes = {
    'Water': 1,
    'Verhard oppervlak': 2,
    'Gras en Akker': 3,
    'Riet en Ruigte': 4,
    'Bos': 5,
    'Struweel': 6,
    '': 0
}

legger_classes = ee.Dictionary(legger_classes)


def to_date_time_string(millis):
    return ee.Date(millis).format('YYYY-MM-dd HH:mm')


def get_sentinel_images(region, date_begin, date_end):
    images = ee.ImageCollection('COPERNICUS/S2') \
        .select(band_names['s2'], band_names['readable']) \
        .filterBounds(region)

    if date_begin:
        if not date_end:
            date_end = date_begin.advance(1, 'day')

        images = images.filterDate(date_begin, date_end)

    return images


def add_vis_parameter(vis, param, value):
    """
    Adds parameter to vis dictionary if not exsit
    :param vis:
    :param param:
    :param value:
    :return:
    """
    if param not in vis:
        vis[param] = value

    return vis


def visualize_image(image, vis):
    if not vis:
        vis = {}

    min = 0.05
    max = [0.35, 0.35, 0.45]
    gamma = 1.4

    vis = add_vis_parameter(vis, 'min', min)
    vis = add_vis_parameter(vis, 'min', max)
    vis = add_vis_parameter(vis, 'gamma', gamma)

    return image.visualize(**vis)


def get_sentinel_image(region, date_begin, date_end, vis):
    images = get_sentinel_images(region, date_begin, date_end)

    image = ee.Image(images.mosaic()).divide(10000)

    image = visualize_image(image, vis)

    return image


def get_ndvi(region, date_begin, date_end, vis):
    images = get_sentinel_images(region, date_begin, date_end) \
        .map(lambda i: i.resample('bilinear'))

    image = ee.Image(images.mosaic()).divide(10000)

    ndvi = image.normalizedDifference(['nir', 'red'])

    if not vis:
        vis = {}

    # set default vis parameters if not provided

    palette = ['000000', '252525', '525252', '737373', '969696', 'bdbdbd',
               'd9d9d9', 'f0f0f0', 'ffffff', 'f7fcf5', 'e5f5e0', 'c7e9c0',
               'a1d99b', '74c476', '41ab5d', '238b45', '006d2c', '00441b']
    min = -1
    max = 1

    vis = add_vis_parameter(vis, 'palette', palette)
    vis = add_vis_parameter(vis, 'min', min)
    vis = add_vis_parameter(vis, 'max', max)

    return ndvi.visualize(**vis)


def _get_landuse(region, date_begin, date_end, vis):
    training_asset_id = 'users/gertjang/trainingsetWaal25012018_UTM'
    validation_asset_id = 'users/gertjang/validationsetWaal25012018_UTM'
    training_image_id = 'COPERNICUS/S2/20170526T105031_20170526T105518_T31UFT'
    # bounds_asset_id = 'users/cindyvdvries/vegetatiemonitor/beheergrens'
    bounds_asset_id = 'users/gena/beheergrens-geo'

    bounds = ee.FeatureCollection(bounds_asset_id)

    # get an image given region and dates
    images = get_sentinel_images(region, date_begin, date_end) \
        .map(lambda i: i.resample('bilinear'))

    image = ee.Image(images.mosaic()).divide(10000)

    # train classifier using specific image
    imageTraining = ee.Image(training_image_id) \
        .select(band_names['s2'], band_names['readable']) \
        .resample('bilinear') \
        .divide(10000)

    trainingSet = ee.FeatureCollection(training_asset_id)

    # sample image values
    training = imageTraining.sampleRegions(
        collection=trainingSet,
        properties=['GrndTruth'],
        scale=10)

    # train random forest classifier
    classifier = ee.Classifier.randomForest(10) \
        .train(training, 'GrndTruth')

    # classify image
    classified = image.classify(classifier) \
        .clip(bounds) \
        # .focal_mode(10, 'circle', 'meters')

    original_classes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                        16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]

    legger_classes = [1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 0, 2, 3, 3,
                      3, 4, 4, 4, 5, 5, 5, 6, 5, 5, 0]

    classified = classified.remap(original_classes, legger_classes)

    mask = classified \
        .eq([1, 2, 3, 4, 5, 6]) \
        .reduce(ee.Reducer.anyNonZero())

    return classified \
        .updateMask(mask)

    # TODO: return as additional info in reply
    # get confusion matrix and training accurracy
    # trainAccuracy = classifier.confusionMatrix()

    # print('Resubstitution error matrix: ', trainAccuracy);
    # print('Training overall accuracy: ', trainAccuracy.accuracy());


def get_landuse(region, date_begin, date_end, vis):
    # get classified as raster
    classified = _get_landuse(region, date_begin, date_end, vis)

    return classified \
        .sldStyle(legger_style)


def get_landuse_vs_legger(region, date_begin, date_end, vis):
    legger = _get_legger_image()

    mask = legger.eq([1, 2, 3, 4, 5, 6]).reduce(ee.Reducer.anyNonZero())
    legger = legger.updateMask(mask)

    # classification
    landuse = _get_landuse(region, date_begin, date_end, vis)

    diff = landuse.subtract(legger)

    # use RWS legger colors
    palette = ['1a9850', '91cf60', 'd9ef8b', 'ffffbf', 'fee08b', 'fc8d59',
               'd73027']

    diff = diff.visualize(**{'min': -5, 'max': 5, 'palette': palette})

    return diff


def _get_legger_image():
    legger_features = ee.FeatureCollection('users/gena/vegetatie-vlakken-geo')

    legger_features = legger_features \
        .map(lambda f: f.set('type', legger_classes.get(f.get('VL_KLASSE'))))

    legger = ee.Image().int().paint(legger_features, 'type')

    return legger


maps = {
    'satellite': get_sentinel_image,
    'ndvi': get_ndvi,
    'landuse': get_landuse,
    'landuse-vs-legger': get_landuse_vs_legger
}


def get_zonal_info_landuse(region, date_begin, date_end, scale):
    pass


def get_zonal_info_landuse_vs_legger(region, date_begin, date_end, scale):
    pass


def get_zonal_info_ndvi(region, date_begin, date_end, scale):
    pass


def get_zonal_info_legger(region, date_begin, date_end, scale):
    features = ee.FeatureCollection(region["features"])

    area = ee.Image.pixelArea().rename('area')

    legger_image = _get_legger_image()
    legger_image = area.addBands(legger_image)

    # for every input feature, compute area of legger types

    def get_feature_info(f):
        f = ee.Feature(f)

        reducer = ee.Reducer.sum().group(**{
            "groupField": 1,
            "groupName": 'type',
        })

        geom = f.geometry()

        area = legger_image.reduceRegion(reducer, geom, scale)

        def format_area(o):
            o = ee.Dictionary(o)

            area = o.get('sum')
            type = ee.Number(o.get('type')).format('%d')

            return {
                "area": area,
                "type": classes_legger.get(type)
            }

        area = ee.List(area.get('groups')).map(format_area)

        return {
            "id": f.get('id'),
            "area_per_type": area
        }

    info = features.toList(5000).map(get_feature_info)

    return info.getInfo()


zonal_info = {
    'landuse': get_zonal_info_landuse,
    'landuse-vs-legger': get_zonal_info_landuse_vs_legger,
    'ndvi': get_zonal_info_ndvi,
    'legger': get_zonal_info_legger
}


def get_image_url(image):
    map_id = image.getMapId()

    id = map_id['mapid']
    token = map_id['token']

    url = 'https://earthengine.googleapis.com/map/' \
          '{0}/{{z}}/{{x}}/{{y}}?token={1}' \
        .format(id, token)

    return url


@app.route('/map/<string:id>/', methods=['POST'])
@flask_cors.cross_origin()
def get_map(id):
    """
    Returns maps processed by Google Earth Engine
    """

    json = request.get_json()

    region = json['region']

    date_begin = json['dateBegin']

    if 'dateEnd' not in json:
        date_end = ee.Date(date_begin).advance(1, 'day')
    else:
        date_end = json['dateEnd']

    date_begin = date_begin or ee.Date(date_begin)
    date_end = date_end or ee.Date(date_end)

    vis = json['vis']

    image = maps[id](region, date_begin, date_end, vis)

    url = get_image_url(image)

    results = {'url': url}

    return jsonify(results)


@app.route('/map/<string:id>/zonal-info/', methods=['POST'])
@flask_cors.cross_origin()
def get_map_zonal_info(id):
    """
    Returns zonal statistics per input feature (region)
    """

    if id not in ['landuse', 'ndvi', 'landuse-vs-legger', 'legger']:
        return 'Error: zonal statistics for {0} is not supported yet' \
            .format(id)

    json = request.get_json()

    region = json['region']

    date_begin = None
    date_end = None

    if 'dataBegin' in json:
        date_begin = ee.Date(json['dateBegin'])

    if 'dataEnd' in json:
        date_end = ee.Date(json['dateEnd'])

    scale = json['scale']

    info = zonal_info[id](region, date_begin, date_end, scale)

    return jsonify(info)


@app.route('/map/<string:id>/times/', methods=['POST'])
@flask_cors.cross_origin()
def get_map_times(id):
    """
    Returns maps processed by Google Earth Engine
    """

    if id != 'satellite':
        return 'Error: times can be requested only for satellite images'

    json = request.get_json()

    region = json['region']

    date_begin = json['dateBegin']
    date_end = json['dateEnd']

    date_begin = date_begin or ee.Date(date_begin)
    date_end = date_end or ee.Date(date_end)

    images = get_sentinel_images(region, date_begin, date_end)

    image_times = ee.List(images.aggregate_array('system:time_start')) \
        .map(to_date_time_string).getInfo()
    image_ids = images.aggregate_array('system:id').getInfo()

    return jsonify({'image_times': image_times, 'image_ids': image_ids})


@app.route('/image/', methods=['POST'])
@flask_cors.cross_origin()
def get_image_by_id():
    id = request.args.get('id')

    vis = request.get_json()

    image = ee.Image(id) \
        .select(band_names['s2'], band_names['readable']) \
        .divide(10000)

    image = visualize_image(image, vis)

    url = get_image_url(image)

    return jsonify(url)


@app.route('/')
@flask_cors.cross_origin()
def root():
    """
    Redirect default page to API docs.
    :return:
    """

    print('redirecting ...')
    return redirect(request.url + 'apidocs')
