from string import Template
from bitstring import BitStream


NALU_TYPE_SPS = 7
NALU_TYPE_PPS = 8
NALU_TYPE_SLICE = 1
NALU_TYPE_IDR = 5

FRAME_I = 0
FRAME_P = 1
FRAME_B = 2

SEARCH_STEP = 50000


class H264:
    media_sdp = Template('m=video ${port} ${protocol} 96\r\na=rtpmap:96 H264/${clock}\r\na=framerate:${framerate}\r\na=control:track${control}\r\na=fmtp:96 packetization-mode=1\r\n')

    def __init__(self):
        pass

    def generate_media_sdp(self, *, port=0, protocol='RTP/AVP', clock=90000, framerate=24, control=0):
        return self.media_sdp.substitute(port=str(port), protocol=protocol,
                                         clock=str(clock), framerate=str(framerate),
                                         control=str(control))

    def check_sep_3(self, data):
        if data[0] == 0 and data[1] == 0 and data[2] == 1:
            return True
        return False

    def check_sep_4(self, data):
        if data[0] == 0 and data[1] == 0 and data[2] == 0 and data[3] == 1:
            return True
        return False

    def search_next_sep(self, data):
        length = len(data)
        if length - 3 < 3:
            return None

        for i in range(3, length - 3):
            if self.check_sep_3(data[i:]) or self.check_sep_4(data[i:]):
                return i

        if self.check_sep_3(data[-3:]):
            return length - 3

        return None

    def get_next_nalu(self, file, size):
        data = file.read(size)

        if self.check_sep_3(data):
            start_offset = 3
        elif self.check_sep_4(data):
            start_offset = 4
        else:
            print('Error: invalid input.')
            return None

        next_sep = self.search_next_sep(data)
        if not next_sep:
            return None

        file.seek(next_sep - len(data), 1)
        return data[start_offset:next_sep]

    def get_nalu_type(self, nalu):
        return nalu[0] & 0x1F

    def get_frame_type(self, slice_):
        bs = BitStream(slice_)
        first_mb_in_slice = bs.read('ue')
        slice_type = bs.read('ue')
        if slice_type == 0 or slice_type == 5:  # FRAME_P
            return FRAME_P
        elif slice_type == 1 or slice_type == 6:  # FRAME_B
            return FRAME_B
        elif slice_type == 2 or slice_type == 7:  # FRAME_I
            return FRAME_I
        elif slice_type == 3 or slice_type == 8:  # FRMAE_SP
            return FRAME_P
        elif slice_type == 4 or slice_type == 9:  # FRAME_SI
            return FRAME_I
        else:
            return None

    def divide_nalu(self, nalu, single_size):
        # implement FU-A
        nalu_header = nalu[0]
        length = len(nalu)
        complete_num = (length-1) // single_size
        remain_size = (length-1) % single_size
        pos = 1

        for i in range(complete_num):
            payload = bytearray([(nalu_header & 0x60) | 28, nalu_header & 0x1F])
            # payload += (nalu_type & 0x60) | 28
            # payload += nalu_type & 0x1F

            if i == 0:
                payload[1] |= 0x80  # start
            elif remain_size == 0 and i == complete_num-1:
                payload[1] |= 0x40  # end

            payload += nalu[pos:pos+single_size]
            pos += single_size
            yield bytes(payload)

        if remain_size > 0:
            payload = bytearray([(nalu_header & 0x60) | 28, nalu_header & 0x1F])
            # payload += (nalu_type & 0x60) | 28
            # payload += nalu_type & 0x1F
            payload[1] |= 0x40
            payload += nalu[pos:pos+remain_size]
            yield bytes(payload)

    def h264_rtp_timestamp_generator(self):
        timestamp = 0
        p_seq = 0
        fps = 25

        while True:
            yield timestamp
            p_seq += 1
            timestamp = 100*p_seq*fps

    def get_h264_rtp_payload(self, file, rtp_header, search_step=SEARCH_STEP):
        nalu_buffer = []
        nalu_seq = 0
        fps = 25
        ts_generator = self.h264_rtp_timestamp_generator()
        while True:
            nalu = self.get_next_nalu(file, SEARCH_STEP)
            if not nalu:
                break
            nalu_type = self.get_nalu_type(nalu)
            if nalu_type == NALU_TYPE_IDR:
                if nalu_buffer:
                    buffer_len = len(nalu_buffer)
                    ts_buffer = []
                    for i in range(buffer_len):
                        ts_buffer.append(next(ts_generator))
                    ts_buffer[0], ts_buffer[buffer_len - 1] = ts_buffer[buffer_len - 1], ts_buffer[0]
                    for i in range(buffer_len):
                        # 打时间戳
                        rtp_header.set_timestamp(ts_buffer[i])
                        print(rtp_header.get_timestamp())
                        yield nalu_buffer[i]
                    nalu_buffer.clear()
                # 打时间戳
                rtp_header.set_timestamp(next(ts_generator))
                print(rtp_header.get_timestamp())
                yield nalu
            elif nalu_type != NALU_TYPE_SLICE:
                print(rtp_header.get_timestamp())
                yield nalu
            else:
                frame_type = self.get_frame_type(nalu[1:])
                print('frame type: '+str(frame_type))
                if frame_type == FRAME_I:
                    if nalu_buffer:
                        buffer_len = len(nalu_buffer)
                        ts_buffer = []
                        for i in range(buffer_len):
                            ts_buffer.append(next(ts_generator))
                        ts_buffer[0], ts_buffer[buffer_len - 1] = ts_buffer[buffer_len - 1], ts_buffer[0]
                        for i in range(buffer_len):
                            # 打时间戳
                            rtp_header.set_timestamp(ts_buffer[i])
                            print(rtp_header.get_timestamp())
                            yield nalu_buffer[i]
                        nalu_buffer.clear()
                    # 打时间戳
                    rtp_header.set_timestamp(next(ts_generator))
                    print(rtp_header.get_timestamp())
                    yield nalu
                elif frame_type == FRAME_P:
                    if nalu_buffer:
                        buffer_len = len(nalu_buffer)
                        ts_buffer = []
                        for i in range(buffer_len):
                            ts_buffer.append(next(ts_generator))
                        ts_buffer[0], ts_buffer[buffer_len - 1] = ts_buffer[buffer_len - 1], ts_buffer[0]
                        for i in range(buffer_len):
                            # 打时间戳
                            rtp_header.set_timestamp(ts_buffer[i])
                            print(rtp_header.get_timestamp())
                            yield nalu_buffer[i]
                        nalu_buffer.clear()
                    nalu_buffer.append(nalu)
                elif frame_type == FRAME_B:
                    nalu_buffer.append(nalu)




h264 = H264()
