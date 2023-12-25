import os
import sys
import logging
import time

import server as srvr
import settings

def main() -> None:
    server = srvr.Server(settings.HOST, settings.TCP_PORT, settings.UDP_PORT)


    def run_loop():
        while True:
            time.sleep(.5)
            print('\033[2J', end='')
            conns = server.connections.copy()

            active_conns = list(filter(lambda x: x.active, conns.values()))
            print(f"active connections: {len(active_conns)}")
            for conn in active_conns :
              print(f"{conn.auth_id} | x, y: {conn.pos[0]}, {conn.pos[1]}")

    try:
        server.start()
        run_loop()

    except Exception as e:
        print(e)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.ERROR)
    main()

