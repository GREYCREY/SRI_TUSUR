import asyncio
import json

async def client1(host, port):
    # Load commands from JSON file
    with open('D:\programming\SRI_TUSUR\command_biab100.json', 'r') as file:
        commands = json.load(file)
    
    control_commands = [commands['short_comm']['complex_mode']['cod_ku'],
                        commands['short_comm']['vkl_atm_biab']['cod_ku'],
                        commands['short_comm']['test']['cod_ku']]
    
    reader, writer = await asyncio.open_connection(host, port)
    
    for command in control_commands:
        message = f"Command: {command}"
        print(f"Client 1 sending: {message}")
        writer.write(message.encode())
        
        try:
            data = await reader.read(1024)
            print(f"Client 1 received: {data.decode()}")
        except ConnectionError:
            print("Connection closed by server.")
            break
        
        await asyncio.sleep(2) 
    
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    asyncio.run(client1(HOST, PORT))
