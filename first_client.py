import asyncio
import json
from time import time
from struct import pack, calcsize

def komm(list_komm: dict, n_pak=2, n_param=0):
    '''Create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)

def mess(data, t_time):
    '''Create message'''
    SIZE_Q = calcsize('Q')
    t_time_int = int(t_time * 1000)  # Преобразование временной метки в миллисекунды
    return pack('<H', SIZE_Q + len(data)) + pack('<Q', t_time_int) + data

async def client1(host, port):
    # Load commands from JSON file
    with open('command_biab100.json', 'r') as file:
        commands = json.load(file)

    command_names = ["complex_mode", "vkl_atm_biab", "vkl_biab"]

    # Process each command and create messages
    for command_name in command_names:
        command_details = commands['short_comm'][command_name]

        # Encode command
        encoded_command = komm(command_details)

        # Get current time (using float for more precision)
        current_time = time()

        # Create message
        message = mess(encoded_command, current_time)

        # Establish connection and send message
        reader, writer = await asyncio.open_connection(host, port)

        print(f"Sending {command_name}: {message}")
        writer.write(message)
        await writer.drain()

        print(f"Sent {command_name}, waiting for response")
        data = await reader.read(100)
        print(f"Received: {data.decode()}")

        print(f"Closing connection for {command_name}")
        writer.close()
        await writer.wait_closed()

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    asyncio.run(client1(HOST, PORT))
