import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone  # 获取本地时区
import time
import json

# 读取config.json
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("config.json 文件未找到，使用默认配置")
        return {"API_TOKEN": "", "USERS": {}, "last_fetched_time": None}

# 保存config.json
def save_config(config):
    try:
        with open("config.json", "w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"保存配置文件失败: {e}")

# 通过 Telegram 机器人发送消息
def send_telegram_message(TELEGRAM_API_TOKEN, TELEGRAM_USER_ID, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_USER_ID,
        "text": message
    }
    
    headers = {
        'Content-Type': 'application/json; charset=UTF-8'  # 显式指定UTF-8编码
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            print(f"消息已发送到 Telegram: {message}")
        else:
            print(f"发送消息失败: {response.status_code}")
    except Exception as e:
        print(f"Telegram 发送消息失败: {e}")

# 获取并解析 RSS 内容
def fetch_rss(RSS_URL):
    try:
        response = requests.get(RSS_URL)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"获取RSS失败: {e}")
        return None

# 解析RSS并提取帖子数据
def parse_rss(xml_data, KEYWORDS, last_fetched_time):
    root = ET.fromstring(xml_data)
    posts = []
    
    local_timezone = get_localzone()  # 获取本地时区
    local_time = datetime.now(local_timezone)  # 获取本地时间
    gmt_time = local_time.astimezone(pytz.utc)  # 转换为 GMT (UTC)
    
    for item in root.findall(".//item"):
        title = item.find("title").text.strip()
        link = item.find("link").text.strip()
        pub_date_str = item.find("pubDate").text.strip()
        guid = item.find("guid").text.strip()
        
        pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S GMT")
        pub_date = pub_date.replace(tzinfo=pytz.utc)
        
        time_diff = gmt_time - pub_date
        
        # 只获取在上次爬取时间之后发布的帖子
        if pub_date > last_fetched_time:
            matched_keywords = [keyword for keyword in KEYWORDS if keyword.lower() in title.lower()]
            if matched_keywords:
                posts.append({"title": title, "link": link, "guid": guid, "pubDate": pub_date, "keywords": matched_keywords})
    
    return posts

# 更新last_fetched_time
def update_last_fetched_time(config):
    local_timezone = get_localzone()  # 获取本地时区
    local_time = datetime.now(local_timezone)  # 获取本地时间
    gmt_time = local_time.astimezone(pytz.utc)  # 转换为 GMT (UTC)
    config["last_fetched_time"] = gmt_time.isoformat()  # 记录为ISO格式字符串
    save_config(config)  # 保存配置文件

def main():
    print(f"开始爬取 RSS 数据")

    config = load_config()
    TELEGRAM_API_TOKEN = config["API_TOKEN"]  # 获取统一的 Telegram API Token
    RSS_URL = "https://rss.nodeseek.com/"

    last_fetched_time_str = config.get("last_fetched_time", None)
    if last_fetched_time_str:
        last_fetched_time = datetime.fromisoformat(last_fetched_time_str).replace(tzinfo=pytz.utc)
    else:
        # 如果没有记录时间，默认设为当前时间的 10 分钟前
        last_fetched_time = datetime.now(pytz.utc) - timedelta(minutes=10)

    for user_id, user_data in config["USERS"].items():
        KEYWORDS = user_data.get("keywords", [])
        keyword_switch = user_data.get("keyword_switch", "off")

        if keyword_switch == "on" and KEYWORDS:
            print(f"处理用户 {user_id}，状态：{keyword_switch}")
            
            # 获取并解析 RSS 数据
            rss_data = fetch_rss(RSS_URL)
            if rss_data:
                posts = parse_rss(rss_data, KEYWORDS, last_fetched_time)
                
                if posts:
                    print(f"找到新的匹配的帖子：")
                    for post in posts:
                        print(f"- {post['title']}: {post['link']}")
                        # 合并所有匹配的关键词并生成消息
                        keywords_str = ", ".join(post['keywords'])
                        message = f"{post['title']}\n{post['link']}"
                        send_telegram_message(TELEGRAM_API_TOKEN, user_id, message)
                else:
                    print(f"用户 {user_id} 未找到新的匹配的帖子")
            else:
                print("无法获取RSS数据")
        else:
            print(f"用户 {user_id} 的状态为 off 或没有设置关键字，跳过处理")

    # 更新爬取时间
    update_last_fetched_time(config)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60)  # 每1分钟执行一次
