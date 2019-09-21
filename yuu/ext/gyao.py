import json
import re

import m3u8

class GYAO:
    def __init__(self, url, session, verbose=False):
        self.session = session
        self.verbose = verbose

        self.url = url
        self.m3u8_url = None
        self.resolution = None
        self.policy_key = None
        self.account = None
        self.m3u8_url_list = None
        self.is_m3u8 = False

        self.resolution_data = {
            "1080p-0": ["~5000kb/s", "AAC 64kb/s 2ch"],
            "720p-0": ["2000kb/s", "AAC 64kb/s 2ch"],
            "480p-0": ["900kb/s", "AAC 64kb/s 2ch"],
            "360p-0": ["550kb/s", "AAC 64kb/s 2ch"],
            "240p-0": ["~200kb/s", "AAC 64kb/s 1ch"],
            "1080p-1": ["~5000kb/s", "AAC 128kb/s 2ch"],
            "720p-1": ["~2000kb/s", "AAC 128kb/s 2ch"],
            "480p-1": ["~900kb/s", "AAC 128kb/s 2ch"],
            "360p-1": ["~550kb/s", "AAC 128kb/s 2ch"],
            "240p-1": ["~200kb/s", "AAC 128kb/s 2ch"],
        }

        self.authorization_required = False
        # Use Chrome UA
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'})


    def __repr__(self):
        return '<yuu.GYAO: Verbose={}, Resolution={}, m3u8 URL={}>'.format(self.verbose, self.resolution, self.m3u8_url)


    def get_token(self):
        headers = {'X-User-Agent': 'Unknown Pc GYAO!/2.0.0 Web'}
        query = '?fields=title%2Cid%2CvideoId'
        v_id = re.findall(r'(?isx)http(?:|s)://gyao.yahoo.co.jp/(?:player|title[\w])/(?P<p1>[\w]*.*)', self.url)
        if not v_id:
            return None, 'Video URL are not valid'
       
        r_vid = self.session.get('https://gyao.yahoo.co.jp/dam/v1/videos/' + v_id[0].replace('/', ':').rstrip(':') + query, headers=headers)
        r_cov = self.session.get("http://players.brightcove.net/4235717419001/default_default/index.html?videoId=" + r_vid['videoId'])
        data_account = re.findall(r'<video-js\s+[^>]*\bdata-account\s*=.([\d]*).*>', r_cov.text, re.IGNORECASE | re.DOTALL | re.VERBOSE)

        r_pk = self.session.get("http://players.brightcove.net/{}/default_default/index.html".format(data_account[0]))

        pkey = re.findall(r'policyKey\s*:\s*(["\'])(?P<pk>.+?)\1', r_pk.text)[1]

        self.account = data_account[0]
        self.policy_key = pkey

        return 'SUCCESS', 'SUCCESS'


    def parse(self, resolution=None):
        """
        Function to parse gyao url
        """
        if self.verbose:
            print('[DEBUG] Requesting data to GYAO/Brightcove API')

        res_list = [
            '240p-0', '360p-0', '480p-0', '720p-0', '1080p-0',
            '240p-1', '360p-1', '480p-1', '720p-1', '1080p-1'
        ]

        if resolution not in res_list:
            return None, 'Resolution {} are non-existant. (Check it with `-R`)'

        v_id = re.findall(r'(?isx)http(?:|s)://gyao.yahoo.co.jp/(?:player|title[\w])/(?P<p1>[\w]*.*)', self.url)
        if not v_id:
            return None, 'Video URL are not valid'

        headers = {'X-User-Agent': 'Unknown Pc GYAO!/2.0.0 Web'}
        r_vid = self.session.get('https://gyao.yahoo.co.jp/dam/v1/videos/' + v_id[0].replace('/', ':').rstrip(':') + '?fields=title%2Cid%2CvideoId%2CshortTitle', headers=headers).json()
        title = r_vid['title']
        ep_title = r_vid['shortTitle']

        output_name = title.replace(ep_title, '').replace('\u3000', ' ') + ' - ' + ep_title

        headers_pk = {
            'Accept': 'application/json;pk=' + self.policy_key,
        }

        error_bc = {
            'CLIENT_GEO': 'Video are geo-locked to Japanese only.'
        }

        req_bc = self.session.get('https://edge.api.brightcove.com/playback/v1/accounts/{}/videos/{}'.format(self.account, r_vid['videoId']), headers=headers_pk)
        if req_bc.status_code == 403:
            error_reason = req_bc[0]['error_subcode']
            return None, error_bc[error_reason]
        
        if self.verbose and req_bc.status_code == 200:
            print('[DEBUG] Data requested')
            print('[DEBUG] Parsing json API')

        jsdata = req_bc.json()
        hls_list = jsdata['sources'][2]['src'] # Use EXT-V4 http version as the base
        hls_list2 = jsdata['sources'][0]['src'] # Use EXT-V3 http version as the one that will be sended over

        if self.verbose:
            print('[DEBUG] M3U8 Link: {}'.format(hls_list))
            print('[DEBUG] Title: {}'.format(output_name))

        self.m3u8_url_list = hls_list

        if self.verbose:
            print('[DEBUG] Requesting m3u8 list')
        r = self.session.get(hls_list)
        r2 = self.session.get(hls_list2)

        if self.verbose and r.status_code == 200:
            if r.status_code == 200:
                print('[DEBUG] m3u8 requested')
                print('[DEBUG] Parsing m3u8')

        if r.status_code == 403:
            return None, 'Video are geo-locked to Japanese only.'

        r_all = m3u8.loads(r.text)
        r2_all = m3u8.loads(r2.text)

        band_list_v4 = []
        for v4 in r_all.playlists:
            temp_ = []
            s_info = v4.stream_info
            audio_inf = s_info.audio.strip('audio')
            if resolution[-2:] == audio_inf:
                temp_.append(s_info.bandwidth)

        for v3 in r2_all.playlists:
            bw = v3.stream_info.bandwidth
            for bwv4 in band_list_v4:
                if bw == bwv4:
                    self.m3u8_url = v3.url
                    self.resolution = resolution

        if not self.m3u8_url:
            return None, 'Resolution {} are not exist in this video.'

        return output_name, None, 'Success Parsing GYAO URL.'


    def parse_m3u8(self):
        if self.verbose:
            print('[DEBUG] Requesting m3u8')
        r = self.session.get(self.m3u8_url)

        if self.verbose and r.status_code == 200:
            if r.status_code == 200:
                print('[DEBUG] m3u8 requested')
                print('[DEBUG] Parsing m3u8')

        if r.status_code == 403:
            return None, None, 'Video are geo-locked to Japanese only.'

        x = m3u8.loads(r.text)
        files = x.files

        if self.verbose:
            print('[DEBUG] Total files: {}'.format(len(files)))

        return files, None, 'Success'


    def resolutions(self):
        if self.verbose:
            print('[DEBUG] Requesting data to API')

        r_all = m3u8.loads(self.session.get(self.m3u8_url_list).text)

        ava_reso = []
        for r_p in r_all.playlists:
            temp_ = []
            res = r_p.stream_info.resolution
            aud_d = r_p.stream_info.audio.strip('audio')
            r_c = '{h}p{a}'.format(res[1], aud_d)
            res_name = '{w}x{h}'.format(res[0], res[1])

            temp_.append(r_c)
            temp_.append(res_name)

            ava_reso.append(temp_)

        return ava_reso

    
    def get_video_key(self):
        """
        Return None since there's not key decryption in GYAO
        """
        return None, 'No Encryption'
