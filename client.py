"""

Written by Mateusz Rzeczyca, Mateusz Adamek, Hubert Chrzan
Students - AGH University of Science and Technology
Cracow, 14.01.2021

"""

import argparse
import socket
import time
import os
import re


class ArgParser(object):
    """
    Class for argument parsing. Has abilities to retrieve the most important data
    like ip address, port, buffer size and transmit time for client and iperf configuration.
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
        parser.add_argument('-t', '--transmit_time', help='Transmit time on iperf', type=int, required=True)
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

    def get_transmit_time(self):
        """
        Returns:
            transmit_time(int): transmit time for iperf configuration
        """
        return self.args.transmit_time


class LinuxDependencies(object):

    @staticmethod
    def __is_installed(program):
        if os.path.exists("/bin/{}".format(program)):
            return True
        else:
            return False

    @staticmethod
    def __install_program(program, program_to_check=None):
        os.system("sudo apt-get -y install --assume-yes {}".format(program))
        
        if program_to_check:
            program = program_to_check

        if LinuxDependencies.__is_installed(program):
            print("Installation complete - {}!".format(program))
        else:
            print("Installation incomplete, exitting...")
            exit(0)

    @staticmethod
    def install_iperf3_if_not_already_installed():
        if LinuxDependencies.__is_installed('iperf3'):
            print("iperf3 is installed!")
            return
        else:
            print('iperf3 cannot be found, installing...')
            if LinuxDependencies.__is_installed("apt-get"):
                LinuxDependencies.__install_program("iperf3")
            else:
                print("You're not using Debian linux distro, install manually! Exitting...")
                exit(0)
            
    @staticmethod        
    def install_iostat_if_not_already_installed():
        if LinuxDependencies.__is_installed('iostat'):
            print("iostat is installed!")
        else:
            print('iostat cannot be found, installing...')
            if LinuxDependencies.__is_installed("apt-get"):
                LinuxDependencies.__install_program("sysstat", "iostat")
            else:
                print("You're not using Debian linux distro, install manually! Exitting...")
                exit(0)


class TCPClient(object):
    """
    TCPClient is a class for creating and managing connection with the server. It is also 
    responsible for batching data in order to send only one batched packet.
    """

    def __init__(self, server_addr, buffer_size):
        """
        Creates socket and connects to the server. After constructor call you can
        send and receive packets from server.

        Attributes:
            server_addr(tuple(str, int)): server data, where str is a IP address and int is a port
            buffer_size(int): packet size for receiving data
        """
        self.buffer_size = buffer_size
        self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.client_socket.connect(server_addr)

    def __del__(self):
        """
        Closes sockets, so that no connection on server is pending during destructor call.
        """
        self.client_socket.close()

    def encode_and_send_data(self, data):
        """
        Encodes and sends to the server given data.

        Attributes:
            data(str): data that will be encoded and sent to server
        """
        ready_to_send_data = data.encode("utf8")
        self.client_socket.send(ready_to_send_data)

    def receive_and_decode_data(self):
        """
        Receives and decodes data from the server.

        Returns:
            decoded_data(str): decoded data received from the server in str format
        """
        received_data = self.client_socket.recv(self.buffer_size)
        decoded_data = received_data.decode("utf8")
        return decoded_data

    def batch_device_data(self, cpu_usage, uptime, temperature, clock_arm, bitrate):
        """
        Batches all collected device data, so that it can be encoded and sent. You can just
        call encode_and_send_data() afterwards with return value of this method.

        Attributes:
            cpu_usage(str): cpu usage retrieved from bash
            uptime(str): device uptime retrieved from bash
            temperature(str): device temperature retrieved from bash
            clock_arm(str): ARM clock retrieved from bash
            bitrate(tuple(str, str)): sender and receiver iperf bitrate retrieved from bash

        Returns:
            batched(str): ready to send batched data
        """
        batched = ""
        batched += "CPU_Usage: {} ".format(cpu_usage)
        batched += "Uptime: {} ".format(uptime)
        batched += "Temperature: {} ".format(temperature)
        batched += "ClockArm: {} ".format(clock_arm)
        batched += "SendBitrate: {} ".format(bitrate[0])
        batched += "RecvBitrate: {}".format(bitrate[1])
        return batched


class BashCmd(object):
    """
    BashCmd is a class, which contains only static methods used to retrieve
    some important information about current device.
    """

    @staticmethod
    def __execute_command(cmd):
        """
        Executes given command on Linux machine and returns its output.

        Attributes:
            cmd(str): command to execute
        
        Returns:
            output(str): output of executed command
        """
        stream = os.popen(cmd)
        output = stream.read()
        return output

    @staticmethod
    def __get_first_double_value_from(output):
        """
        Sometimes bash command can return some value, which looks like float / double type.
        This method retrieves this file from the command output.

        Attributes:
            output(str): output of executed bash command

        Returns:
            retrieved_float(str): first double / float value in output of bash command
        """
        double_values_in = r"[-+]?\d*\.\d+|\d+"
        output_lst = re.findall(double_values_in, output)
        return output_lst[0]

    @staticmethod
    def get_cpu_usage():
        """
        Method returns cpu usage of the device.

        Returns:
            cpu_usage(str)
        """
        cpu_usage_cmd = "iostat -c | awk '{print $3}' | sed '4q;d'"
        output = BashCmd.__execute_command(cpu_usage_cmd)
        cpu_usage = BashCmd.__get_first_double_value_from(output)
        return cpu_usage
    
    @staticmethod
    def get_device_uptime():
        """
        Method returns device uptime, how much time device is ON.

        Returns:
            system_uptime_seconds(str)
        """
        proc_uptime_cmd = "cat /proc/uptime"
        output = BashCmd.__execute_command(proc_uptime_cmd)
        system_uptime_seconds = BashCmd.__get_first_double_value_from(output)
        return system_uptime_seconds

    @staticmethod
    def get_device_temperature():
        """
        Returns device temperature. Make sure that this is RPi, so that
        this command can only on RPi.

        Returns:
            temperature(str): RPi temperature in celsius
        """
        device_temperature_cmd = "vcgencmd measure_temp"
        output = BashCmd.__execute_command(device_temperature_cmd)
        temperature = BashCmd.__get_first_double_value_from(output)
        return temperature

    @staticmethod
    def get_clock_arm():
        """
        Returns RPi's clock arm.

        Returns:
            clock_arm(str): RPi's clock arm
        """
        clock_arm_cmd = "vcgencmd measure_clock arm"
        output = BashCmd.__execute_command(clock_arm_cmd)
        clock_arm = BashCmd.__get_first_double_value_from(output)
        return clock_arm

    @staticmethod
    def get_bitrate_from_iperf_logs(logfile, bitrate_type):
        """
        Method returns sender and receiver iperf logs. You should pass, which logs file
        should be parsed and also which type should be retrieved. Executed command:

        cat {logfile} | tail -4 | awk '{print $7}' | sed '{bitrate_type}q;d'

        Attributes:
            logfile(str): log file, which will be parsed
            bitrate_type(int): 1 stands for sender, 2 for receiver

        Returns:
            bitrate(str): retrieved bitrate
        """
        last_lines_cmd = "cat {} | tail -4 |".format(logfile)
        awk_cmd = "awk '{print $7}' |"
        retrieve_line_cmd = "sed '{}q;d'".format(bitrate_type)

        bitrate_cmd = last_lines_cmd + awk_cmd + retrieve_line_cmd
        output = BashCmd.__execute_command(bitrate_cmd)
        bitrate = BashCmd.__get_first_double_value_from(output)
        
        return bitrate
    

class IperfFunctor(object):
    """
    IperfFunctor is a abstraction for iperf management on Linux. With this we can
    parse iperf output and run the command itself.
    """

    @property
    def time_to_transmit(self):
        return self.__time_to_transmit

    @time_to_transmit.setter
    def time_to_transmit(self, new_time):
        self.__time_to_transmit = new_time

    @property
    def interval(self):
        return self.__interval
    
    @interval.setter
    def interval(self, new_interval):
        self.__interval = new_interval

    @property
    def logfile(self):
        return self.__logfile

    @logfile.setter
    def logfile(self, new_logfile):
        self.__logfile = new_logfile

    def __init__(self):
        """
        Just initializes object with its basic values. Those defined as properties can be 
        modified by other methods / classes.
        """
        self.__iperf_cmd = "iperf3 -c {host_ip} -t {time} -i {interval} -p {port} -R --logfile {logfile}"
        self.__server_ip = "bouygues.testdebit.info"
        self.__time_to_transmit = 10
        self.__interval = 2
        self.__logfile = "logs.txt"
        self.__port = 5209

    def run(self):
        """
        Runs iperf command with instance self parameters and then sleeps needed time.
        After execution of this method you can parse_file() in order to retrieve
        sender / receiver bitrate.
        """
        cmd = self.__iperf_cmd.format(
            host_ip=self.__server_ip, 
            time=self.time_to_transmit, 
            interval=self.interval, 
            port=self.__port, 
            logfile=self.logfile
        )
        os.system(cmd)
        print("Sleeping {} and waiting for iperf...".format(self.time_to_transmit))
        time.sleep(self.time_to_transmit)

    def parse_file(self):
        """
        Method parses iperf logs output and returns sender / receiver bitrate. Method also
        deletes old log file, because it is not needed after parsing.

        Returns:
            bitrate(tuple(str, str)): bitrate[0] stands for receiver bitrate, bitrate[1] for sender
        """
        receiver_bitrate_type = "1"
        sender_bitrate_type = "2"
        receiver_bitrate = BashCmd.get_bitrate_from_iperf_logs(self.logfile, receiver_bitrate_type)
        sender_bitrate = BashCmd.get_bitrate_from_iperf_logs(self.logfile, sender_bitrate_type)

        if os.path.exists(self.logfile):
            os.remove(self.logfile)
        else:
            print("From unknown reason {} cannot be deleted!".format(self.logfile))

        return (receiver_bitrate, sender_bitrate)


def main(args):
    LinuxDependencies.install_iperf3_if_not_already_installed()
    LinuxDependencies.install_iostat_if_not_already_installed()

    iperf = IperfFunctor()
    iperf.time_to_transmit = args.get_transmit_time()
    iperf.interval = 2
    iperf.logfile = dir_path = os.path.dirname(os.path.realpath(__file__)) + "/logs.txt"

    client = TCPClient(
        server_addr=args.get_server_data(), 
        buffer_size=args.get_buffer()
    )

    data = input('Input some data: ')
    client.encode_and_send_data(data)

    data = client.receive_and_decode_data()
    print("Received data: {}".format(data))

    while True:
        iperf.run()

        data = client.batch_device_data(
            cpu_usage=BashCmd.get_cpu_usage(), 
            uptime=BashCmd.get_device_uptime(), 
            temperature=BashCmd.get_device_temperature(), 
            clock_arm=BashCmd.get_clock_arm(),
            bitrate=iperf.parse_file()
        )
        print("Batched: {}".format(data))
        client.encode_and_send_data(data)
        time.sleep(2)


if __name__ == "__main__":
    args = ArgParser()

    try:
        main(args)
    except KeyboardInterrupt:
        print("KeyboardInterrupt: Ctrl-C, exitting...")
    except BrokenPipeError:
        print("BrokenPipeError: server has ended connection, exitting...")
    except ConnectionResetError:
        print("ConnectionResetError: server has an issue and ended connection, exitting...")

    
