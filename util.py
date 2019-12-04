import random
import re
from os import path, system
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


def match_media_time(request):
    res = re.search(r'npt=(?P<cur_time>(\d*\.?\d*)|now)-(?P<end_time>\d*\.?\d*)', request)
    if not res:
        return None, None
    res_dict = res.groupdict()
    return res_dict['cur_time'], res_dict['end_time']


def make_stream_file(filepath):
    if not path.exists(filepath):
        filename = path.splitext(filepath)[0]
        system('ffmpeg -y -i %s.mp4 -vcodec copy -acodec copy -vbsf h264_mp4toannexb %s.ts' % (filename, filename))
