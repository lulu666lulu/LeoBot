import datetime
import string
import random
import hashlib
import time
from hoshino import aiorequests
from urllib.parse import urlencode
from ..util import get_config, get_next_day, Dict, init_db

config = get_config()
mhyVersion = "2.7.0"
config.use_cookie_index = 0
config.runtime = get_next_day()
cookies = config.setting.cookies


def __md5__(text):
    _md5 = hashlib.md5()
    _md5.update(text.encode())
    return _md5.hexdigest()


def __get_ds__():
    n = "14bmu1mz0yuljprsfgpvjh3ju2ni468r"
    i = str(int(time.time()))
    r = ''.join(random.sample(string.ascii_lowercase + string.digits, 6))
    c = __md5__("salt=" + n + "&t=" + i + "&r=" + r)
    return i + "," + r + "," + c


async def request_data(uid, api='index', character_ids=None):
    next_cookie = False
    now = datetime.datetime.now().timestamp()
    if now > config.runtime:
        config.runtime = get_next_day()
        config.use_cookie_index = 0
    server = 'cn_gf01'
    if uid[0] == "5":
        server = 'cn_qd01'
    cookie = cookies[config.use_cookie_index]

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'DS': __get_ds__(),
        'Origin': 'https://webstatic.mihoyo.com',
        'x-rpc-app_version': mhyVersion,
        'User-Agent': 'Mozilla/5.0 (Linux; Android 9; Unspecified Device) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/39.0.0.0 Mobile Safari/537.36 miHoYoBBS/2.2.0',
        'x-rpc-client_type': '5',
        'Referer': 'https://webstatic.mihoyo.com/app/community-game-records/index.html?v=6',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,en-US;q=0.8',
        'X-Requested-With': 'com.mihoyo.hyperion',
        'Cookie': cookie
    }

    params = {"server": server, "role_id": uid}

    json_data = None
    fn = aiorequests.get
    base_url = 'https://api-takumi.mihoyo.com/game_record/genshin/api/%s'
    url = base_url % api + '?'
    if api == 'index':
        url += urlencode(params)
    elif api == 'spiralAbyss':
        params['schedule_type'] = 1
        url += urlencode(params)
    elif api == 'character':
        fn = aiorequests.post
        params.update({"character_ids": character_ids})
        json_data = params

    res = await fn(url=url, headers=headers, json=json_data)
    json_data = await res.json(object_hook=Dict)
    if json_data.retcode == 10103:
        next_cookie = True
    if json_data.retcode == 10101 or next_cookie:
        config.use_cookie_index += 1
        if config.use_cookie_index == len(cookies):
            return 'all cookie(%s) has limited' % len(cookies)
        return await request_data(uid, api=api, character_ids=character_ids)

    return json_data


async def info(uid):
    return await request_data(uid)


async def spiralAbyss(uid):
    return await request_data(uid, 'spiralAbyss')


async def character(uid, character_ids):
    return await request_data(uid, 'character', character_ids)


class stats:
    def __init__(self, data, max_hide=False):
        self.data = data
        self.max_hide = max_hide

    @property
    def active_day(self) -> int:
        return self.data['active_day_number']

    @property
    def active_day_str(self) -> str:
        return '活跃天数: %s' % self.active_day

    @property
    def achievement(self) -> int:
        return self.data['achievement_number']

    @property
    def achievement_str(self) -> str:
        return '成就达成数: %s' % self.achievement

    @property
    def anemoculus(self) -> int:
        return self.data['anemoculus_number']

    @property
    def anemoculus_str(self) -> str:
        if self.max_hide and self.anemoculus == 66:
            return ''
        return '风神瞳: %s/66' % self.anemoculus

    @property
    def geoculus(self) -> int:
        return self.data['geoculus_number']

    @property
    def geoculus_str(self) -> str:
        if self.max_hide and self.geoculus == 131:
            return ''
        return '岩神瞳: %s/131' % self.geoculus

    @property
    def electroculus(self) -> int:
        return self.data['electroculus_number']

    @property
    def electroculus_str(self) -> str:
        if self.max_hide and self.electroculus == 95:
            return ''
        return '雷神瞳: %s/95' % self.electroculus

    @property
    def avatar(self) -> int:
        return self.data['avatar_number']

    @property
    def avatar_str(self) -> str:
        return '获得角色数: %s' % self.avatar

    @property
    def way_point(self) -> int:
        return self.data['way_point_number']

    @property
    def way_point_str(self) -> str:
        # if self.max_hide and self.way_point == 83:
        #     return ''
        return '解锁传送点: %s' % self.way_point

    @property
    def domain(self) -> int:
        return self.data['domain_number']

    @property
    def domain_str(self) -> str:
        return '解锁秘境: %s' % self.domain

    @property
    def spiral_abyss(self) -> str:
        return self.data['spiral_abyss']

    @property
    def spiral_abyss_str(self) -> str:
        return '' if self.spiral_abyss == '-' else '当期深境螺旋: %s' % self.spiral_abyss

    @property
    def common_chest(self) -> int:
        return self.data['common_chest_number']

    @property
    def common_chest_str(self) -> str:
        return '普通宝箱: %s' % self.common_chest

    @property
    def exquisite_chest(self) -> int:
        return self.data['exquisite_chest_number']

    @property
    def exquisite_chest_str(self) -> str:
        return '精致宝箱: %s' % self.exquisite_chest

    @property
    def luxurious_chest(self) -> int:
        return self.data['luxurious_chest_number']

    @property
    def luxurious_chest_str(self) -> str:
        return '华丽宝箱: %s' % self.luxurious_chest

    @property
    def precious_chest(self) -> int:
        return self.data['precious_chest_number']

    @property
    def precious_chest_str(self) -> str:
        return '珍贵宝箱: %s' % self.precious_chest

    @property
    def string(self):
        str_list = [
            self.active_day_str,
            self.achievement_str,
            self.anemoculus_str,
            self.geoculus_str,
            self.electroculus_str,
            self.avatar_str,
            self.way_point_str,
            self.domain_str,
            self.spiral_abyss_str,
            self.luxurious_chest_str,
            self.precious_chest_str,
            self.exquisite_chest_str,
            self.common_chest_str
        ]
        return '\n'.join(list(filter(None, str_list)))


db = init_db(config.cache_dir, 'uid.sqlite')


def get_uid_by_qid(qid):
    db_info = db.get(qid, {})
    if not db_info:
        return None
    return db_info['uid']


def save_uid_by_qid(qid, uid):
    db[qid] = {'uid': uid}
