import random
import re
from os import path
from urllib.parse import urlparse


def random_generator(n):
    random_list = random.sample(range(1, n**2), n)
    i = 0
    while True:
        yield random_list[i]
        i = (i+1) % n


def get_media_path(root, url_path):
    abs_path = path.join(root, url_path[1:])
    tmp, file_ext = path.splitext(abs_path)
    filepath = path.dirname(tmp)
    filename = path.basename(tmp)
    return filepath, filename, file_ext


def match_rtp_rtcp_port(string):
    res = re.search(r'client_port=\s*(?P<rtp_port>\d+)-(?P<rtcp_port>\d+)', string)
    if not res:
        return None, None
    res_dict = res.groupdict()
    rtp_port = int(res_dict.get('rtp_port'))
    rtcp_port = int(res_dict.get('rtcp_port'))
    return rtp_port, rtcp_port


def parse_path(request, root=''):
    url = request.split('\n')[0].split(' ')[1]
    url_path = urlparse(url).path
    path_tup = get_media_path(root, url_path)
    return path_tup


def parse_ext(request):
    url = request.split('\n')[0].split(' ')[1]
    return path.splitext(url)
