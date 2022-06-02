

import asyncio
import json
import websockets
import logging
# logger = logging.getLogger('websockets')
# logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())

from src.scipy_solver import ScipySolver

class SocketServer:
    def __init__(self, address, port) -> None:
        print(f"Starting up solver server at {address}:{port}")
        self.address = address
        self.port = port
        self.solver = ScipySolver()

        async def handle_messages(websocket, path):
            while True:
                msg = await websocket.recv()
                await websocket.send(json.dumps(self.solver.parse_message(json.loads(msg))))

        server = websockets.serve(handle_messages, self.address, self.port)

        asyncio.get_event_loop().run_until_complete(server)
        print("Server started!")
        asyncio.get_event_loop().run_forever()

        

