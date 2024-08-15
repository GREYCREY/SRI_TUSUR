import asyncio
import struct

async def handle_client(reader, writer):
    while True:
        # Чтение данных от клиента
        data = await reader.read(1024)
        if not data:
            break
        
        # Декодирование данных
        command = struct.unpack('<H', data[:2])[0]
        print(f"Server received command: {command}")
        
        # Обработка команды и отправка ответа
        response = f"Received command {command}".encode()
        writer.write(response)
        await writer.drain()  # Обеспечение отправки данных
        
    print("Closing connection")
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 50007)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
