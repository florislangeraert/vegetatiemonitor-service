from google.cloud import firestore

Session = firestore.Client()
collection = u's2-tile-cache'

class Firestore():
    def __init__(self) -> Session:
        pass

    def count_tiles():
        db = firestore.Client()

        tile_images = db.collection(collection).list_documents()

        return len(list(tile_images))

    def query_collection(txty_min: int, txty_max: int):
        tile_images = {}

        db = firestore.Client()

        tile_images_ref = db.collection(collection)

        tile_images_query = tile_images_ref.where(u'txty', u'>=', txty_min).where(u'txty', u'<=', txty_max) \
            .select(['image_time', 'image_id'])

        for tile_image in tile_images_query.stream():
            tile_image = tile_image.to_dict()
            tile_images[tile_image['image_time']] = {
                'id': tile_image['image_id'],
                'time': tile_image['image_time']
            }

        return tile_images

    def delete_collection():
        db = firestore.Client()

        tile_images_ref = db.collection(collection)

        for tile in tile_images_ref.stream():
            tile.reference.delete()

        return True
    
    def add_collection(tile_images: list):

        db = firestore.Client()

        tile_images_ref = db.collection(collection)

        #add new tile_image records
        for tile_image in tile_images:
            t = tile_images_ref.document()
            tile_image['txty'] = _compound_tile_index(tile_image['tx'], tile_image['ty'])
            t.set(tile_image)

        return True

def _compound_tile_index(tx, ty):
    return tx * 100000 + ty