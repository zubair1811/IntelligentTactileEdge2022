import numpy as np

# exec(open("./settings.txt").read())
exec (open("./settings.txt").read())


def througput_calculation(mRTT,bwdth, packet_size):
    bwdth= (bwdth/8) * 1e6
    packet_size = packet_size * 1e3
    T_transfer= mRTT + (((1/bwdth) * packet_size) *1e3 )
    T_put= (packet_size/T_transfer*1e-3) * 8
    return T_put


def read_latencies_file(latencies_filename):
    path = './Experiment Results/%s' % latencies_filename
    with open(path, 'r') as latencies_file:
        lines = latencies_file.read().split('\n')
    packet_ns = []
    latencies_ms = []
    total_n_packets = int(lines[0])
    for line in lines[1:]:
        if len(line) == 0:
            continue
        fields = line.split(' ')
        packet_n = int(fields[0])
        packet_ns.append(packet_n)
        latency_us = float(fields[1])
        latency_ms = latency_us / 1000
        latencies_ms.append(latency_ms)
    packet_ns = np.array(packet_ns)
    latencies_ms = np.array(latencies_ms)
    mRTT = round(np.average(latencies_ms), 3)
    pack_loss = [round(i, 3) for i in latencies_ms if i > 500]
    pack_loss =round((len(pack_loss) /n_packets) * 100,3)
    T_put = round(througput_calculation(mRTT=mRTT, bwdth=bandwith, packet_size=packet_len),3)
    return (mRTT, pack_loss, T_put)






