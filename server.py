import os
import socket
import threading
import random
from typing import Any

import settings
import packets


class TCPServer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connections: dict[int, socket.socket] = {}


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
        self.connections[auth_id] = conn
        return True


    def _generate_auth_id(self) -> int:
        possible = [x for x in range(0, 20000)]
        for x in self.connections.keys():
            possible.remove(x)

        return random.choice(possible)


    def _disconnect_connection_by_auth_id(self, auth_id: int) -> None:
        print('disconnecting', self.connections[auth_id])
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
                print('connection request by', addr)
                with conn:
                    if not self._authenticate(conn):
                        break

                    print(addr, "authorized!")
                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        self._handle_data(data)


class UDPServer:
    def __init__(self, host: str, port: int, tcp_server: TCPServer) -> None:
        self.host = host
        self.port = port
        self.tcp_server = tcp_server


    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((self.host, self.port))
            while True:
                data, addr = s.recvfrom(1024)
                print(data)
                threading.Thread(target=self._handle_data, args=(s, data, addr)).start()

    def _handle_data(self, socket: socket.socket, data: bytes, addr: Any) -> None:
        packet = packets.Packet.deserialize(data)

        print('Received message:', packet.payload, 'from', packet.auth_id)
        socket.sendto(packet.serialize(), addr)


if __name__ == "__main__":
    tcp_server = TCPServer(settings.HOST, int(settings.TCP_PORT))
    threading.Thread(target=tcp_server.run, daemon=True).start()

    udp_server = UDPServer(settings.HOST, int(settings.UDP_PORT), tcp_server)
    threading.Thread(target=udp_server.run, daemon=True).start()

    while True:
        pass
