# Update the existing file with these changes

import hashlib
from dataclasses import dataclass
from parameter import *

@dataclass
class File:
    name: str
    size: int

@dataclass
class Piece:
    index: int
    hash: str

class MetaInfoFile:
    def __init__(self, info_hash: str, pieces: List[Piece], file: File, tracker_address: str):
        self.info_hash = info_hash
        self.pieces = pieces
        self.file = file
        self.tracker_address = tracker_address
    def encode(self) -> bytes:
        info = {
            'file_name': self.file.name,
            'file_size': self.file.size,
            'piece length': PIECE_SIZE,
            'pieces_count': len(self.pieces)
        }
        return bencodepy.encode({
            'info': info,
            'announce': self.tracker_address
        })
    def decode(self, metainfo: bytes) -> 'MetaInfoFile':
        decoded = bencodepy.decode(metainfo)
        return MetaInfoFile(info_hash=hashlib.sha1(decoded['info']).hexdigest(), 
                            pieces=[Piece(index=i, hash=piece) for i, piece in enumerate(decoded['info']['pieces'])], 
                            file=File(name=decoded['info']['file_name'], size=decoded['info']['file_size']), 
                            tracker_address=decoded['announce'])

class MagnetLink:
    def __init__(self, info_hash: str, tracker_address: str):
        self.info_hash = info_hash
        self.tracker_address = tracker_address

    def to_string(self) -> str:
        return f"magnet:?xt=urn:btih:{self.info_hash}&tr={self.tracker_address}"
    
    def decode(self, magnet_string: str) -> 'MagnetLink':
        parts = magnet_string.split('&')
        info_hash = parts[0].split(':')[-1]
        tracker_address = parts[1].split('=')[-1]
        return MagnetLink(info_hash, tracker_address)
