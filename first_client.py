import asyncio
import json
import packet as pk
import struct

async def send_command(writer, command):
    """Helper function to send a command to the server."""
    writer.write(command)
    await writer.drain()  # Ensure the command is sent immediately

async def receive_response(reader):
    """Helper function to receive and process the server's response."""
    data = await reader.read(16384)  # Read up to 16KB of data
    return data

async def client1(host, port):
    # Load commands from JSON file
    with open('H:\programming\Developing\SRI_TUSUR\command_biab100.json', 'r') as file:
        commands = json.load(file)

    control_commands = [
        commands['short_comm']['complex_mode']['cod_ku'],
        commands['short_comm']['vkl_atm_biab']['cod_ku'],
        commands['short_comm']['test']['cod_ku']
    ]
    
    reader, writer = await asyncio.open_connection(host, port)
    
    # Convert control commands to the appropriate format for sending
    for command in control_commands:
        encoded_command = struct.pack('<H', command)  # Assuming command needs to be packed
        print(f"Client 1 sending: Command {command}")
        await send_command(writer, encoded_command)
        
        try:
            data = await receive_response(reader)
            print(f"Client 1 received: {data}")
            
            # Example: updating packet data (similar to atm.update_dt_packet(data))
            atm = pk.Atm_Packet()  # Assuming pk has been imported and includes Atm_Packet
            atm.update_dt_packet(data)
            print(atm.ansver_packet())
        except ConnectionError:
            print("Connection closed by server.")
            break
        
        await asyncio.sleep(2)  # Wait before sending the next command
    
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    asyncio.run(client1(HOST, PORT))
