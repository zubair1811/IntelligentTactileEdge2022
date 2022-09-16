import socket, time, pickle
import multiprocessing

exec(open("./settings.txt").read()) #TODO use to run with CMD in mininet command using maketerm
#exec(open("./settings.txt").read()) # Uncooment and use for directly used with xterm

listen_port=kin_link_0
n_packets_expected= n_packets
target_ip=PC_1
target_address=(target_ip,listen_port+1)

def ServerSide():
    sock_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sock_in.bind(("0.0.0.0", listen_port))
    sock_in.listen()
    conn, address = sock_in.accept()
    socket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_out.connect(target_address)
    print("Slave running ... at {} to communicate {}".format(listen_port,address))
    while True:
        try:
            data = conn.recv(1024)
            print(data)
            if not data:
                break
            socket_out.sendall(data)
            print(f"B-->Slave <--- {data}")  # TODO
        except KeyboardInterrupt:
            print("Slave in Exception mode") # TODO
            break
    print("Closing...")
    sock_in.close()

if __name__ == '__main__':
    # ServerSide()
    receiver = multiprocessing.Process(target=ServerSide)
    receiver.start()
    receiver.join()
