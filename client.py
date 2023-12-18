import pickle
import socket
import threading
import random
import logging
import time
from typing import Any, Optional

import settings
import packets


class Client:
    def __init__(self, host: str, tcp_port: int, udp_port: int, username: str = "username123") -> None:
        self.tcp_socket: socket.socket
        self.udp_socket: Optional[socket.socket] = None
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.die: bool = False
        self.auth_id: int = 0
        self.id: int = 0
        self.username = username
        self.map: list[list[str]]
        self.others: dict[int, tuple[float, float]] = {}
        self.entities: dict[int, tuple[float, float]] = {}

    @property
    def authenticated(self) -> bool:
        return self.auth_id != 0 and self.udp_socket != None and self.id != 0


    def disconnect(self, disconnect_type: packets.DisconnectEnum = packets.DisconnectEnum.UNEXPECTED) -> None:
        packet_bytes = packets.Packet(
                packets.PacketType.DISCONNECT,
                self.auth_id,
                packets.PayloadFormat.DISCONNECT.pack(disconnect_type)
            ).serialize()

        self.tcp_socket.sendall(packet_bytes)
        self.udp_socket = None
        self.die = True


    def _start_connection_and_authenticate(self, socket: socket.socket) -> bool:
        socket.sendall(
            packets.Packet(
                packets.PacketType.JOIN_REQUEST,
                0,
                packets.PayloadFormat.JOIN_REQUEST.pack(self.username.encode())
            ).serialize()
        )
        response = socket.recv(1024)

        packet = packets.Packet.deserialize(response)

        if packet.packet_type != packets.PacketType.JOIN_RESPONSE:
            return False

        id, = packets.PayloadFormat.JOIN_RESPONSE.unpack(packet.payload)

        if packet.packet_type == packets.PacketType.JOIN_RESPONSE and int(id) != 0 and packet.auth_id != 0:
            self.auth_id = packet.auth_id
            self.id = id
            logging.info(f'authenticated with auth_id {packet.auth_id} & id {id}')
            return True

        return False


    def _build_map_from_payload(self, payload: bytes) -> list[list[str]]:
        rows = payload.decode()
        rows = [rows[i:i+settings.MAP_LENGTH] for i in range(0, len(rows), settings.MAP_LENGTH)]
        map_data: list[list[str]] = []

        for row in rows:
            map_data.append([*row])

        return map_data


    def _handle_tcp(self, data: bytes) -> None:

        packet = packets.Packet.deserialize(data)

        if packet.packet_type == packets.PacketType.MAP_DATA:
            self.map = self._build_map_from_payload(packet.payload)
            logging.debug(f"got map data:\n{self.map}")

        if packet.packet_type == packets.PacketType.DISCONNECT:
            self.disconnect(packets.DisconnectEnum.EXPECTED)

        if packet.packet_type == packets.PacketType.INITIAL_DATA:
            logging.info("loading initial data")
            self.others = pickle.loads(packet.payload)
            if self.id in self.others:
                self.others.pop(self.id)

        logging.debug(self.others)

    def _handle_udp(self, data: bytes, addr: Any) -> None:
        packet = packets.Packet.deserialize(data)
        logging.debug(f"{packet.auth_id} | {packet.payload}")

        if packet.packet_type == packets.PacketType.MOVE:
            id, x, y = packets.PayloadFormat.MOVE.unpack(packet.payload)
            logging.info(f'unpacked id %s, x %s, y %s', id, x, y)
            if id == self.id:
                return

            if id not in self.others.keys():
                logging.warning(f"move packet potentialy erronous! {id} was sendt but not found")

            self.others[id] = (x, y)

        if packet.packet_type == packets.PacketType.SYNC:
            self.others = pickle.loads(packet.payload)
            if self.id in self.others:
                self.others.pop(self.id)

        if packet.packet_type == packets.PacketType.SYNC_ENTITIES:
            self.entities = pickle.loads(packet.payload)


    def _start_udp(self) -> None:
        def run():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

                logging.info("connecting through udp")
                self.udp_socket = s

                while not self.die:
                    data, addr = s.recvfrom(1024)
                    if not data:
                        self.die = True
                        logging.info("dying")
                        break

                    self._handle_udp(data, addr)

        threading.Thread(target=run, daemon=True).start()


    def send_packet(self, packet: packets.Packet) -> None:
        if not self.authenticated or self.udp_socket == None:
            logging.error("not authenticated! packets are being dropped")
        else:
            self.udp_socket.sendto(packet.serialize(), (self.host, self.udp_port))


    def tcp_connection(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            self.tcp_socket = s
            s.connect((self.host, self.tcp_port))
            if not self._start_connection_and_authenticate(s):
                self.disconnect(packets.DisconnectEnum.EXPECTED)
                return

            self._start_udp()

            while not self.die:
                data = s.recv(1024)
                if not data:
                    self.die = True
                    break

                self._handle_tcp(data)


    def start(self) -> None:
        threading.Thread(target=self.tcp_connection, daemon=True).start()


if __name__ == "__main__":
    client = Client(settings.HOST, int(settings.TCP_PORT), int(settings.UDP_PORT))

    client.start()
    try:
        while True:
            time.sleep(.5)
            if client.authenticated:
                client.send_packet(
                    packets.Packet(
                        packets.PacketType.MOVE,
                        client.auth_id,
                        packets.PayloadFormat.MOVE.pack(client.id, random.randint(0, 50), random.randint(0, 50))
                ))
                logging.info(client.others)

    except KeyboardInterrupt as _:
        client.disconnect(packets.DisconnectEnum.EXPECTED)

    except Exception as _:
        client.disconnect()

