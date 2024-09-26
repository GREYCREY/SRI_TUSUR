import socket
from struct import unpack, pack, calcsize

def handle_connection(conn, addr):
    print("Connected by", addr)
    
    while True:
        try:
            data = conn.recv(1024)
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
        receipt = pack('<HQHBH', message_length, timestamp, 2, 1, cod_ku)
        conn.sendall(receipt)

    conn.close()
    print("Disconnected by", addr)

def main(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()

        print(f"Server listening on {host}:{port}")
        while True:
            conn, addr = server_socket.accept()
            handle_connection(conn, addr)

if __name__ == "__main__":
    HOST, PORT = "", 50007
    main(HOST, PORT)
