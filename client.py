import os
import socket
import threading
import random
import logging
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
        self.username = username
        self.map: list[list[str]]


    @property
    def authenticated(self) -> bool:
        return self.auth_id != 0 and self.udp_socket != None


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
        socket.connect((self.host, self.tcp_port))
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

        payload, = packets.PayloadFormat.JOIN_RESPONSE.unpack(packet.payload)

        if packet.packet_type == packets.PacketType.JOIN_RESPONSE and int(payload) != 0:
            self.auth_id, = packets.PayloadFormat.JOIN_RESPONSE.unpack(packet.payload)
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
            logging.info(f"got map data:\n{self.map}")


    def _handle_udp(self, data: bytes, addr: Any) -> None:

        packet = packets.Packet.deserialize(data)
        #print(packet.auth_id, packet.payload)


    def _start_udp(self) -> None:
        def run():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

                logging.info("starting udp server")
                self.udp_socket = s

                while True:
                    data, addr = s.recvfrom(1024)
                    if not data:
                        self.die = True
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
            if not self._start_connection_and_authenticate(s):
                self.disconnect(packets.DisconnectEnum.EXPECTED)
                return

            self._start_udp()

            while True:
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
            if client.authenticated:
                client.send_packet(
                    packets.Packet(
                        packets.PacketType.MOVE,
                        client.auth_id,
                        packets.PayloadFormat.MOVE.pack(random.randint(0, 50), random.randint(0, 50))
                ))
    except KeyboardInterrupt as _:
        client.disconnect(packets.DisconnectEnum.EXPECTED)

    except Exception as _:
        client.disconnect()

