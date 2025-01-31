import os
import json
import traceback

config = {
    "base": {
        "daily_max": 10,
        "freq_limit": 10,
        "whitelistmode": False,
        "blacklistmode": False,
        "ban_if_group_num_over": 200,
        "max_pic_once_send": 3
    },
    "default": {
        "withdraw" : 60,
        "lolicon": True,
        "lolicon_r18": False,
        "acggov": False    
    },
    "lolicon": {
        "mode": 2,
        "apikey": [],
        "r18": False,
        "use_thumb": True,
        "pixiv_direct": False,
        "pixiv_proxy": "https://i.pixiv.cat",
        "lolicon_proxy": ""
    }
}

# 源 0 关闭 1 lolicon 2 acggov 3 组合
# lolicon_r18 0 非18 1 纯r18 2 混合
group_config = {}

def get_config(key, sub_key):
    if key in config and sub_key in config[key]:
        return config[key][sub_key]
    return None

def load_config():
    path = os.path.join(os.path.dirname(__file__), 'config.json')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf8') as f:
            d = json.load(f)
            if 'base' in d:
                for k, v in d['base'].items():
                    config['base'][k] = v
            if 'acggov' in d:
                for k, v in d['acggov'].items():
                    config['acggov'][k] = v
            if 'lolicon' in d:
                for k, v in d['lolicon'].items():
                    config['lolicon'][k] = v
    except:
        traceback.print_exc()
load_config()

def load_group_config():
    path = os.path.join(os.path.dirname(__file__), 'group_config.json')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf8') as f:
            d = json.load(f)
            for k,v in d.items():
                group_config[k] = v
    except:
        traceback.print_exc()
load_group_config()

def get_group_config(group_id, key):
    group_id = str(group_id)
    if group_id not in group_config:
        group_config[group_id] = {}
        for k, v in config['default'].items():
            group_config[group_id][k] = v
    if key in group_config[group_id]:
        return group_config[group_id][key]
    else:
        return None

def set_group_config(group_id, key, value):
    group_id = str(group_id)
    if group_id not in group_config:
        group_config[group_id] = {}
        for k, v in config['default'].items():
            group_config[group_id][k] = v
    group_config[group_id][key] = value
    path = os.path.join(os.path.dirname(__file__), 'group_config.json')
    try:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(group_config, f, ensure_ascii=False, indent=2)
    except:
        traceback.print_exc()