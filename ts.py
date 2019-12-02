from string import Template

TS_PACKET_SIZE = 188


class TS:
    media_sdp = Template('m=video ${port} ${protocol} 33\r\n'
                         'a=rtpmap:33 MP2T/${rate}\r\n'
                         'a=framerate:${framerate}\r\n'
                         'c=${network_type} ${ip_type} 127.0.0.1\r\n')

    def generate_media_sdp(self, *, port, rate, protocol, framerate, network_type, ip_type, ip):
        return self.media_sdp.substitute(port=port, protocol=protocol,
                                         rate=rate,
                                         framerate=framerate,
                                         network_type=network_type, ip_type=ip_type, ip=ip)

    def get_ts_rtp_payload(self, file):
        while True:
            ts_packets = file.read(7*TS_PACKET_SIZE)
            length = len(ts_packets)
            if length <= 0:
                print('finish read ts file')
                break
            # print('read len is %d %d' % (length, length % 188))
            for i in range(length//188):
                if ts_packets[i*TS_PACKET_SIZE] != 0x47:
                    print('not 0x47 in head of %d' % i)
            yield ts_packets

    def get_video_duration(self, filename):
        file = open(filename, 'rb')
        packet_cnt = 1
        while packet_cnt <= 1024:
            file.seek(-packet_cnt*TS_PACKET_SIZE, 2)
            packet = file.read(TS_PACKET_SIZE)
            res = self.get_pcr_value(packet)
            if res != -1:
                return res
            packet_cnt += 1

    def get_pcr_value(self, data):
        if not (data[3] & 0x20):
            # print('no field')
            return -1
        length = data[4]
        if length == 0:
            # print('length is 0')
            return -1
        if not (data[5] & 0x10):
            # print('no pcr')
            return -1

        pref = data[6:6 + 4]
        v_ref = int.from_bytes(pref, 'big')
        v_ref = v_ref << 1
        v_ref += data[10] / 128
        v_ext = (data[10] % 2) * 256 + data[11]
        res = (v_ref * 300 + v_ext) // 27000
        return res




ts = TS()