import os
import sys
import logging
import time

import server as srvr
import settings

def main() -> None:
    server = srvr.Server(settings.HOST, settings.TCP_PORT, settings.UDP_PORT)

    server.start()

    while True:
        time.sleep(.5)
        conns = server.connections.copy()

        realtime_str = "\n"
        active_conns = list(filter(lambda x: x.active, conns.values()))
        for conn in active_conns :
          realtime_str += f"{conn.auth_id} | x, y: {conn.pos[0]}, {conn.pos[1]}\n"

        # Clear the remaining part of the line
        print('\033[2J', end='')

        # Move the cursor up
        for _ in range(len(active_conns) + 1):
           print('\033[F', end='')

        # Print the new content
        print(realtime_str, end="")



if __name__ == "__main__":
    logging.getLogger().setLevel(logging.ERROR)
    main()

