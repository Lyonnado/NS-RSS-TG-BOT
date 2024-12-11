import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# 加载配置
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"API_TOKEN": "", "USERS": {}}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# 保存配置
def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

# 更新用户信息
def update_user_info(user_id, key, value, action="add"):
    config = load_config()
    users = config.setdefault("USERS", {})
    user_data = users.setdefault(user_id, {})
    
    if action == "add":
        user_data[key] = value
    elif action == "update":
        user_data[key] = value
    elif action == "delete":
        if key in user_data:
            del user_data[key]

    save_config(config)

# 添加关键字
async def add_keywords(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    if len(context.args) == 0:
        await update.message.reply_text("请提供需要添加的关键词，例如：/add 关键字1 关键字2")
        return

    keywords = context.args
    config = load_config()
    user_data = config.get("USERS", {}).get(user_id, {})
    existing_keywords = set(user_data.get("keywords", []))  # 获取当前已有的关键字

    # 将新添加的关键字与现有的关键字合并
    updated_keywords = list(existing_keywords | set(keywords))  # 使用集合合并，避免重复

    update_user_info(user_id, "keywords", updated_keywords, action="update")
    await update.message.reply_text(f"已添加关键词：{'，'.join(keywords)}")

# 列出关键字
async def list_keywords(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    config = load_config()
    user_data = config.get("USERS", {}).get(user_id, {})
    keywords = user_data.get("keywords", [])

    if keywords:
        await update.message.reply_text(f"你的关键词列表：\n{'，'.join(keywords)}")
    else:
        await update.message.reply_text("你目前没有设置任何关键词。")

# 删除关键字
async def delete_keywords(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    if len(context.args) == 0:
        await update.message.reply_text("请提供需要删除的关键词，例如：/delete 关键字1 关键字2")
        return

    keywords = context.args
    config = load_config()
    user_data = config.get("USERS", {}).get(user_id, {})
    existing_keywords = set(user_data.get("keywords", []))
    to_remove = set(keywords)

    if not to_remove & existing_keywords:
        await update.message.reply_text("没有找到匹配的关键词，无法删除。")
        return

    update_user_info(user_id, "keywords", list(existing_keywords - to_remove), action="update")
    await update.message.reply_text(f"已删除关键词：{'，'.join(to_remove)}")

# 打开关键字开关
async def turn_on(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    update_user_info(user_id, "keyword_switch", "on", action="update")
    await update.message.reply_text("已将关键字开关设置为开。")
    print(f"用户 {user_id} 设置了开关为开")  # 添加调试信息

# 关闭关键字开关
async def turn_off(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    update_user_info(user_id, "keyword_switch", "off", action="update")
    await update.message.reply_text("已将关键字开关设置为关。")
    print(f"用户 {user_id} 设置了开关为关")  # 添加调试信息

def main():
    # 加载配置
    config = load_config()
    api_token = config.get("API_TOKEN")
    if not api_token:
        raise ValueError("配置文件中未找到 API_TOKEN，请确保正确配置。")

    # 初始化 Telegram 应用
    application = Application.builder().token(api_token).build()

    # 添加处理器
    application.add_handler(CommandHandler("add", add_keywords))
    application.add_handler(CommandHandler("list", list_keywords))
    application.add_handler(CommandHandler("delete", delete_keywords))
    application.add_handler(CommandHandler("on", turn_on))
    application.add_handler(CommandHandler("off", turn_off))

    application.run_polling()

if __name__ == '__main__':
    main()
