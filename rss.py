import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone  # 获取本地时区
import time
import json

# 读取config.json
def load_config():
    with open("config.json", "r", encoding="utf-8") as file:
        return json.load(file)

# 通过 Telegram 机器人发送消息
def send_telegram_message(TELEGRAM_API_TOKEN, TELEGRAM_USER_ID, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_USER_ID,
        "text": message
    }
    try:
        response = requests.get(url, params=params)
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
        # 显式获取编码并解码内容
        encoding = response.encoding if response.encoding else 'utf-8'
        return response.content.decode(encoding)
    except Exception as e:
        print(f"获取RSS失败: {e}")
        return None

# 解析RSS并提取帖子数据
def parse_rss(xml_data, KEYWORDS):
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
        
        if time_diff <= timedelta(minutes=100):
            # 确保关键词匹配正常
            matched_keywords = [keyword for keyword in KEYWORDS if keyword in title]
            if matched_keywords:
                posts.append({"title": title, "link": link, "guid": guid, "pubDate": pub_date, "keywords": matched_keywords})
    
    return posts

def main():
    print(f"开始爬取 RSS 数据")

    config = load_config()
    TELEGRAM_API_TOKEN = config["API_TOKEN"]  # 获取统一的 Telegram API Token
    RSS_URL = "https://rss.nodeseek.com/"

    for user_id, user_data in config["USERS"].items():
        KEYWORDS = user_data["keywords"]
        keyword_switch = user_data["keyword_switch"]

        if keyword_switch == "on":
            print(f"处理用户 {user_id}，状态：{keyword_switch}")
            
            # 获取并解析 RSS 数据
            rss_data = fetch_rss(RSS_URL)
            if rss_data:
                posts = parse_rss(rss_data, KEYWORDS)
                
                if posts:
                    print(f"找到新的匹配的帖子：")
                    for post in posts:
                        print(f"- {post['title']}: {post['link']}")
                        for keyword in post['keywords']:
                            message = f"找到新的匹配的帖子：\n{post['title']} (关键字: {keyword})\n{post['link']}"
                            send_telegram_message(TELEGRAM_API_TOKEN, user_id, message)
                else:
                    print(f"用户 {user_id} 未找到新的匹配的帖子")
            else:
                print("无法获取RSS数据")
        else:
            print(f"用户 {user_id} 的状态为 off，跳过处理")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(20)  # 每1分钟执行一次

