from hoshino import Service, R
from hoshino.typing import *
from hoshino import Service, priv, util
from hoshino.util import DailyNumberLimiter, pic2b64, concat_pic, silence
import sqlite3, os, random, asyncio
from nonebot import MessageSegment
from hoshino import Service
from hoshino.typing import CQEvent
import random
import imageio
import numpy as np
import heapq
from hoshino.modules.priconne import chara
import time
import math
import nonebot
from . import runchara
import copy
import os
from  PIL  import   Image,ImageFont,ImageDraw
from io import BytesIO
import base64

sv = Service('pcr-run', enable_on_default=True)

ROAD = '='
ROADLENGTH = 15
TOTAL_NUMBER = 11
NUMBER = 5
ONE_TURN_TIME = 3
SUPPORT_TIME = 30
SLEEP_TIME = 10 #消息撤回间隔
DB_PATH = os.path.expanduser('~/.hoshino/pcr_running_counter.db')
FILE_PATH = os.path.dirname(__file__)
class RunningJudger:
    def __init__(self):
        self.on = {}
        self.support = {}
    def set_support(self,gid):
        self.support[gid] = {}
    def get_support(self,gid):
        return self.support[gid] if self.support.get(gid) is not None else 0
    def add_support(self,gid,uid,id,score):
        self.support[gid][uid]=[id,score]
    def get_support_id(self,gid,uid):
        if self.support[gid].get(uid) is not None:
            return self.support[gid][uid][0]
        else :
            return 0
    def get_support_score(self,gid,uid):
        if self.support[gid].get(uid) is not None:
            return self.support[gid][uid][1]
        else :
            return 0
    def get_on_off_status(self, gid):
        return self.on[gid] if self.on.get(gid) is not None else False
    def turn_on(self, gid):
        self.on[gid] = True
    def turn_off(self, gid):
        self.on[gid] = False
        
running_judger = RunningJudger()

class ScoreCounter:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._create_table()
        
    def _create_table(self):
        try:
            self._connect().execute('''CREATE TABLE IF NOT EXISTS SCORECOUNTER
                          (GID             INT    NOT NULL,
                           UID             INT    NOT NULL,
                           SCORE           INT    NOT NULL,
                           PRIMARY KEY(GID, UID));''')
        except:
            raise Exception('创建表发生错误')
            
    def _connect(self):
        return sqlite3.connect(DB_PATH)
    
    def _get_score(self, gid, uid):
        try:
            r = self._connect().execute("SELECT SCORE FROM SCORECOUNTER WHERE GID=? AND UID=?",(gid,uid)).fetchone()        
            return 0 if r is None else r[0]
        except:
            raise Exception('查找表发生错误')
    
    def _reduce_score(self, gid, uid ,score):
        try:
            current_score = self._get_score(gid, uid)
            if current_score >= score:
                conn = self._connect()
                conn.execute("INSERT OR REPLACE INTO SCORECOUNTER (GID,UID,SCORE) \
                                VALUES (?,?,?)", (gid, uid, current_score-score))
                conn.commit()     
            else:
                conn = self._connect()
                conn.execute("INSERT OR REPLACE INTO SCORECOUNTER (GID,UID,SCORE) \
                                VALUES (?,?,?)", (gid, uid, 0))
                conn.commit()     
        except:
            raise Exception('更新表发生错误')  
            
    #判断金币是否足够下注
    def _judge_score(self, gid, uid ,score):
        try:
            current_score = self._get_score(gid, uid)
            if current_score >= score:
                return 1
            else:
                return 0
        except Exception as e:
            raise Exception(str(e))
    
#这个类用于记录一些与技能有关的变量，如栞的ub计数，可可萝的主人
class NumRecord:
    def __init__(self):
        self.kan_num = {}
        self.kokoro_num = {}
        
    def init_num(self,gid):
        self.kan_num[gid] = 1
        self.kokoro_num[gid] = 0
    def get_kan_num(self,gid): 
        return self.kan_num[gid] 
    def add_kan_num(self,gid,num):
        self.kan_num[gid]+=num
    def set_kokoro_num(self,gid,kokoro_id):
        l1 = range(1,NUMBER+1)
        list(l1).remove(kokoro_id)
        self.kokoro_num[gid] = random.choice(l1)
        return self.kokoro_num[gid]
    def get_kokoro_num(self,gid):
        return self.kokoro_num[gid]
        
numrecord = NumRecord()

#撤回消息
async def del_msg_run(bot, ev, msg_id, sleeptime):
    #bot = nonebot.get_bot()
    #time.sleep(sleeptime)
    #print(self_id)
    self_id=ev.self_id
    await bot.send(ev,f"{self_id}开始撤回消息{msg_id}")
    bot = nonebot.get_bot()
    await bot.delete_msg(self_id,msg_id)
    #print('撤回一条消息')

#将角色以角色编号的形式分配到赛道上，返回一个赛道的列表。
def chara_select():
    l = range(1,TOTAL_NUMBER+1)
    select_list = random.sample(l,5)
    return select_list
#取得指定角色编号的赛道号,输入分配好的赛道和指定角色编号
def get_chara_id(list,id):
    raceid= list.index(id)+1
    return raceid
       
#输入赛道列表和自己的赛道，选出自己外最快的赛道
def select_fast(position,id):
    list1 = copy.deepcopy(position) 
    list1[id-1] = 999
    fast = list1.index(min(list1))
    return fast+1

#输入赛道列表和自己的赛道，选出自己外最慢的赛道。 
def select_last(position,id):
    list1 = copy.deepcopy(position)
    list1[id-1] = 0
    last = list1.index(max(list1))
    return last+1    
    
#输入赛道列表，自己的赛道和数字n，选出自己外第n快的赛道。     
def select_number(position,id,n):
    lis = copy.deepcopy(position)
    lis[id-1] = 999
    max_NUMBER = heapq.nsmallest(n, lis) 
    max_index = []
    for t in max_NUMBER:
        index = lis.index(t)
        max_index.append(index)
        lis[index] = 0
    nfast = max_index[n-1]
    return nfast+1

#输入自己的赛道号，选出自己外的随机1个赛道，返回一个赛道编号   
def select_random(id):
    l1 = range(1,NUMBER+1)
    list(l1).remove(id)
    select_id = random.choice(l1)
    return select_id

#输入自己的赛道号和数字n，选出自己外的随机n个赛道，返回一个赛道号的列表   
def nselect_random(id,n):
    l1 = range(1,NUMBER+1)
    list(l1).remove(id)
    select_list = random.sample(l1,n)
    return select_list
    
#选择除自己外的全部对象，返回赛道号的列表
def select_all(id):
    l1 = list(range(1,NUMBER+1))
    l1.remove(id)
    return l1

def search_kokoro(charalist):
    if 10 in charalist:
        return charalist.index(10)+1
    
    else:
        return None

def create_gif(image_list, gid, duration=0.35):
    frames = []
    GIF_PATH = os.path.join(FILE_PATH,'gifs')
    for image_name in image_list:
        image_name = os.path.join(GIF_PATH,image_name)
        #print(image_name)
        frames.append(imageio.imread(image_name))
    gif_name = f'{gid}_run.gif'
    GIFS = os.path.join(GIF_PATH,f'{gid}_run.gif')
    imageio.mimsave(GIFS, frames, 'GIF', duration=duration)
    gif_send = MessageSegment.image(f'file:///{os.path.abspath(GIFS)}')
    return gif_send

def save_base64_img(sss,name):
    GIF_PATH = os.path.join(FILE_PATH,'gifs')
    image_name = os.path.join(GIF_PATH,name)
    #print(sss)
    imagedata = base64.b64decode(sss)
    #print(imagedata)
    file = open(image_name,"wb")
    file.write(imagedata)
    file.close()

#对单一对象的基本技能：前进，后退，沉默，暂停，必放ub
def forward(id,step,position):
    fid = int(id)
    position[fid-1] = position[fid-1] - step
    position[fid-1] = max (1,position[fid-1])
    return
    
def backward(id,step,position):

    position[id-1] = position[id-1] + step
    position[id-1] = min (ROADLENGTH,position[id-1])
    return  

def give_silence(id,num,silence):
    silence[id-1] += num
    return   

def give_pause(id,num,pause):
    pause[id-1] += num
    return

def give_ub(id,num,ub):
    ub[id-1] += num
    return

def change_position(id,rid,position):
    position[id-1],position[rid-1] = position[rid-1],position[id-1]
    return 

#用于技能参数增加
def add(a,b):
    return a+b
    
#对列表多对象的基本技能
def n_forward(list,step,position):
    for id in list:
        position[id-1] = position[id-1] - step
        position[id-1] = max (1,position[id-1])
    return
    
def n_backward(list,step,position):
    for id in list:
        position[id-1] = position[id-1] + step
        position[id-1] = min (ROADLENGTH,position[id-1])
    return  

def n_give_silence(list,num,silence):
    for id in list:
        silence[id-1] += num
    return   

def n_give_pause(list,num,pause):
    for id in list:
        pause[id-1] += num
    return

def n_give_ub(list,num,ub):
    for id in list:
        ub[id-1] += num
    return

#概率触发的基本技能
def prob_forward(prob,id,step,position):
    r=random.random()
    if r < prob:
        forward(id,step,position)
        return 1
    else :
        return 0
      
def prob_backward(prob,id,step,position):
    r=random.random()
    if r < prob:
        backward(id,step,position)
        return 1
    else :
        return 0        
        
def prob_give_pause(prob,id,num,pause):
    r=random.random()
    if r < prob:
        give_pause(id,num,pause)
        return 1
    else :
        return 0

def prob_give_silence(prob,id,num,silence):
    r=random.random()
    if r < prob:
        give_silence(id,num,silence)
        return 1
    else :
        return 0

#根据概率触发技能的返回，判断是否增加文本，成功返回成功文本，失败返回失败文本
def prob_text(is_prob,text1,text2):
    if is_prob == 1:
        addtion_text = text1
    else:
        addtion_text = text2
    return addtion_text

#按概率表选择一个技能编号
def skill_select(cid):
    c = runchara.Run_chara(str(cid))
    skillnum_ = ['0','1', '2', '3', '4']
    #概率列表,读json里的概率，被注释掉的为老版本固定概率
    r_ = c.getskill_prob_list()
   #r_ = [0.7, 0.1, 0.1, 0.08, 0.02]
    sum_ = 0
    ran = random.random()
    for num, r in zip(skillnum_, r_):
        sum_ += r
        if ran < sum_ :break
    return int (num)

#加载指定角色的指定技能，返回角色名，技能文本和技能效果
def skill_load(cid,sid):
    c = runchara.Run_chara(str(cid))
    name = c.getname()
    if sid == 0:
        return name,"none","null"
    else :
        skill_text = c.getskill(sid)["skill_text"]
        skill_effect = c.getskill(sid)["skill_effect"]
        return name,skill_text,skill_effect
    
#指定赛道的角色释放技能，输入分配好的赛道和赛道编号
def skill_unit(Race_list,rid,position,silence,pause,ub,gid):
    #检查是否被沉默
    cid = Race_list[rid-1]
    sid = skill_select(cid)
    if ub[rid-1]!=0:
        sid = 3
        ub[rid-1]-= 1
        
    skill = skill_load(cid,sid)
    skillmsg = skill[0]
    skillmsg += ":"
    if silence[rid-1] == 1:
        skillmsg += "本回合被沉默"
        silence[rid-1] -= 1
        return skillmsg
    skillmsg += skill[1]
    list = Race_list
    id = rid
    position = position
    silence = silence
    pause = pause
    ub = ub
    kan_num = numrecord.get_kan_num(gid)
    kokoro_num = numrecord.get_kokoro_num(gid)
    if skill[2]== "null":
        return skillmsg
    loc = locals()    
    addtion_text = ''
    exec(skill[2])
    if 'text'in loc.keys():
        addtion_text = loc['text']
    if 'kan_num1'in loc.keys():
        numrecord.add_kan_num(gid,loc['kan_num1'])         
    skillmsg += addtion_text
    
    return skillmsg
    
#每个赛道的角色轮流释放技能    
def skill_race(Race_list,position,silence,pause,ub,gid):
    skillmsg = ""
    for rid in range(1,6):
        skillmsg += skill_unit(Race_list,rid,position,silence,pause,ub,gid)
        if rid !=5:
            skillmsg += "\n"
    return skillmsg    
        
#初始状态相关函数    
def position_init(position):
    for i in range (0,NUMBER):
        position[i] = ROADLENGTH
    return
    
def silence_init(silence):
    for i in range (0,NUMBER):
        silence[i] = 0
    return
    
def pause_init(pause):
    for i in range (0,NUMBER):
        pause[i] = 0
    return    
    
def ub_init(ub):
    for i in range (0,NUMBER):
        ub[i] = 0
    return       

#赛道初始化
def race_init(position,silence,pause,ub):
    position_init(position)
    silence_init(silence)
    pause_init(pause)
    ub_init(ub)
    return
    
#一个角色跑步 检查是否暂停
def one_unit_run(id,pause,position,Race_list):
    if  pause[id-1]  == 0:
        cid = Race_list[id-1]
        c = runchara.Run_chara(str(cid))
        speedlist = c.getspeed()
        step = random.choice(speedlist)
        forward(id,step,position)
        return
    else:
        pause[id-1]-=1
        return
           
#一轮跑步，每个角色跑一次    
def one_turn_run(pause,position,Race_list):
    for id in range(1,6):
        one_unit_run(id,pause,position,Race_list)

#打印当前跑步状态
def print_race(Race_list,position,msg,img_name):
    im = Image.new("RGB", (800, 615), (255, 255, 255))
    
    base_img = os.path.join(FILE_PATH, "run_bg.jpg")
    dtimg = Image.open(base_img)
    dtbox = (0, 0)
    im.paste(dtimg, dtbox)
    
    dr = ImageDraw.Draw(im)
    ICON_PATH = os.path.join(FILE_PATH,'icon')
    FONTS_PATH = os.path.join(FILE_PATH,'fonts')
    FONTS = os.path.join(FONTS_PATH,'msyh.ttf')
    font = ImageFont.truetype(FONTS, 16)
    racemsg = ""
    for id in range(1,6):
        cid = Race_list[id-1]
        c = runchara.Run_chara(str(cid))
        icon = c.geticon()
        image = c.getimg()
        for n in range (1,ROADLENGTH+1):
            if n != position[id-1]:
                racemsg = racemsg + ROAD
            else:
                image_path = os.path.join(ICON_PATH,image)
                img = Image.open(image_path).convert('RGBA')
                size = img.size
                sf_weight = math.ceil(size[0]/(size[1]/65))
                img = img.resize((sf_weight, 65))
                top_height = 160+(id-1)*60-10
                left = 25 + (n-1)*50
                box = (left, top_height)
                im.paste(img, box, mask=img.split()[3])
                racemsg = racemsg + str(icon)
        if id != 5:
            racemsg = racemsg + "\n"   
    dr.text((110, 470), msg, font=font, fill="#06a6d8")
    bio  = BytesIO()
    im.save(bio, format='PNG')
    
    base64_img = base64.b64encode(bio.getvalue()).decode()
    save_base64_img(base64_img,img_name)
    return racemsg
    
#检查比赛结束用，要考虑到同时冲线
def check_game(position,winner):
    xuhao = 1
    is_win = 0
    xuhao=xuhao+len(winner)
    for id in range(1,6):
        mc_flag=0
        mingcixx=[]
        if position[id-1] == 1:
            for win in winner:
                if id==win[1]:
                    mc_flag=1
            if mc_flag==0:
                mingcixx=[xuhao,id]
                print(mingcixx)
                winner.append(mingcixx)
                if len(winner)>=3:
                    is_win = 1
    return is_win,winner  

def introduce_race(Race_list):
    msg = ''
    for id in range(1,6):
        msg += f'{id}号：'
        cid = Race_list[id-1]
        c = runchara.Run_chara(str(cid))
        icon = c.geticon()
        name = c.getname()
        msg += f'{name}，图标为{icon}'
        msg += "\n" 
    msg += f"所有人请在{SUPPORT_TIME}秒内选择支持的选手。格式如下：\n1/2/3/4/5号xx金币\n如果金币为0，可以发送：\n领赛跑金币"    
    return msg    
        
bot_del = nonebot.get_bot()
@sv.on_prefix(('开始赛跑', '赛跑开始'))
async def Racetest(bot, ev: CQEvent):
    #if not priv.check_priv(ev, priv.ADMIN):
    #    await bot.finish(ev, '只有群管理才能开启赛跑', at_sender=True)
    if running_judger.get_on_off_status(ev.group_id):
            await bot.send(ev, "此轮赛跑还没结束，请勿重复使用指令。")
            return
    runimg_list = []
    running_judger.turn_on(ev.group_id)
    gid = ev.group_id
    #用于记录各赛道上角色位置，第i号角色记录在position[i-1]上
    position = [ROADLENGTH for x in range(0,NUMBER)]
    #同理，记录沉默，暂停，以及必放ub标记情况
    silence = [0 for x in range(0,NUMBER)]
    pause = [0 for x in range(0,NUMBER)]
    ub = [0 for x in range(0,NUMBER)]
    numrecord.init_num(gid)
    Race_list = chara_select()
    msg = '兰德索尔赛跑即将开始！\n下面为您介绍参赛选手：'
    ret = await bot.send(ev, msg)
    #await asyncio.sleep(ONE_TURN_TIME)
    #await bot_del.delete_msg(self_id=ev.self_id,message_id=ret['message_id'])
    #del_msg_run(bot, ev, ret['message_id'], SLEEP_TIME)
    #msg = ret['message_id']
    #ret = await bot.send(ev, msg)
    await asyncio.sleep(ONE_TURN_TIME)
    #介绍选手，开始支持环节
    msg = introduce_race(Race_list)
    await bot.send(ev, msg)
    await asyncio.sleep(SUPPORT_TIME)
    running_judger.turn_off(ev.group_id)
    #支持环节结束
    msg = '支持环节结束，下面赛跑正式开始。'
    await bot.send(ev, msg)    
    await asyncio.sleep(ONE_TURN_TIME) 
    kokoro_id = search_kokoro(Race_list)
    if kokoro_id is not None:
        kokoro_num = numrecord.set_kokoro_num(gid,kokoro_id)
        msg=f'本局存在可可萝，可可萝的主人为{kokoro_num}号选手'
        await bot.send(ev, msg)    
        await asyncio.sleep(ONE_TURN_TIME)

    
    race_init(position,silence,pause,ub)
    msg = '运动员们已经就绪！\n'

    msg = print_race(Race_list,position,msg,f'{gid}_0_1.jpg')

    runimg_list.append(f'{gid}_0_1.jpg')

    gameend = 0
    i = 1
    winner = []
    del_msg1=''
    del_msg2=''
    del_msg3=''
    
    while gameend == 0:
        
        msg = f'第{i}轮跑步:\n'
        
        one_turn_run(pause,position,Race_list)
        msg = print_race(Race_list,position,msg,f'{gid}_{i}_1.jpg')
        
        
        runimg_list.append(f'{gid}_{i}_1.jpg')
        
        check = check_game(position,winner)
        if check[0]!=0:
            break
            

        skillmsg = "技能发动阶段:\n"
        skillmsg += skill_race(Race_list,position,silence,pause,ub,gid)
        
        
        msg = print_race(Race_list,position,skillmsg,f'{gid}_{i}_2.jpg')
        
        
        runimg_list.append(f'{gid}_{i}_2.jpg')
        
        i+=1
        check = check_game(position,check[1])
        gameend = check[0]
    
    gif_name = create_gif(runimg_list, gid, 1.5)
    await bot.send(ev, gif_name)
    winner = check[1]
    winshuchu=''
    winmsg1=''
    winmsg2=''
    winmsg3=''
    for win in winner:
        if win[0]==1:
            winmsg1 += str(win[1])+'号选手\n'
        if win[0]==2:
            winmsg2 += str(win[1])+'号选手\n'
        if win[0]==3:
            winmsg3 += str(win[1])+'号选手\n'
    if winmsg1:
        winshuchu += "第一名为:\n"+winmsg1
    if winmsg2:
        winshuchu += "第二名为:\n"+winmsg2
    if winmsg3:
        winshuchu += "第三名为:\n"+winmsg3
    msg = f'胜利者:\n{winshuchu}'
    score_counter = ScoreCounter()
    await bot.send(ev, msg)
    gid = ev.group_id
    support = running_judger.get_support(gid)
    winuid = []
    shengwangmsg = ''
    supportmsg = '金币结算:\n'
    bd_msg=''
    if support!=0:
        for uid in support:
            support_id = support[uid][0]
            support_score = support[uid][1]
            jl_mingci=0
            for win in winner:
                if win[1]==support_id:
                    jl_mingci=win[0]
                    break
            if jl_mingci==1:
                winuid.append(uid)
                winscore = support_score*1.5
                #addscore = winscore+support_score
                score_counter._add_score(gid, uid ,winscore)
                supportmsg += f'[CQ:at,qq={uid}]+{winscore}金币\n'
            elif jl_mingci==2:
                winuid.append(uid)
                winscore = support_score*1
                #addscore = winscore+support_score
                score_counter._add_score(gid, uid ,winscore)
                supportmsg += f'[CQ:at,qq={uid}]+{winscore}金币\n'
            elif jl_mingci==3:
                winuid.append(uid)
                winscore = support_score*0.5
                #addscore = winscore+support_score
                score_counter._add_score(gid, uid ,winscore)
                supportmsg += f'[CQ:at,qq={uid}]+{winscore}金币\n'
            else:
                score_counter._reduce_score(gid, uid ,support_score)
                supportmsg += f'[CQ:at,qq={uid}]-{support_score}金币\n'
    await asyncio.sleep(2)
    await bot.send(ev, supportmsg)
    running_judger.set_support(ev.group_id) 
    running_judger.turn_off(ev.group_id)
 
@sv.on_rex(r'^(\d+)号(\d+)(金币|分)$') 
async def on_input_score(bot, ev: CQEvent):
    try:
        if running_judger.get_on_off_status(ev.group_id):
            gid = ev.group_id
            uid = ev.user_id
            
            match = ev['match']
            select_id = int(match.group(1))
            input_score = int(match.group(2))
            #print(select_id,input_score)
            score_counter = ScoreCounter()
            #若下注该群下注字典不存在则创建
            if running_judger.get_support(gid) == 0:
                running_judger.set_support(gid)
            support = running_judger.get_support(gid)
            #检查是否重复下注
            if uid in support:
                msg = '您已经支持过了。'
                await bot.send(ev, msg, at_sender=True)
                return
            #检查金币是否足够下注
            if score_counter._judge_score(gid, uid ,input_score) == 0:
                msg = '您的金币不足。'
                await bot.send(ev, msg, at_sender=True)
                return
            else :
                running_judger.add_support(gid,uid,select_id,input_score)
                #score_counter._reduce_score(gid, uid ,input_score)
                msg = f'支持{select_id}号成功。'
                await bot.send(ev, msg, at_sender=True)                
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))            
            
@sv.on_prefix('领赛跑金币')
async def add_score(bot, ev: CQEvent):
    try:
        score_counter = ScoreCounter()
        gid = ev.group_id
        uid = ev.user_id
        
        current_score = score_counter._get_score(gid, uid)
        if current_score == 0:
            score_counter._add_score(gid, uid ,50)
            msg = '您已领取50金币'
            await bot.send(ev, msg, at_sender=True)
            return
        else:     
            msg = '金币为0才能领取哦。'
            await bot.send(ev, msg, at_sender=True)
            return
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))         
@sv.on_prefix('查赛跑金币')
async def get_score(bot, ev: CQEvent):
    try:
        score_counter = ScoreCounter()
        gid = ev.group_id
        uid = ev.user_id
        
        current_score = score_counter._get_score(gid, uid)
        msg = f'您的金币为{current_score}'
        await bot.send(ev, msg, at_sender=True)
        return
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e)) 
        
async def get_user_card_dict(bot, group_id):
    mlist = await bot.get_group_member_list(group_id=group_id)
    d = {}
    for m in mlist:
        d[m['user_id']] = m['card'] if m['card']!='' else m['nickname']
    return d        
@sv.on_fullmatch(('赛跑排行榜', '赛跑群排行'))
async def Race_ranking(bot, ev: CQEvent):
    try:
        user_card_dict = await get_user_card_dict(bot, ev.group_id)
        score_dict = {}
        score_counter = ScoreCounter()
        gid = ev.group_id
        for uid in user_card_dict.keys():
            if uid != ev.self_id:
                score_dict[user_card_dict[uid]] = score_counter._get_score(gid, uid)
        group_ranking = sorted(score_dict.items(), key = lambda x:x[1], reverse = True)
        msg = '此群赛跑金币排行为:\n'
        for i in range(min(len(group_ranking), 10)):
            if group_ranking[i][1] != 0:
                msg += f'第{i+1}名: {group_ranking[i][0]}, 金币: {group_ranking[i][1]}分\n'
        await bot.send(ev, msg.strip())
    except Exception as e:
        await bot.send(ev, '错误:\n' + str(e))        
    

    
        
        
        
        
   
    
    
    
    
    
    
    
    
    





    
