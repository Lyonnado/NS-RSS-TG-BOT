import json
import time
import requests
import pytz
from datetime import datetime, timedelta
import feedparser
from email.utils import parsedate_to_datetime

# 读取配置文件并返回配置字典
def read_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)

# 更新配置文件中的 "last_fetched_time" 字段
def write_last_fetched_time(config, last_fetched_time):
    with open("config.json", "r", encoding="utf-8") as f:
        full_config = json.load(f)
    full_config["last_fetched_time"] = last_fetched_time
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(full_config, f, indent=4, ensure_ascii=False)

# 获取上次抓取的时间
def get_last_fetched_time(config):
    last_fetched_time = config.get("last_fetched_time")
    if not last_fetched_time:
        # 如果没有时间，则默认为当前时间减去 10 分钟
        return (datetime.now(pytz.utc) - timedelta(minutes=10)).isoformat()
    return last_fetched_time

# 更新配置中的最后抓取时间为最新帖子的时间
def update_last_fetched_time(config, latest_post_time):
    write_last_fetched_time(config, latest_post_time)

# 获取RSS源的数据
def fetch_rss_feed():
    url = "https://rss.nodeseek.com"
    return feedparser.parse(url)

# 筛选出新发布的文章，判断是否在上次抓取时间之后发布
def filter_new_posts(feed, last_fetched_time):
    last_time = datetime.fromisoformat(last_fetched_time)
    new_posts = []
    for entry in feed.entries:
        try:
            # 使用更健壮的日期解析方法
            post_time = parsedate_to_datetime(entry.published)
            
            # 确保时区信息正确（转换为UTC）
            if post_time.tzinfo is None:
                post_time = post_time.replace(tzinfo=pytz.utc)
            else:
                post_time = post_time.astimezone(pytz.utc)
                
        except Exception as e:
            print(f"解析日期失败: {entry.published}, 错误: {e}")
            continue
        
        if post_time > last_time:
            new_posts.append({
                "title": entry.title,
                "link": entry.link,
                "published": post_time.isoformat()  # 保存发布时间用于更新记录
            })
    return new_posts

# 通过Telegram API发送消息
def send_telegram_message(api_token, user_id, message):
    url = f"https://api.telegram.org/bot{api_token}/sendMessage"
    payload = {
        "chat_id": user_id,
        "text": message
    }
    requests.post(url, json=payload)

# 根据用户配置处理符合条件的帖子，发送给符合关键词的用户
def process_users(config, posts):
    api_token = config["API_TOKEN"]
    for user_id, user_data in config["USERS"].items():
        # 获取用户的关键词设置和关键词开关
        keywords = user_data.get("keywords", [])
        keyword_switch = user_data.get("keyword_switch", "off")

        # 如果用户没有设置关键词，或者关键词开关为"off"，跳过该用户
        if not keywords or keyword_switch == "off":
            continue

        # 筛选出符合关键词的帖子（忽略大小写）
        user_posts = [
            post for post in posts
            if any(keyword.lower() in post["title"].lower() for keyword in keywords)
        ]

        # 给每个符合条件的用户发送消息
        for post in user_posts:
            # 发送标题和链接
            message = f"{post['title']}\n{post['link']}"
            send_telegram_message(api_token, user_id, message)

# 主函数，循环抓取新帖子并处理
def main():
    while True:
        # 读取配置
        config = read_config()
        
        # 获取最后抓取时间
        last_fetched_time = get_last_fetched_time(config)
        
        # 获取RSS源的内容
        rss_feed = fetch_rss_feed()

        # 筛选出新发布的帖子
        new_posts = filter_new_posts(rss_feed, last_fetched_time)

        # 如果有新帖子，处理用户的相关操作
        if new_posts:
            process_users(config, new_posts)
            # 找到最新帖子的发布时间
            latest_post_time = max(
                [datetime.fromisoformat(post["published"]) for post in new_posts],
                default=datetime.fromisoformat(last_fetched_time)
            ).isoformat()
            # 更新配置中的最后抓取时间为最新帖子的时间
            update_last_fetched_time(config, latest_post_time)
        else:
            # 没有新帖子时，尝试获取当前RSS源中最新帖子的时间
            if rss_feed.entries:
                try:
                    latest_entry = rss_feed.entries[0]
                    post_time = parsedate_to_datetime(latest_entry.published)
                    if post_time.tzinfo is None:
                        post_time = post_time.replace(tzinfo=pytz.utc)
                    else:
                        post_time = post_time.astimezone(pytz.utc)
                    update_last_fetched_time(config, post_time.isoformat())
                except Exception as e:
                    print(f"更新最新帖子时间失败: {e}")
            else:
                # 如果没有帖子，使用当前时间作为回退
                current_time = datetime.now(pytz.utc).isoformat()
                update_last_fetched_time(config, current_time)

        # 每隔60秒循环一次
        time.sleep(60)

# 脚本入口，启动主函数
if __name__ == "__main__":
    main()
