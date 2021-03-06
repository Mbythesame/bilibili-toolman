import tqdm
import os
import argparse
import logging
import providers
from pathlib import Path

pbar = None
global_args = {
    'cookies': ('Bilibili 所用 Cookies ( 需要 SESSDATA 及 bili_jct ) e.g.cookies=SESSDATA=cb0..; bili_jct=6750... ',None),    
}
local_args = {
    'opts':('解析设置',None),
    'thread_id': ('分区 ID',17),
    'tags': ('标签','转载'),
    'desc_fmt':('描述格式 e.g. %(desc)s','%(desc)s'),
    'title_fmt':('标题格式 e.g. %(title)s','%(title)s'),
    'is_seperate_parts':('多个视频独立投稿（不分P）',None),
}

def setup_logging():
    import coloredlogs
    coloredlogs.DEFAULT_LOG_FORMAT = '[ %(asctime)s %(name)8s %(levelname)6s ] %(message)s'
    coloredlogs.install(0);logging.getLogger('urllib3').setLevel(100);logging.getLogger('PIL.Image').setLevel(100)

def prepare_temp():    
    if not os.path.isdir(temp_path):os.mkdir(temp_path)
    os.chdir(temp_path)    
    return True

def report_progress(current, max_val):
    global pbar
    if not pbar:
        pbar = tqdm.tqdm(desc='Uploading', total=max_val,
                         unit='B', unit_scale=True)
    pbar.update(current - pbar.n)
    if (max_val != pbar.total):
        pbar.clear()
        pbar.total = max_val


temp_path = 'temp'
cookie_path = os.path.join(str(Path.home()), '.bilibili-toolman')


def save_cookies(cookie):
    if not cookie:
        return
    with open(cookie_path, 'w+') as target:
        target.write(cookie)


def load_cookies():
    return open(cookie_path).read()


def _enumerate_providers():
    provider_dict = dict()
    for provider in dir(providers):
        if not 'provider_' in provider:
            continue
        provider_name = provider.replace('provider_', '')
        provider_dict[provider_name] = getattr(providers, provider)
    return provider_dict


provider_args = _enumerate_providers()


def _create_argparser():
    p = argparse.ArgumentParser(description='bilibili-toolman 哔哩哔哩工具人',formatter_class=argparse.RawTextHelpFormatter,epilog='''e.g.
    python bilibili-toolman.py --cookies "cookies=SESSDATA=cb0..; bili_jct=6750..." --youtube "https://www.youtube.com/watch?v=_3Mo7U0XSFo" --thread_id 17 --tags "majima,goro,majima goro" --opts "format=best"    
    ''')
    for arg, arg_ in global_args.items():
        arg_help,arg_default = arg_
        p.add_argument('--%s' % arg, type=str, help=arg_help,default=arg_default)
    # global args
    for arg, arg_ in local_args.items():        
        arg_help,arg_default = arg_
        arg_help='  (Per-file option) %s' % arg_help
        p.add_argument('--%s' % arg, type=str, help=arg_help,default=arg_default)
    # local args (per source)
    for provider_name, provider in provider_args.items():
        p.add_argument('--%s' % provider_name, metavar='%s-URL' %
                       provider_name.upper(), type=str, help='(Provider) %s\n   Options: %s'%(provider.__desc__,provider.__cfg_help__))
    return p

def limit_chars(string):
    import re
    return re.sub("[\U00010000-\U0010ffff]",'',string) # remove emojis

def limit_length(string,max):
    if len(string) > max:string = string[:max-3] + '...'
    return string

def prase_args(args: list):    
    if len(args) < 2:
        parser = _create_argparser()    
        parser.print_help()
        return
    args.pop(0)  # remove filename
    parser = _create_argparser()    
    global_args_dict = dict()
    for k, v in parser.parse_args(args).__dict__.items():
        if k in global_args:
            global_args_dict[k] = v
            if not '--%s' % k in args:continue
            args.pop(args.index('--%s' % k) + 1)
            args.pop(args.index('--%s' % k))
    '''pre-parse : fetch global args,then remove them'''
    local_args_group = []
    current_line = []
    current_provider = ''

    def add(): 
        args = parser.parse_args(current_line).__dict__       
        args['resource'] = args[current_provider]
        local_args_group.append((provider_args[current_provider],args))
    
    for arg in args:
        if arg[2:] in provider_args:
            # a new proivder
            current_provider = arg[2:]
            if current_line:
                # non-empty,add to local group
                add()
                current_line = []
        current_line.append(arg)
    if(current_line):
        add()
    return global_args_dict, local_args_group
