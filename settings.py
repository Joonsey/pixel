import os
import logging

logging.getLogger().setLevel(logging.INFO)

HOST = os.environ['HOST'] if 'HOST' in os.environ.keys() else 'localhost'
TCP_PORT = os.environ['TCP_PORT'] if 'TCP_KEYS' in os.environ.keys() else 8881
UDP_PORT = os.environ['UDP_PORT'] if 'UDP_KEYS' in os.environ.keys() else 8888

MAP_LENGTH = len(open('map', 'r').readline())
