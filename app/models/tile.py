from sqlalchemy import BigInteger, Column, Integer, Sequence, String
from app.postgres import Base

"""
Representation of a tile image
"""
class Tile(Base):
    __tablename__ = 's2-tile-cache'

    id = Column(Integer, primary_key=True)
    image_id = Column(String)
    image_time = Column(BigInteger)
    tx = Column(Integer)
    txty = Column(BigInteger)
    ty = Column(Integer)
    zoom = Column(Integer)

    def __init__(self, image_id, image_time, tx, txty, ty, zoom):
        self.image_id = image_id
        self.image_time = image_time
        self.tx = tx
        self.txty = txty
        self.ty = ty
        self.zoom = zoom