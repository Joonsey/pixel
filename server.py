import os
import socket
import threading
import random
import logging

from dataclasses import dataclass
from typing import Any

import settings
import packets

@dataclass
class Connection:
    socket: socket.socket
    auth_id: int
    pos: tuple[float, float]

class TCPServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections: dict[int, Connection] = {}
        self.map: list[list[str]]

        self.map = self._generate_map()


    def _generate_map(self) -> list[list[str]]:
        data = []
        with open('map', 'r') as f:
            for line in f.readlines():
                data.append(line.split(','))

        return data


    def _authenticate(self, conn: socket.socket) -> bool:
        response = conn.recv(1024)

        packet = packets.Packet.deserialize(response)

        if packet.packet_type != packets.PacketType.JOIN_REQUEST: return False

        auth_id = self._generate_auth_id()
        conn.send(
            packets.Packet(
                packets.PacketType.JOIN_RESPONSE,
                auth_id,
                packets.PayloadFormat.JOIN_RESPONSE.pack(auth_id)
            ).serialize()
        )
        self.connections[auth_id] = Connection(conn, auth_id, (0,0))
        return True


    def _onboard_client(self, conn: socket.socket) -> None:
        conn.send(
            packets.Packet(
                packets.PacketType.MAP_DATA,
                list(filter(lambda x: x.socket == conn, self.connections.values()))[0].auth_id,
                packets.PayloadFormat.MAP_DATA.pack(self._get_map_data())
            ).serialize()
        )


    def _get_map_data(self) -> bytes:
        map_bytes = b"".join("".join(x).encode() for x in self.map)
        map_bytes = map_bytes.replace(b'\n', b'')
        logging.info(map_bytes)
        return map_bytes


    def _generate_auth_id(self) -> int:
        possible = [x for x in range(0, 20000)]
        for x in self.connections.keys():
            possible.remove(x)

        return random.choice(possible)


    def _disconnect_connection_by_auth_id(self, auth_id: int) -> None:
        logging.info(f'{auth_id} disconnected')
        self.connections.pop(auth_id)


    def _handle_data(self, data: bytes) -> None:
        packet = packets.Packet.deserialize(data)

        if packet.packet_type == packets.PacketType.DISCONNECT:
            self._disconnect_connection_by_auth_id(packet.auth_id)


    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            while True:
                conn, addr = s.accept()
                logging.info(f'connection request by {addr}')
                with conn:
                    if not self._authenticate(conn):
                        break

                    self._onboard_client(conn)

                    logging.info(f'{addr} authorized!')
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        self._handle_data(data)


class UDPServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections: dict[int, socket.socket] = {}


    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            while True:
                data, addr = s.recvfrom(1024)
                threading.Thread(target=self._handle_data, args=(s, data, addr)).start()

    def _handle_data(self, socket: socket.socket, data: bytes, addr: Any) -> None:
        packet = packets.Packet.deserialize(data)

        logging.debug(f'Received message: {packet.payload} from {packet.auth_id}')
        socket.sendto(packet.serialize(), addr)


class Server:
    def __init__(self, host: str, tcp_port: int, udp_port: int) -> None:
        self.tcp_server = TCPServer(host, tcp_port)
        self.udp_server = UDPServer(host, udp_port)

    def start(self) -> None:
        threading.Thread(target=self.tcp_server.run, daemon=True).start()
        threading.Thread(target=self.udp_server.run, daemon=True).start()


if __name__ == "__main__":
    random.seed(69420)

    server = Server(settings.HOST, int(settings.TCP_PORT), int(settings.UDP_PORT))
    server.start()
    while True:
        pass
