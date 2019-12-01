HEADER_SIZE = 12
H264_PAYLOAD_TYPE = 96
ACC_PAYLOAD_TYPE = 97
TS_PAYLOAD_TYPE = 33
RTP_MAX_PKT_SIZE = 1400


class RTP_Header:


    def __init__(self):
        self.header = None
        self.payload = None

    def set_header(self, version, padding, extension, cc, seqnum, marker, pt, ssrc):
        # timestamp = int(time())
        timestamp = 0
        header = bytearray(HEADER_SIZE)

        # Fill the header bytearray with RTP header fields
        header[0] = (version << 6) | (padding << 5) | (extension << 4) | cc
        header[1] = (marker << 7) | pt
        header[2] = (seqnum >> 8) & 255  # upper bits
        header[3] = seqnum & 255
        header[4] = timestamp >> 24 & 255
        header[5] = timestamp >> 16 & 255
        header[6] = timestamp >> 8 & 255
        header[7] = timestamp & 255
        header[8] = ssrc >> 24 & 255
        header[9] = ssrc >> 16 & 255
        header[10] = ssrc >> 8 & 255
        header[11] = ssrc & 255

        self.header = header

    def increase_seq(self):
        seq = self.header[2] << 8 | self.header[3]
        seq += 1
        self.header[2] = (seq >> 8) & 255
        self.header[3] = seq & 255

    def get_seq(self):
        return self.header[2] << 8 | self.header[3]

    def increase_timestamp(self, increase):
        timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        timestamp += increase
        self.header[4] = timestamp >> 24 & 255
        self.header[5] = timestamp >> 16 & 255
        self.header[6] = timestamp >> 8 & 255
        self.header[7] = timestamp & 255

    def get_timestamp(self):
        return self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]

    def set_timestamp(self, timestamp):
        self.header[4] = timestamp >> 24 & 255
        self.header[5] = timestamp >> 16 & 255
        self.header[6] = timestamp >> 8 & 255
        self.header[7] = timestamp & 255

    def encode(self):
        pass

    def decode(self):
        pass

    def get_payload_type(self, file_ext):
        if file_ext == '.h264':
            return H264_PAYLOAD_TYPE
        elif file_ext == '.aac':
            return ACC_PAYLOAD_TYPE
        elif file_ext == '.ts':
            return TS_PAYLOAD_TYPE
