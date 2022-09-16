import socket, time, pickle
import multiprocessing
import json
import struct

exec(open("./settings.txt").read())  #TODO use to run with CMD in mininet command using maketer
#exec(open("./settings.txt").read()) # Uncooment and use for directly used with xterm

target_ip = PC_2 #10.0.0.12
listen_port=kin_link_1 #6001
target_address=(target_ip,listen_port)
packet_len=packet_len
n_packets=n_packets
n_packets_expected= n_packets
send_rate_kbytes_per_s=send_rate_kbytes_per_s


def save_packet_latencies(packetn_latency_tuples, n_packets_expected, output_filename):
        # path ='./Experiment Results/%s'%output_filename
        path = './Experiment Results/%s' % output_filename
        with open(path, 'w') as out_file:
            out_file.write("%d\n" % n_packets_expected)
            for tup in packetn_latency_tuples:
                packet_n = tup[0]
                latency = "%.2f" % tup[1]
                out_file.write("%s %s\n" % (packet_n, latency))
def backup(filename, data):
    with open('./Experiment Results/%s.json'  % (filename), 'w') as f:
        f.write(json.dumps(data))

def recv_one_message(sock):
    lengthbuf = recvall(sock, 4)
    length, = struct.unpack('!I', lengthbuf)
    return recvall(sock, length)


def recvall(sock, count):
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf: return None
        buf += newbuf
        count -= len(newbuf)
    return buf


def packet_backwarding():
    sock_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sock_in.bind(("0.0.0.0", listen_port))
    sock_in.listen()
    conn, address = sock_in.accept()
    print("B_Server running...")
    packets=[]
    while len(packets)<n_packets_expected:
        data = recv_one_message(conn)
        print(f"B_Master<--- {data}")
        recv_time = time.time()
        payload = data.rstrip("a".encode())  # TODO
        (packet_n, send_time) = pickle.loads(payload)
        latency_us = (recv_time - send_time) * 1e6
        packets.append((packet_n, latency_us))
    print("Done !!!!")
    output_filename = "HD_{}".format(n_packets_expected)
    save_packet_latencies(packets, n_packets_expected, output_filename)
    print("Closing...")
    sock_in.close()

if __name__ == '__main__':
    # ServerSide()
    receiver = multiprocessing.Process(target=packet_backwarding)
    receiver.start()
    receiver.join()
