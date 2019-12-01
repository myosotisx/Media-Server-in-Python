from string import Template


class AAC:
    media_sdp = Template('m=audio ${dst_port} ${protocol} 97\r\na=rtpmap:97 ${codec}/${rate}/${chanel}\r\nc=${network_type} ${ip_type} ${dst_ip}\r\n')

    def generate_media_sdp(self, *, dst_port, protocol, codec, rate, chanel, network_type, ip_type, dst_ip):
        return self.media_sdp.substitute(dst_port=str(dst_port), protocol=protocol,
                                         codec=codec, rate=str(rate), chanel=str(chanel),
                                         network_type=network_type, ip_type=ip_type,
                                         dst_ip=dst_ip)

    def get_acc_frame_length(self, adts_header):
        return ((adts_header[3] & 0x03) << 11) | ((adts_header[4] & 0xFF) << 3) | ((adts_header[5] & 0xE0) >> 5)

    def get_frame(self, file):
        adts_header = file.read(7)
        if len(adts_header) < 7:
            return None
        frame_length = self.get_acc_frame_length(adts_header)

        frame_data = file.read(frame_length-7)
        payload = bytearray([0x00, 0x10, (frame_length & 0x1FE0) >> 5, (frame_length & 0x1F) << 3])
        payload += frame_data
        return payload


aac = AAC()
