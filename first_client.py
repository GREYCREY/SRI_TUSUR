import asyncio
import json
from time import time
from struct import pack, calcsize


def komm (list_komm : dict, n_pak = 2, n_param = 0):
    '''create command'''
    k = list_komm['type_ku']
    m = list_komm['cod_ku']
    return pack('<HHIH', n_pak, k, m, n_param)
def mess (data, t_time):
    '''create message'''
    SIZE_Q = calcsize('Q')
    return pack('<H', SIZE_Q+len(data)) + pack('<Q', t_time) + data

async def client1(host, port):
    # Load commands from JSON file
    with open('command_biab100.json', 'r') as file:
        commands = json.load(file)

# Process each command and create messages
    for command_name, command_details in commands['short_comm'].items():
    # Encode command
        encoded_command = komm(command_details)
    
    # Get current time
        current_time = int(time())
    
    # Create message
        message = mess(encoded_command, current_time)   
    # Here you can send the message or do further processing
        print(f"Command: {command_name}, Encoded Message: {message}")

if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 50007
    asyncio.run(client1(HOST, PORT))
    
