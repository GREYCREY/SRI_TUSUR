import asyncio

# Function to create an acknowledgment message
def create_ack_message(command):
    return f"Command received: {command}"

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
        
        command = data.decode()
        print(f"Server received: {command}")
        
        ack_message = create_ack_message(command)
        
        # Create binary acknowledgment message
        binary_ack_message = ack_message.encode() + b'\x00\x01\x02\x03'  # Example binary data appended
        
        try:
            writer.write(binary_ack_message)
            await writer.drain()  # Ensure all data is sent
        except ConnectionError:
            print(f"Client suddenly closed, cannot send")
            break
    
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
