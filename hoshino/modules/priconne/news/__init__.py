from hoshino import Service
from .spider import *

svbl = Service('pcr-news-bili', bundle='pcr订阅', help_='B服官网新闻')

async def news_poller(spider:BaseSpider, sv:Service, TAG):
    if not spider.item_cache:
        await spider.get_update()
        sv.logger.info(f'{TAG}新闻缓存为空，已加载至最新')
        return
    news = await spider.get_update()
    if not news:
        sv.logger.info(f'未检索到{TAG}新闻更新')
        return
    sv.logger.info(f'检索到{len(news)}条{TAG}新闻更新！')
    await sv.broadcast(spider.format_items(news), TAG, interval_time=0.5)
    

@svbl.scheduled_job('cron', minute='*/5', jitter=20)
async def bili_news_poller():
    await news_poller(BiliSpider, svbl, 'B服官网')

async def send_news(bot, ev, spider:BaseSpider, max_num=5):
    if not spider.item_cache:
        await spider.get_update()
    news = spider.item_cache
    news = news[:min(max_num, len(news))]
    await bot.send(ev, spider.format_items(news), at_sender=True)

@svbl.on_fullmatch(('B服新闻', 'b服新闻', 'B服日程', 'b服日程'))
async def send_bili_news(bot, ev):
    await send_news(bot, ev, BiliSpider)
