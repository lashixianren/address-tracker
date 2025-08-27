#!/usr/bin/env python3
"""
简单的Telegram API测试脚本
"""

import asyncio
import aiohttp
import ssl
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_telegram_api():
    """测试Telegram API连接"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN 未配置")
        return
    
    base_url = f"https://api.telegram.org/bot{token}"
    
    # 创建SSL上下文
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # 测试getMe
        print("🔍 测试 getMe...")
        async with session.get(f"{base_url}/getMe") as response:
            if response.status == 200:
                data = await response.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    print(f"✅ Bot信息: {bot_info.get('first_name')} (@{bot_info.get('username')})")
                else:
                    print(f"❌ getMe失败: {data}")
            else:
                print(f"❌ getMe请求失败: {response.status}")
        
        # 测试getUpdates
        print("\n🔍 测试 getUpdates...")
        params = {
            "limit": 5,
            "timeout": 5
        }
        
        async with session.get(f"{base_url}/getUpdates", params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("ok"):
                    updates = data.get("result", [])
                    print(f"✅ 获取到 {len(updates)} 个更新")
                    for i, update in enumerate(updates):
                        update_id = update.get("update_id", "unknown")
                        if "message" in update:
                            message = update["message"]
                            chat_id = message.get("chat", {}).get("id", "unknown")
                            text = message.get("text", "no text")
                            print(f"  更新 {i+1}: ID={update_id}, 聊天ID={chat_id}, 内容={text[:50]}...")
                        else:
                            print(f"  更新 {i+1}: ID={update_id}, 类型=其他")
                else:
                    print(f"❌ getUpdates失败: {data}")
            else:
                print(f"❌ getUpdates请求失败: {response.status}")
                error_text = await response.text()
                print(f"错误详情: {error_text}")

if __name__ == "__main__":
    asyncio.run(test_telegram_api())
