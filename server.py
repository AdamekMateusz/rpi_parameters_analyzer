"""

Written by Mateusz Rzeczyca, Mateusz Adamek
Students - AGH University of Science and Technology
Cracow, 14.01.2021

"""


from scapy.all import ARP, Ether, srp
import matplotlib.pyplot as plt
import numpy as np
import netifaces
import requests
import argparse
import tkinter
import socket
import socket
import struct
import fcntl
import re
import os


class MACManager(object):

    mac_details_check_count = 5

    @staticmethod
    def __get_mac_details(mac_address):
        url = "https://api.macvendors.com/{}".format(mac_address) # API to get the vendor details

        i = 0
        while True:
            response = requests.get(url)

            if response.status_code != 200:
                if i == MACManager.mac_details_check_count:
                    return "Cannot retrieve mac details {} after {} times".format(MACManager.mac_details_check_count)

                i += 1
                continue

            return response.content.decode('utf-8')

    @staticmethod
    def get_network_interfaces():
        interfaces = netifaces.interfaces()
        return interfaces

    @staticmethod
    def get_mac_info_of_interface(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', bytes(ifname, 'utf-8')[:15]))

        mac_addr = ':'.join('%02x' % b for b in info[18:24])
        ip_addr = netifaces.ifaddresses(ifname)[netifaces.AF_INET][0]['addr']
        vendor = MACManager.__get_mac_details(mac_addr)

        return {"ip": ip_addr, "mac": mac_addr, "vendor": vendor}

    @staticmethod
    def get_mac_info_of_ip(address):
        target_ip = address + "/24"

        arp = ARP(pdst=target_ip)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp

        try:
            result = srp(packet, timeout=3, verbose=0)[0]
        except PermissionError:
            print("PermissionError: [Errno 1] Operation not permitted")
            exit(0)

        clients = []
        for sent, received in result:
            if address == received.psrc:
                vendor = __get_mac_details(received.hwsrc)
                clients.append({'ip': received.psrc, 'mac': received.hwsrc, 'vendor': vendor})

        print(clients)
        return clients


class ArgParser(object):
    """
    Class for argument parsing. Has abilities to retrieve the most important data
    like ip address, port, buffer size for server.
    """

    def __init__(self):
        """
        Initializes instance and parses all arguments. Afterwards you can call self.args
        with the name of the parameter.
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--ip', help='Server Ipv4 address', type=str, required=True)
        parser.add_argument('-p', '--port', help='Server Ipv4 port', type=int, required=True)
        parser.add_argument('-b', '--buffer', help='Packet size', type=int, required=True)
        self.args = parser.parse_args()

    def get_server_data(self):
        """
        Returns:
            server_data(tuple(str, int)): returns tuple, where (ip addr in str, port in int)
        """
        return (self.args.ip, self.args.port)

    def get_buffer(self):
        """
        Returns:
            buffer(int): buffer size / packet size
        """
        return self.args.buffer


class BatchedData(object):
    """
    BatchedData is class that contain only static members, which are used
    for cleaner interpretation of sent data by client. Contains cpu_usage,
    uptime, temperature, clock_arm and bitrate. Also has print() method which
    prints current state of the members.
    """

    cpu_usage = ""
    uptime = ""
    temperature = ""
    clock_arm = ""
    bitrate = ("", "")

    @staticmethod
    def print():
        """
        Prints current state of the members of BatchedData.
        """
        print('{} - {} - {} - {} - {} - {}'.format(
            BatchedData.cpu_usage, BatchedData.uptime, BatchedData.temperature, 
            BatchedData.clock_arm, BatchedData.bitrate[0], BatchedData.bitrate[1]
        ))
    

class TCPServer(object):
    """
    TCPServer is a class for creating server and management all incoming connections.
    It is also helper for retrieving batched data from the received data.
    """

    def __init__(self, server_addr, buffer_size):
        """
        Initializes socket and binds server. If cannot be bound, method exits the program.
        Looks for only one device!

        Attributes:
            server_addr(tuple(str, int)): str should contain ip address and int should be port
            buffer_size(int): packet size that will be received
        """
        self.client_socket = None
        self.client_addr_info = ("Unknown", -1)
        self.buffer_size = buffer_size
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.server_socket.bind(server_addr)
        except OSError:
            print("OSError: address already in use, other app is using it...")
            exit(0)

        self.server_socket.listen(1)

    def accept_incoming_connection_if_available(self):
        """
        Accepts incoming connection and prints data about the client connected.
        """
        self.client_socket, self.client_addr_info = self.server_socket.accept()
        print(self.client_addr_info)

    def receive_and_decode_data(self):
        """
        Receives packets with the size of self.buffer_size, decodes it and
        then return.

        Returns:
            decoded_data(str): data received and decoded from client.
        """
        received_data = self.client_socket.recv(self.buffer_size)
        decoded_data = received_data.decode("utf8")
        return decoded_data

    def encode_and_send_data(self, data):
        """
        Encodes given data and sends it to the connected client.

        Attributes:
            data(str): data in str format, that is ready to sent.
        """
        encoded_data = data.encode('utf8')
        self.client_socket.send(encoded_data)

    def retrieve_client_ip_addr(self):
        """
        Returns currently connected clients ip address.

        Returns:
            ip_addr(str): clients ip address
        """
        return self.client_addr_info[0]

    def retrieve_batched_data(self, batched_data):
        """
        Method retrieves all needed information from batched data. It is expected
        that second package sent will contain those information.

        Attributes:
            batched_data(str): batched data sent, that contains all Linux machine parameters

        Returns:
            BatchedData(): instance of the BatchedData()
        """
        double_values_in = r"[-+]?\d*\.\d+|\d+"
        output_lst = re.findall(double_values_in, batched_data)

        BatchedData.cpu_usage = float(output_lst[0])
        BatchedData.uptime = float(output_lst[1])
        BatchedData.temperature = float(output_lst[2])
        BatchedData.clock_arm = float(output_lst[3])
        BatchedData.bitrate = (float(output_lst[4]), float(output_lst[5]))

        return BatchedData()


class Subplotter(object):
    """
    Subplotter is a helper class for Plotter. It contains all needed
    information for one subplot, it definitely makes Plotter much cleaner,
    when data is separated from implementation.
    """

    def __init__(self, axs, x):
        """
        Initializes object with created subplot, its x axis data.

        Attributes:
            axs(): subplot from matplotlib
            x(list(int)): list for x axis
        """
        self.axs = axs
        self.y = np.array([0])
        self.lines, = self.axs.plot(x, self.y)

    def append_new_value(self, val):
        """
        Appends new value to y axis.

        Attributes:
            val(int): value, which will be appended to y axis
        """
        self.y = np.append(self.y, val)

    def draw(self, x):
        """
        Updates x and y axis, recalculates the whole plot and scale with the new data.

        Attributes:
            x(list(int)): list of the x axis data
        """
        self.lines.set_xdata(x)
        self.lines.set_ydata(self.y)
        self.axs.relim()
        self.axs.autoscale_view()


class Plotter(object):
    """
    Plotter is a matplotlib abstraction layer, which makes clear
    what is plotted and what should be updated.
    """

    def __init__(self):
        """
        Creates 6 subplots for all client data.
        """
        self.iterator = 0
        self.x_time = np.array([0])

        self.figure, all_subplots = plt.subplots(6)
        self.cpu_usage = Subplotter(all_subplots[0], self.x_time)
        self.uptime = Subplotter(all_subplots[1], self.x_time)
        self.temperature = Subplotter(all_subplots[2], self.x_time)
        self.clock_arm = Subplotter(all_subplots[3], self.x_time)
        self.bitrate_send = Subplotter(all_subplots[4], self.x_time)
        self.bitrate_recv = Subplotter(all_subplots[5], self.x_time)

        plt.show(block=False)

    def push_batched_data(self, batched_data):
        """
        Pushes all collected data to the correct subplots.

        Attributes:
            batched_data(BatchedData): instance with all retrieved data from the client.
        """
        self.cpu_usage.append_new_value(batched_data.cpu_usage)
        self.uptime.append_new_value(batched_data.uptime)
        self.temperature.append_new_value(batched_data.temperature)
        self.clock_arm.append_new_value(batched_data.clock_arm)
        self.bitrate_send.append_new_value(batched_data.bitrate[0])
        self.bitrate_recv.append_new_value(batched_data.bitrate[1])

    def draw(self):
        """
        Method draws new data to the figure created with constructor call.
        Looks for ValueError.
        """
        try:
            self.x_time = np.append(self.x_time, self.iterator)
            self.iterator += 1

            self.cpu_usage.draw(self.x_time)
            self.uptime.draw(self.x_time)
            self.temperature.draw(self.x_time)
            self.clock_arm.draw(self.x_time)
            self.bitrate_send.draw(self.x_time)
            self.bitrate_recv.draw(self.x_time)

            self.figure.canvas.draw()
            self.figure.canvas.flush_events()
        except ValueError:
            print("ValueError: shape mismatch: objects cannot be broadcast to a single shape")


def main(args):

    interfaces = MACManager.get_network_interfaces()
    for interface in interfaces:
        mac_info = MACManager.get_mac_info_of_interface(interface)
        print("MAC_INFO: {} - {} - {}".format(mac_info['ip'], mac_info['mac'], mac_info['vendor']))

    server = TCPServer(
        server_addr=args.get_server_data(),
        buffer_size=args.get_buffer()
    )

    plotter = Plotter()

    while True:
        server.accept_incoming_connection_if_available()
        clients_ip_addr = server.retrieve_client_ip_addr()

        mac_info = MACManager.get_mac_info_of_ip(clients_ip_addr)
        if mac_info:
            print("MAC_INFO: {} - {} - {}".format(mac_info[0]['ip'], mac_info[0]['mac'], mac_info[0]['vendor']))

        received_data = server.receive_and_decode_data()
        print(received_data)

        server.encode_and_send_data(received_data)

        while True:
            received_data = server.receive_and_decode_data()
            print(received_data)
            if len(received_data) == 0:
                print("Clossing connection and waiting...")
                break
            
            batched_data = server.retrieve_batched_data(received_data)
            batched_data.print()

            plotter.push_batched_data(batched_data)
            plotter.draw()
            

if __name__ == "__main__":
    if os.geteuid() != 0:
        exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting...")

    args = ArgParser()

    try:
        main(args)
    except KeyboardInterrupt:
        print("KeyboardInterrupt: Ctrl-C, exitting...")
    except tkinter.TclError:
        print("_tkinter.TclError: user closed window, exitting...")
    
