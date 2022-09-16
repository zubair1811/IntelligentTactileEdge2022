
import os
import numpy as np
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import time
import substring as ss
from mininet.term import makeTerm
import random
import ecpredictor as ecp
import learner as lrn
import pandas as pd
import json
import packet_analysis as analyis
import actions as A_set
import statistics

exec(open("./settings.txt").read())
packet_len=packet_len
n_packets=n_packets
send_rate_kbytes_per_s=send_rate_kbytes_per_s
n_packets_expected=n_packets_expected

class CreateTopo(Topo):

    def build(self, n=2):
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        self.addLink(s1, s2, bw=10, delay='0.2ms') # S1 --- S2 --> d=0.2ms, bw=20

        for h in range(1, n + 1):
            host_a = self.addHost('a%s' % h)
            bw = random.randint(1,10)
            self.addLink(host_a, s2, bw=bw, delay='0.2ms') # S2 --- (a1, a2, ..., a5) --> d=0.2ms, bw= 1-10

            host_b = self.addHost('b%s' % h)
            bw = random.randint(1,10)
            self.addLink(host_b, s1, bw=bw, delay='0.2ms') # S1 --- (b1, b2, ..., b5) --> d=0.2ms, bw= 1-10

        master = self.addHost('master', ip='10.0.0.41')
        self.addLink(master, s1, bw=10, delay='0.2ms') # Master --- S1 --> d=0.2ms, bw= 10
        slave = self.addHost('slave', ip='10.0.0.42')
        self.addLink(slave, s2, bw=10, delay='0.2ms') # Slave --- S2 --> d=0.2ms, bw= 10

        m1 = self.addHost('m1', ip='10.0.1.1')
        self.addLink(m1, s1, bw=10, delay='0.2ms') # Monitor --- S1 --> d=0.2ms, bw= 10
        m2 = self.addHost('m2', ip='10.0.1.2')
        self.addLink(m2, s2, bw=10, delay='0.2ms') # Monitor --- S2 --> d=0.2ms, bw= 10

def Exp01_pingCheck(h,j):
    os.system("sudo mn -c")
    setLogLevel('info')
    n=h
    exp=j
    topo = CreateTopo(n)
    net = Mininet(topo, link=TCLink,autoSetMacs=True)
    net.start()
    # CLI(net)
    n=n
    a = []
    b = []

    for i in range(1, n + 1):
        a.append(net['a%s' % i])
        b.append(net['b%s' % i])

    s1 = net['s1']
    master = net['master']
    slave = net['slave']
    m1 = net['m1']
    m2 = net['m2']

    print('*** Testing connectivity between pairs')

    for i in range(n):
        net.ping(hosts=[a[i], b[i]])

    print('******** Setting up AQM in S1 and ECN in hosts ********')

    s1.cmd('tc qdisc del dev s1-eth1 root')
    s1.cmd('tc qdisc add dev s1-eth1 root handle 1:0 htb default 1')
    s1.cmd('tc class add dev s1-eth1 classid 1:1 htb rate 10mbit')
    s1.cmd('tc qdisc add dev s1-eth1 parent 1:1 handle 10:1 fq_codel limit 1000')

    for i in range(n):
        a[i].cmd('sysctl -w net.ipv4.tcp_ecn=1')
        b[i].cmd('sysctl -w net.ipv4.tcp_ecn=1')

    print('*** Gathering network data for retraining congestion predictor...')
    s1.cmd('settings=$(<./cap.ini) && tshark -i s1-eth1 $settings > ./traces-{}.csv &'.format(exp))


    for i in range(1, n + 2):
        if i==n+1:
            makeTerm(slave, cmd='sysctl -w net.ipv4.tcp_ecn=1 && python3 ./b_reciever.py; read')
            makeTerm(master, cmd='sysctl -w net.ipv4.tcp_ecn=1 && python3 ./c_feedback.py; read')
            time.sleep(0.5)
            makeTerm(master, cmd='sysctl -w net.ipv4.tcp_ecn=1 && python3 ./a_sending.py; read')
            # slave.cmd('sysctl -w net.ipv4.tcp_ecn=1 && sudo nohup ../14-09-2022-Final/slave &')
            # master.cmd('sysctl -w net.ipv4.tcp_ecn=1 && sudo nohup ../14-09-2022-Final/master &')
            # # time.sleep(0.5)
            # # master.cmd('sysctl -w net.ipv4.tcp_ecn=1 && python3 ./a_sending.py')
            # # master.cmd('ping 10.0.0.42 -i 0.001 -c 1000 -s 1000 >./data/data.txt')

        else:
            a[i - 1].cmd('netcat -l 1234 >/dev/null &')  # A host on S2 acts as Server
            time.sleep(random.random() * 2)  # Each transmission starts after a random delay between 0.2 and 2.0 secs
            MB = random.randint(3, 630)  # Random amount of MB to transmit
            b[i - 1].cmd('dd if=./file.test bs={}M count=1 | nc 10.0.0.{} 1234 &'.format(MB, i))

    time.sleep(30)
    master.terminate()
    ec_val, MSE, MAE = ecp.retrain(exp)
    ec_pred = np.cumsum(ec_val, dtype=float)
    print('*** MSE and MAE of prediction based on re-training: %.2f %.2f' % (MSE, MAE))
    iter = 40
    S = 100  # Number of states: discrete levels of congestion [0, 100] in a period of 1 s
    A = np.arange(1, 7, 1)  # Set of actions: set value of target parameter in us
    epsilon = 0.5
    ind_action = len(A) - 1  # Start with default target (5 ms)

    max_ec_pred = 0
    max_ec_observ = 0
    hist_r = []
    del_q = []
    hist_rtt = []
    hist_tput = []
    hist_plr = []
    m2.cmd('iperf -s &')

    for i in range(iter):

        print('*** Interval number: %i' % i)
        print('*** Selected Action: %i' % (A[ind_action]))

        ## Observing current state (past second):

        m_error = False
        # target = A[ind_action]
        # interval = int(target / (0.05 * 1000))  # Tipycally, target is 5% of interval
        # s1.cmd('tc qdisc change dev r1-eth1 parent 1:1 handle 10:1 fq_codel limit 1000 target {}us interval {}ms'.format(
        #         target, interval))  # Change the parameters of AQM
        s1.cmd('tail -n 1000 ./traces-{}.csv > ./tmp_traces.csv'.format(exp))

        data = pd.read_csv('./tmp_traces.csv', header=None, usecols=[0], engine='python', error_bad_lines=False,
                           warn_bad_lines=False)

        ## Making congestion prediction:

        data = data.sort_values(by=[0], ascending=False)
        n_ecep = ecp.count(data, t_limit=1)
        Xn, yn = ecp.pdata(pd.Series(n_ecep))
        yp, MSE, MAE = ecp.predict(Xn, yn)
        ec_pred = np.cumsum(yp, dtype=float)
        ec_observ = np.cumsum(yn, dtype=float)

        if ec_observ.max() > max_ec_observ:
            max_ec_observ = ec_observ.max()  # Stores the max value of observed EC

        if ec_pred.max() > max_ec_pred:
            max_ec_pred = ec_pred.max()  # Stores the max value of predicted EC

        ec_curr = int((ec_observ.max() / max_ec_observ) * S - 1)
        ec_ahead = int((ec_pred.max() / max_ec_pred) * S - 1)

        # if i>0:
        #     slave.cmd('iperf -s &')
        #     master.cmd('ping 10.0.0.42 -i 0.001 -c 1000 -s 1000 -q | tail -1 > ./latency/ping.out &')
        #     master.cmd('iperf -c 10.0.0.42 -i 0.001 -p 6001 -n 1000 -t 1 | tail -1 > ./latency/tput.out')
        #     din = open('./tempfiles/ping.out').readlines()
        #     slice = ss.substringByInd(din[0], 26, 39)
        #     text = (slice.split('/'))
        #     mRTT = float(text[1])
        #     din = open('./tempfiles/tput.out').readlines()
        #     tput = float(ss.substringByInd(din[0], 34, 37))
        #     unit = ss.substringByInd(din[0], 39, 39)
        #     if unit == 'K':
        #         tput = tput * 0.001
        #     T_put=tput
        #     pack_loss=0
        # else:
        exec(open("./settings.txt").read())
        m1.cmd('ping 10.0.1.2 -i 0.001 -c {} -s {} -w 1 -q | tail -1 > ./latency/ping.out &'.format(n_packets, packet_len))
        m1.cmd('iperf -c 10.0.1.2 -i 0.001 -b {}M -n {} -t 1 | tail -1 > ./latency/tput.out'.format(send_rate_kbytes_per_s,packet_len))
        # makeTerm(slave, cmd='sysctl -w net.ipv4.tcp_ecn=1 && python3 ./b_reciever.py; read')
        # makeTerm(master, cmd='sysctl -w net.ipv4.tcp_ecn=1 && python3 ./c_feedback.py; read')
        # time.sleep(0.5)
        # makeTerm(master, cmd='sysctl -w net.ipv4.tcp_ecn=1 && python3 ./a_sending.py; read')
        # time.sleep(20)
        # mRTT, pack_loss, T_put = analyis.read_latencies_file("HD_{}".format(n_packets_expected))
        # slave.cmd('tail -n 2000 ./latency/HD_{} > ./latency/HD_{}_{}'.format(n_packets_expected, n_packets_expected,exp))
        statinfo = os.stat('./latency/ping.out')
        if statinfo.st_size < 10:
            print('*** No ping response')
            m_error = True
            mRTT = statistics.mean(hist_rtt)
        else:
            din = open('./latency/ping.out').readlines()
            slice = ss.substringByInd(din[0], 26, 39)
            text = (slice.split('/'))
            mRTT = float(text[1])

        hist_rtt.append(mRTT)
        print('*** mRTT: %.3f' % mRTT)

        # hist_plr.append(pack_loss)
        # print('*** Packet Loss Rate: %.3f' % pack_loss)

        statinfo = os.stat('./latency/tput.out')
        if statinfo.st_size < 10:
            print('*** No tput response. Setting R = 0')
            m_error = True
            mRTT = statistics.mean(hist_tput)
        else:
            din = open('./latency/tput.out').readlines()
            T_put = float(ss.substringByInd(din[0], 34, 37))
            unit = ss.substringByInd(din[0], 39, 39)
            if unit == 'K':
                T_put = T_put * 0.001

        hist_tput.append(T_put)

        hist_tput.append(T_put)
        print('*** Throughput: %.3f' % T_put)

        # hist_r.append(T_put - mRTT-pack_loss)
        hist_r.append(T_put/ mRTT)

        if m_error:
            R = 0
        else:
            R = hist_r[i]  # Reward is based on power function

        print('*** Reward: %.3f' % R)

        ## Updating Q-values:

        Q,delta_q = lrn.update(ec_curr, ind_action, R, ec_ahead)
        del_q.append(delta_q)

        ## Selecting action for next iteration:

        ind_action = lrn.action(ec_curr, epsilon)
        if mRTT<=10:
            A_set.select_packet_n(ind_action+7)
            A_set.select_pkt_rate(ind_action+7)
        else:
            A_set.select_packet_n(ind_action)
            A_set.select_pkt_rate(ind_action)

        # s1.cmd('tc -s -d qdisc show dev s11-eth1 >>./iaqm.stat')


    print('*** Saving Q-Table and historical rewards')

    # np.save('./Rewards.json', hist_r)
    # np.save('./Q-Values.json', Q)
    # np.save('./DeltaQ.json', del_q)

    # print('*** Stopping emulation')
    # slave.cmd('rm -f ./*.out &')
    slave.cmd('rm -f ./*.csv &')
    # m1.cmd('rm -f ./*.pcap &')

    net.stop()

    print('*** Experiment finished!')
    return hist_r, del_q, hist_rtt,hist_tput,hist_plr


def exp_ping():
    os.system("sudo mn -c")
    setLogLevel('info')
    n = 5
    topo = CreateTopo(n)
    net = Mininet(topo, link=TCLink, autoSetMacs=True)
    net.start()
    CLI(net) ### FOr checking


###################################### SIMULATIONS ########################
def experiment(h,itr):
    reward = []
    DeltaQ = []
    RTT = []
    Tput = []
    PLR=[]
    for i in range(itr):
        print(" $$$$$$$$$ Iteration ---{} $$$$$$$$$ ".format(i))
        r, delta_q, rtt, tput, plr = Exp01_pingCheck(h,i)

        reward.append(r)
        DeltaQ.append(delta_q)
        RTT.append(rtt)
        Tput.append(tput)
        PLR.append(plr)

    return reward, DeltaQ, RTT, Tput, PLR

def backup(filename, data):
    # with open('./final_results/store_results/%s.json' % (filename), 'w') as f:
    with open('./result/%s.json'  % (filename), 'w') as f:
        f.write(json.dumps(data))

if __name__ == "__main__":
    itr=5
    alpha = 0.5
    host=20
    #
    reward, DeltaQ, RTT, Tput, PLR= experiment(host,itr)
    # exp_ping()
    # #
    backup(filename='Reward_{}_{}_{}'.format(itr,alpha,host),data=reward)
    backup(filename='Delta_Q_{}_{}_{}'.format(itr,alpha,host),data=DeltaQ)
    backup(filename='RTT_{}_{}_{}'.format(itr, alpha,host), data=RTT)
    backup(filename='ThroughPut_{}_{}_{}'.format(itr, alpha,host), data=Tput)
    # backup(filename='PLR_{}_{}'.format(itr, alpha), data=PLR)
    print("Experiment End")



