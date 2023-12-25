import os
import logging

logging.getLogger().setLevel(logging.INFO)

HOST = os.environ['HOST'] if 'HOST' in os.environ.keys() else 'localhost'
TCP_PORT = int(os.environ['TCP_PORT']) if 'TCP_KEYS' in os.environ.keys() else 8881
UDP_PORT = int(os.environ['UDP_PORT']) if 'UDP_KEYS' in os.environ.keys() else 8888

MAP_LENGTH = len(open('map', 'r').readline().replace(',', '')) - 1

RESOLUTION = 1280, 720
RENDER_RESOLUTION = 540, 360
FPS_TARGET = 60
TILESIZE = 16
