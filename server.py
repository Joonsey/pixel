from __future__ import annotations
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
    active: bool = True

    def update_pos(self, new_pos: tuple[float | int, float | int]) -> None:
        self.pos = new_pos

class TCPServer:
    def __init__(self, host: str, port: int, parent: Server) -> None:
        self.host = host
        self.port = port
        self.map: list[list[str]]
        self.connections = parent.connections

        self.map = self._generate_map()
        self.running = True

        self.stop = parent.stop


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
        auth_id = list(filter(lambda x: x.socket == conn, self.connections.values()))[0].auth_id
        logging.info(f"sending map data to {auth_id}")
        conn.send(
            packets.Packet(
                packets.PacketType.MAP_DATA,
                auth_id,
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
        self.connections[auth_id].active = False
        #self.connections.pop(auth_id)


    def disconnect_all_clients(self) -> None:
        for conn in self.connections.copy().values():
            self._disconnect_connection_by_auth_id(conn.auth_id)


    def handle_client(self, conn: socket.socket, addr: Any) -> None:
        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                packet = packets.Packet.deserialize(data)

                if packet.packet_type == packets.PacketType.DISCONNECT:
                    self._disconnect_connection_by_auth_id(packet.auth_id)

            except OSError as e:
                # should maybe try reconnecting automatically?
                conn.close()
                logging.info("connection is closed")
                break



    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
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
                        threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

            except OSError as e:
                s.close()

            finally:
                self.disconnect_all_clients()
                self.stop()


    def _stop(self) -> None:
        self.running = False


class UDPServer:
    def __init__(self, host: str, port: int, parent: Server) -> None:
        self.host = host
        self.port = port
        self.connections = parent.connections

        self.running = True

        self.stop = parent.stop


    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind((self.host, self.port))
                while self.running:
                    data, addr = s.recvfrom(1024)
                    threading.Thread(target=self._handle_data, args=(s, data, addr), daemon=True).start()
            finally:
                self.stop()

    def _handle_data(self, socket: socket.socket, data: bytes, addr: Any) -> None:
        packet = packets.Packet.deserialize(data)

        logging.debug(f'Received message: {packet.payload} from {packet.auth_id}')
        if packet.auth_id not in self.connections.keys():
            logging.debug(f'unauthorized package from with auth_id: {packet.auth_id}')
            return

        if packet.packet_type == packets.PacketType.MOVE:
            x, y = packets.PayloadFormat.MOVE.unpack(packet.payload)
            self.connections[packet.auth_id].update_pos((float(x), float(y)))

        socket.sendto(packet.serialize(), addr)


    def _stop(self) -> None:
        self.running = False


class Server:
    def __init__(self, host: str, tcp_port: int, udp_port: int) -> None:
        self.connections: dict[int, Connection] = {}
        self.tcp_server = TCPServer(host, tcp_port, self)
        self.udp_server = UDPServer(host, udp_port, self)

    def start(self) -> None:
        threading.Thread(target=self.tcp_server.run, daemon=True).start()
        threading.Thread(target=self.udp_server.run, daemon=True).start()

    def stop(self) -> None:
        self.udp_server._stop()
        self.tcp_server._stop()


if __name__ == "__main__":
    random.seed(69420)

    server = Server(settings.HOST, int(settings.TCP_PORT), int(settings.UDP_PORT))
    server.start()
    while True:
        pass
