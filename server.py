import socket
import threading
from urllib.parse import urlparse
from os import path

import util
import rtsp
import time
from rtsp import rtsp
from rtp import RTP_Header
from h264 import h264
from aac import aac
from ts import TS_PACKET_SIZE
from ts import ts


class Server:
    IDLE = 0
    READY = 1
    PLAY = 2

    def __init__(self, ip, rtsp_port, rtp_port, rtcp_port, backlog, root='Videos'):
        self.server_ip = ip
        self.server_rtsp_port = rtsp_port
        self.server_rtp_port = rtp_port
        self.server_rtcp_port = rtcp_port
        self.server_backlog = backlog
        self.server_root = root

        self.server_rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_rtsp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_rtsp_socket.bind((self.server_ip, self.server_rtsp_port))

        self.server_rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_rtp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_rtp_socket.bind((self.server_ip, self.server_rtp_port))

        self.server_rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_rtcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_rtcp_socket.bind((self.server_ip, self.server_rtcp_port))

        self.client_rtsp_socket = [None] * self.server_backlog
        self.client_rtp_socket = [None] * self.server_backlog
        self.client_rtp_port = [None] * self.server_backlog
        self.client_rtcp_port = [None] * self.server_backlog
        self.client_addr = [None] * self.server_backlog
        self.client_rtsp_thread = [None] * self.server_backlog
        self.client_rtp_thread = [None] * self.server_backlog
        self.client_rtcp_thread = [None] * self.server_backlog
        self.client_status = [None] * self.server_backlog
        self.client_session_id = [0] * self.server_backlog
        self.client_video_filepath = [None] * self.server_backlog
        self.client_play_event = [None] * self.server_backlog
        self.client_video_duration = [None] * self.server_backlog
        self.client_video_file = [None] * self.server_backlog
        self.client_play_speed = [1.0] * self.server_backlog

        self.session_id_generator = util.random_generator(1000)

    def start(self):
        self.server_rtsp_socket.listen(self.server_backlog)
        while True:
            new_rtsp_socket, new_addr = self.server_rtsp_socket.accept()
            client_index = self.init_client(new_rtsp_socket, new_addr)
            if client_index == -1:
                continue
            self.client_rtsp_thread[client_index] = threading.Thread(target=self.handle_client, args=(client_index,))
            self.client_rtsp_thread[client_index].start()

    def stream(self, client_index, filepath):
        # check file type
        file_ext = path.splitext(filepath)[1]
        if file_ext != '.h264' and file_ext != '.aac' and file_ext != '.ts':
            print('Error invalid file type ' + file_ext)
            return

        try:
            self.client_video_file[client_index] = open(filepath, 'rb')
        except:
            print('Error: fail to open file ' + filepath)
            return

        rtp_header = RTP_Header()
        rtp_header.set_header(2, 0, 0, 0, 0, 0, rtp_header.get_payload_type(file_ext), 10)
        while True:
            if self.client_status[client_index] == self.READY:
                self.client_play_event[client_index].wait()
            if self.client_status[client_index] == self.IDLE:
                break
            rtp_payload = self.client_video_file[client_index].read(7*TS_PACKET_SIZE)
            if not rtp_payload:
                continue
            try:
                self.server_rtp_socket.sendto(rtp_header.header + rtp_payload, (self.client_addr[client_index][0],
                                                                            self.client_rtp_port[client_index]))
            except:
                break
            rtp_header.increase_seq()
            time.sleep(0.001/self.client_play_speed[client_index])
        if self.client_video_file[client_index]:
            self.client_video_file[client_index].close()

    def control(self, client_index):
        while True:
            data = self.server_rtcp_socket.recv(1024)
            # print(data.decode())

    def init_client(self, rtsp_socket, addr):
        for i in range(self.server_backlog):
            if not self.client_session_id[i]:
                self.client_session_id[i] = next(self.session_id_generator)
                # self.mapper[self.client_session_id[i]] = i
                self.client_rtsp_socket[i] = rtsp_socket
                self.client_rtp_socket[i] = None
                self.client_addr[i] = addr
                self.client_rtsp_thread[i] = None
                self.client_rtp_thread[i] = None
                self.client_status[i] = self.IDLE
                return i
        return -1

    def handle_client(self, client_index):
        while True:
            try:
                request_bytes = self.client_rtsp_socket[client_index].recv(1024)
            except:
                self.destroy_client(client_index)
                break
            if request_bytes:
                self.mapping_rtsp_request(client_index, request_bytes.decode('utf-8'))

    def mapping_rtsp_request(self, client_index, request):
        print(request)
        cmd = request.split('\n')[0].split(' ')[0]
        if cmd == 'OPTIONS':
            self.handle_OPTIONS(client_index, request)
        elif cmd == 'DESCRIBE':
            self.handle_DESCRIBE(client_index, request)
        elif cmd == 'SETUP':
            self.handle_SETUP(client_index, request)
        elif cmd == 'PLAY':
            self.handle_PLAY(client_index, request)
        elif cmd == 'PAUSE':
            self.handle_PAUSE(client_index, request)
        elif cmd == 'TEARDOWN':
            self.handle_TEARDOWN(client_index, request)

    def handle_OPTIONS(self, client_index, request):
        if self.client_status[client_index] != self.IDLE:
            return
        request_dict = rtsp.get_request_dict(request)
        seq = int(request_dict.get('CSeq'))
        if seq is None:
            return
        response_dict = {'CSeq': str(seq), 'Public': 'OPTIONS, DESCRIBE, SETUP, TEARDOWN, PLAY'}
        response = rtsp.generate_response(response_dict, type=rtsp.OK)
        self.client_rtsp_socket[client_index].send(response.encode())

    def handle_DESCRIBE(self, client_index, request):
        if self.client_status[client_index] != self.IDLE:
            return
        request_dict = rtsp.get_request_dict(request)
        seq = int(request_dict.get('CSeq'))
        if seq is None:
            return
        control_sdp_dict = {'sdp_version': 0, 'user': '-',
                            'session_id': self.client_session_id[client_index],
                            'session_version': 1, 'network_type': 'IN',
                            'ip_type': 'IP4', 'ip': self.server_ip}

        ts_sdp_dict = {'port': 9832, 'protocol': 'RTP/AVP', 'rate': 90000, 'framerate': 25,
                       'network_type': 'IN', 'ip_type': 'IP4', 'ip': self.client_addr[client_index][0]}
        sdp = rtsp.generate_session_sdp(**control_sdp_dict)+ts.generate_media_sdp(**ts_sdp_dict)
        response_dict = {'CSeq': str(seq), 'Content-length': str(len(sdp)), 'Content-type': 'application/sdp'}
        response = rtsp.generate_response(response_dict, type=rtsp.OK, other=sdp)
        self.client_rtsp_socket[client_index].send(response.encode())

    def handle_SETUP(self, client_index, request):
        if self.client_status[client_index] != self.IDLE:
            return

        request_dict = rtsp.get_request_dict(request)
        seq = int(request_dict.get('CSeq'))
        if seq is None:
            return

        transport_info = request_dict.get('Transport')
        if not transport_info:
            return

        self.client_rtp_port[client_index], self.client_rtcp_port[client_index] = util.match_rtp_rtcp_port(
            transport_info)
        if not self.client_rtp_port[client_index] or not self.client_rtcp_port[client_index]:
            return

        path_tup = util.parse_path(request, self.server_root)
        self.client_video_filepath[client_index] = path.join(path_tup[0], path_tup[1] + '.ts')
        util.make_stream_file(self.client_video_filepath[client_index])
        self.client_status[client_index] = self.READY
        response_dict = {'CSeq': str(seq), 'Transport': 'RTP/AVP;unicast;client_port=%d-%d;server_port=%d-%d' %
                                                        (self.client_rtp_port[client_index],
                                                         self.client_rtcp_port[client_index],
                                                         self.server_rtp_port,
                                                         self.server_rtcp_port),
                         'Session': str(self.client_session_id[client_index])}

        response = rtsp.generate_response(response_dict, type=rtsp.OK)
        self.client_rtsp_socket[client_index].send(response.encode())

    def handle_PLAY(self, client_index, request):
        # if self.client_status[client_index] != self.READY:
        #     return
        request_dict = rtsp.get_request_dict(request)
        seq = int(request_dict.get('CSeq'))
        session_id = int(request_dict.get('Session'))
        if seq is None or session_id != self.client_session_id[client_index]:
            return

        speed = request_dict.get('Speed')
        if not (speed is None):
            try:
                self.client_play_speed[client_index] = float(speed)
            except:
                self.client_play_speed[client_index] = 1.0

        if not self.client_rtp_thread[client_index]:
            if self.client_status[client_index] != self.READY:
                return
            # start stream
            video_filepath = self.client_video_filepath[client_index]
            if video_filepath:
                self.client_status[client_index] = self.PLAY

                response_dict = {'CSeq': str(seq),
                                 'Session': str(self.client_session_id[client_index]),
                                 'Range': 'npt=0.000-',
                                 'Speed': str(self.client_play_speed[client_index])}
                duration = ts.get_video_duration(video_filepath)
                if duration != -1:
                    duration = duration / 1000  # msec to sec
                    self.client_video_duration[client_index] = duration
                    response_dict['Range'] = 'npt=0.000-%.3f' % self.client_video_duration[client_index]

                response = rtsp.generate_response(response_dict, type=rtsp.OK)
                self.client_rtsp_socket[client_index].send(response.encode())
                self.client_rtp_thread[client_index] = threading.Thread(target=self.stream, args=(client_index,
                                                                                                  video_filepath))
                self.client_status[client_index] = self.PLAY
                self.client_play_event[client_index] = threading.Event()
                self.client_rtp_thread[client_index].start()
                self.client_rtcp_thread[client_index] = threading.Thread(target=self.control, args=(client_index,))
                self.client_rtcp_thread[client_index].start()
        else:
            response_dict = {'CSeq': str(seq),
                             'Session': str(self.client_session_id[client_index]),
                             'Range': 'npt=now-',
                             'Speed': str(self.client_play_speed[client_index])}
            start_time, end_time = util.match_media_time(request)
            if start_time != 'now':
                # reposition stream
                if self.client_status[client_index] != self.READY:
                    return
                self.client_video_file[client_index].seek(0, 0)
                # search for the start packet
                start_time = float(start_time) * 1000
                while True:
                    data = self.client_video_file[client_index].read(TS_PACKET_SIZE)
                    if not data:
                        break
                    pcr = ts.get_pcr_value(data)
                    if pcr >= start_time:  # compare with msec
                        self.client_video_file[client_index].seek(-TS_PACKET_SIZE, 1)
                        start_time = pcr / 1000  # transfer to sec
                        break
                if self.client_video_duration[client_index]:
                    response_dict['Range'] = 'npt=%.3f-%.3f' % (start_time, self.client_video_duration[client_index])
                else:
                    response_dict['Range'] = 'npt=%.3f-' % start_time
            elif self.client_video_duration[client_index]:
                # resume stream
                response_dict['Range'] = 'npt=now-%.3f' % self.client_video_duration[client_index]
            response = rtsp.generate_response(response_dict, type=rtsp.OK)
            self.client_rtsp_socket[client_index].send(response.encode())
            self.client_status[client_index] = self.PLAY
            self.client_play_event[client_index].set()

    def handle_PAUSE(self, client_index, request):
        if self.client_status[client_index] != self.PLAY:
            return

        request_dict = rtsp.get_request_dict(request)
        seq = int(request_dict.get('CSeq'))
        session_id = int(request_dict.get('Session'))
        if seq is None or session_id != self.client_session_id[client_index]:
            return

        self.client_play_event[client_index].clear()
        self.client_status[client_index] = self.READY

        response_dict = {'CSeq': str(seq),
                         'Session': str(self.client_session_id[client_index])}
        response = rtsp.generate_response(response_dict, type=rtsp.OK)
        self.client_rtsp_socket[client_index].send(response.encode())

    def handle_TEARDOWN(self, client_index, request):
        request_dict = rtsp.get_request_dict(request)
        seq = int(request_dict.get('CSeq'))
        session_id = int(request_dict.get('Session'))
        if seq is None or session_id != self.client_session_id[client_index]:
            return

        response_dict = {'CSeq': str(seq),
                         'Session': str(self.client_session_id[client_index])}
        response = rtsp.generate_response(response_dict, type=rtsp.OK)
        self.client_rtsp_socket[client_index].send(response.encode())
        self.destroy_client(client_index)

    def destroy_client(self, client_index):
        # reset client status
        self.client_status[client_index] = self.IDLE

        # reset client rtsp socket
        if self.client_rtsp_socket[client_index]:
            # self.client_rtsp_socket[client_index].shutdown(socket.SHUT_RDWR)
            self.client_rtsp_socket[client_index].close()
            self.client_rtsp_socket[client_index] = None

        # reset client rtp socket
        if self.client_rtp_socket[client_index]:
            # self.client_rtp_socket[client_index].shutdown(socket.SHUT_RDWR)
            self.client_rtp_socket[client_index].close()
            self.client_rtp_socket[client_index] = None

        # reset client thread
        self.client_rtsp_thread[client_index] = None
        self.client_rtp_thread[client_index] = None
        self.client_rtcp_thread[client_index] = None
        self.client_play_event[client_index] = None

        # reset client parameters
        self.client_rtp_port[client_index] = None
        self.client_rtcp_port[client_index] = None
        self.client_addr[client_index] = None
        self.client_session_id[client_index] = 0
        self.client_video_filepath[client_index] = None
        self.client_video_duration[client_index] = None
        self.client_video_file[client_index] = None
        self.client_play_speed[client_index] = 1.0


server = Server('127.0.0.1', 57501, 57502, 57503, 10)
server.start()
