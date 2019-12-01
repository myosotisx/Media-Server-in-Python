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


ts = TS()