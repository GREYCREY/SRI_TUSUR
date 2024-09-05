import asyncio
from struct import unpack, pack, calcsize

async def handle_connection(reader, writer):
    addr = writer.get_extra_info("peername")
    print("Connected by", addr)
    
    while True:
        try:
            data = await reader.read(1024)
        except ConnectionError:
            print(f"Client suddenly closed while receiving from {addr}")
            break
        
        if not data:
            break

        # Распаковываем заголовок и временную метку
        header_format = '<H Q'
        header_size = calcsize(header_format)
        header = unpack(header_format, data[:header_size])
        message_length, timestamp = header
        print(f"Message length: {message_length}, Timestamp: {timestamp}")

        # Распаковываем команду
        command_format = '<H H I H'
        n_pak, type_ku, cod_ku, param = unpack(command_format, data[header_size:header_size+calcsize(command_format)])
        
        print(f"Server received: {cod_ku}")
        receipt = pack('<HQHBH', message_length , timestamp, 2 , 1 , cod_ku)
        writer.write(receipt)
        await writer.drain()

    writer.close()
    await writer.wait_closed()
    print("Disconnected by", addr)

async def main(host, port):
    server = await asyncio.start_server(handle_connection, host, port)
    async with server:
        await server.serve_forever()

HOST, PORT = "", 50007

if __name__ == "__main__":
    asyncio.run(main(HOST, PORT))
