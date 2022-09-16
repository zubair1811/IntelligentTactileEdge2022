
def select_packet_n(action):
    with open("../14-09-2022-Final/settings.txt", "r") as file:
        line_no = file.readlines()
    with open("../14-09-2022-Final/settings.txt", "r") as file:
        list_of_lines = file.read()
    if action == 1:
        pkt_leg = 800
    elif action == 2:
        pkt_leg = 1000
    elif action == 3:
        pkt_leg = 128
    elif action == 4:
        pkt_leg = 200
    elif action == 5:
        pkt_leg = 512
    elif action == 6:
        pkt_leg = 150
    elif action == 7:
        pkt_leg = 300
    else:
        pkt_leg = 1000
    data1 = line_no[2][11:]
    filedata1 = list_of_lines.replace(f'packet_len={data1}', f'packet_len={pkt_leg}\n')
    with open("../14-09-2022-Final/settings.txt", "w") as file:
        list_of_lines = file.write(filedata1)



def select_pkt_rate(action):
    with open("../14-09-2022-Final/settings.txt", "r") as file:
        line_no = file.readlines()
    with open("../14-09-2022-Final/settings.txt", "r") as file:
        list_of_lines = file.read()
    if action == 1:
        pkt_rate=500
    elif action == 2:
        pkt_rate = 3
    elif action == 3:
        pkt_rate = 50
    elif action == 4:
        pkt_rate = 5
    elif action == 5:
        pkt_rate = 100
    elif action == 6:
        pkt_rate = 150
    elif action == 7:
        pkt_rate = 1000
    else:
        pkt_rate = 50

    data2 = line_no[4][23:]
    print(data2)
    filedata2 = list_of_lines.replace(f'send_rate_kbytes_per_s={data2}', f'send_rate_kbytes_per_s={pkt_rate}\n')
    with open("../14-09-2022-Final/settings.txt", "w") as file:
        list_of_lines = file.write(filedata2)


select_packet_n(9)
select_pkt_rate(9)