from sqlalchemy.orm import Session
from app.models import Tile

def count_tiles(session: Session):
    return session.query(Tile).count()

def query_collection(session: Session, txty_min: int, txty_max: int):
    tile_images = {}

    tile_images_query = session.query(Tile) \
        .filter(Tile.tx >= txty_min) \
        .filter(Tile.ty <= txty_max) \
        .all()

    for tile_image in tile_images_query:
        tile_image = tile_image.to_dict()
        tile_images[tile_image['image_time']] = {
            'id': tile_image['image_id'],
            'time': tile_image['image_time']
        }

    return tile_images

def delete_collection(session: Session):
    session.query(Tile).delete()
    session.commit()

    return True

def add_collection(session: Session, tile_images: list):

    for tile_image in tile_images:
        tile = Tile(tile_image['image_id'],tile_image['image_time'],tile_image['tx'],_compound_tile_index(tile_image['tx'], tile_image['ty']),tile_image['ty'], tile_image['zoom'])
        session.add(tile)

    session.commit()

    return True

def _compound_tile_index(tx, ty):
    return tx * 100000 + ty
