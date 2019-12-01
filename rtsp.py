from string import Template


class RTSP:
    OK = 1
    # session_sdp = Template('v=${sdp_version}\r\no=${user} ${session_id} ${session_version} ${network_type} ${ip_type} ${ip}\r\nt=0 0\r\na=control:*\r\n')
    session_sdp = Template('v=${sdp_version}\r\no=${user} ${session_id} ${session_version} ${network_type} ${ip_type} ${ip}\r\nt=0 0\r\n')
    def __init__(self, version='RTSP/1.0'):
        self.version = version
        self.ok_header = self.version+' 200 OK\r\n'

    def get_request_dict(self, request):
        request_dict = {}
        lines = request.split('\n')[1:]
        for line in lines:
            words = line.split(':')
            if len(words) != 2:
                continue
            words[0] = words[0].strip()
            words[1] = words[1].strip()
            request_dict[words[0]] = words[1]
        return request_dict

    def generate_response(self, response_dict, custom_header=None, type=OK, other=None):
        response = ''
        if custom_header:
            response += custom_header
        elif type == self.OK:
            response += self.ok_header
        for key, value in response_dict.items():
            line = str(key)+': '+str(value)+'\r\n'
            response += line
        response += '\r\n'
        if other:
            response += other
        return response

    def generate_session_sdp(self, *, sdp_version=0, user='-', session_id,
                             session_version=1, network_type='IN', ip_type='IP4',
                             ip):
        return self.session_sdp.substitute(sdp_version=str(sdp_version), user=user,
                                           session_id=str(session_id), session_version=str(session_version),
                                           network_type=network_type,
                                           ip_type=ip_type, ip=ip)


rtsp = RTSP()




