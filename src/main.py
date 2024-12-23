import asyncio
import sys
from functools import partial
from typing import Optional
import electrum_ecc as ecc

from modules.lntransport import (LNTransport, LNResponderTransport,
                                 LNPeerAddr, extract_nodeid, split_host_port, LightningPeerConnectionClosed)


def chunk_data(data: bytes, chunk_size: int = 64000):
    chunk_amount = (len(data) + chunk_size - 1) // chunk_size
    current_chunk = 1
    for i in range(0, len(data), chunk_size):
        prefix = f"{current_chunk}/{chunk_amount}:"
        current_chunk += 1
        yield prefix.encode() + data[i:i+chunk_size]

class ChunkedData:
    def __init__(self):
        self.data = b""
        self.chunk_amount: int = 0
        self.current_chunk: int = 0

    def add_chunk(self, chunk: bytes) -> Optional[bytes]:
        """"returns data if complete, prefix is 'current_chunk/chunk_amount:'"""
        prefix, data = chunk.split(b":", 1)
        current_chunk, chunk_amount = prefix.split(b"/", 1)
        if self.chunk_amount == 0:
            self.chunk_amount = int(chunk_amount)
        else:
            if chunk_amount != self.chunk_amount or int(current_chunk) == self.current_chunk + 1:
                raise ChunkMismatchError()
        self.current_chunk = int(current_chunk)
        self.data += data
        if self.current_chunk == self.chunk_amount:
            return self.data
        else:
            return None


async def read_messages(transport):
    try:
        data = ChunkedData()
        async for msg in transport.read_messages():
            full_data = None
            try:
                full_data = data.add_chunk(msg)
            except ChunkMismatchError:
                data = ChunkedData()  # just reset it, if it fails again we get invalid messages and close
                full_data = data.add_chunk(msg)
            finally:
                if full_data is not None:
                    print(full_data)
                    data = ChunkedData()
    except LightningPeerConnectionClosed:
        print("connection closed")

async def cb(reader, writer, server_key):
    t = LNResponderTransport(server_key.get_secret_bytes(), reader, writer)
    initiator_key = await t.handshake()
    print(f"client connected: {initiator_key.hex()}")

    await read_messages(t)


async def main():
    if len(sys.argv) == 1:  # server
        server_key = ecc.ECPrivkey.generate_random_key()
        server_cb = partial(cb, server_key=server_key)
        server = await asyncio.start_server(server_cb, '127.0.0.1', port=8080)
        print(f"serving on {server_key.get_public_key_hex()}@{server.sockets[0].getsockname()[0]}"
              f":{server.sockets[0].getsockname()[1]}")

        async with server:
            await server.serve_forever()
        return

    # client. path, connection string
    client_key = ecc.ECPrivkey.generate_random_key()
    file_path = None
    if len(sys.argv) == 2:  # only connection string, read from stdin
        node_id, remaining = extract_nodeid(sys.argv[1])
    else: # assuming filename, connection string
        file_path = sys.argv[1]
        node_id, remaining = extract_nodeid(sys.argv[2])
    host, port = split_host_port(remaining)
    peer_addr = LNPeerAddr(host, int(port), node_id)
    t = LNTransport(client_key.get_secret_bytes(), peer_addr, e_proxy=None)
    await t.handshake()
    print(f"Connected to {node_id.hex()}", file=sys.stderr)

    if file_path:
        with open(file_path, "rb") as f:
            for chunk in chunk_data(f.read()):
                t.send_bytes(chunk)
    else:
        while True:
            data = sys.stdin.read()
            if len(data) == 0:
                break
            for chunk in chunk_data(data.encode()):
                t.send_bytes(chunk)
    t.close()

class ChunkMismatchError(Exception):
    pass

if __name__ == "__main__":
    asyncio.run(main())