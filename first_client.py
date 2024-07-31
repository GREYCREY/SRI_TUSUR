import asyncio

async def client1(host, port):
    reader, writer = await asyncio.open_connection(host, port)
    
    while True:
        message = "Hello from Client 1"
        print(f"Client 1 sending: {message}")
        writer.write(message.encode())
        
        try:
            data = await reader.read(1024)
            print(f"Client 1 received: {data.decode()}")
        except ConnectionError:
            print("Connection closed by server.")
            break
        
        await asyncio.sleep(2)  # Pause for a bit before sending next message
        
        if input("Press  'q' to quit: ") == 'q':
            break
    
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    asyncio.run(client1(HOST, PORT))
