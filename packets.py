import struct
from enum import auto, IntEnum


class PacketType(IntEnum):
    JOIN_REQUEST = auto()
    JOIN_RESPONSE = auto()
    MAP_DATA = auto()
    DISCONNECT = auto()
    MOVE = auto()
    INITIAL_DATA = auto()
    SYNC = auto()
    SYNC_ENTITIES = auto()


class PayloadFormat:
    JOIN_REQUEST = struct.Struct('16s')
    JOIN_RESPONSE = struct.Struct('I')
    DISCONNECT = struct.Struct('I')
    MOVE = struct.Struct('III')
    MAP_DATA = struct.Struct('576s')


class DisconnectEnum(IntEnum):
    EXPECTED = auto()
    UNEXPECTED = auto()


class Packet:
    HEADER_SIZE = struct.calcsize('IIII')
    MAGIC_NUMBER = 0xDEADBEEF


    def __init__(self, packet_type: PacketType, auth_id: int, payload: bytes):
        self.packet_type = packet_type
        self.auth_id = auth_id
        self.payload = payload


    def serialize(self):
        magic_number_bytes = struct.pack('I', self.MAGIC_NUMBER)
        packet_type_bytes = struct.pack('I', self.packet_type)
        auth_id_bytes = struct.pack('I', self.auth_id)
        payload_length_bytes = struct.pack('I', len(self.payload))

        headers = magic_number_bytes + packet_type_bytes + auth_id_bytes + payload_length_bytes
        serialized_packet = headers + self.payload

        return serialized_packet


    @classmethod
    def deserialize(cls, serialized_data: bytes):
        if len(serialized_data) < Packet.HEADER_SIZE:
            raise ValueError("Invalid packet - packet is too short")

        magic_number, packet_type, sequence_number, payload_length = struct.unpack('IIII', serialized_data[:Packet.HEADER_SIZE])

        if magic_number != Packet.MAGIC_NUMBER:
            raise ValueError("Invalid packet - magic number mis-match of packets. \npacket will be disqualified")
        payload = serialized_data[Packet.HEADER_SIZE: Packet.HEADER_SIZE+ payload_length]

        return Packet(packet_type, sequence_number, payload)
