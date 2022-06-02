

from sys import argv
from src.server import SocketServer


if __name__ == "__main__":
    server = SocketServer(address=argv[1], port=argv[2])