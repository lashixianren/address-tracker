"""
Configuration module for the Address Tracker application.
Loads environment variables and provides configuration settings.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class that holds all application settings."""
    
    # Infura WebSocket URL
    INFURA_WSS_URL = os.getenv('INFURA_WSS_URL')
    
    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    
    # Monitored Addresses
    _monitored_addresses_str = os.getenv('MONITORED_ADDRESSES', '')
    MONITORED_ADDRESSES = [addr.strip() for addr in _monitored_addresses_str.split(',') if addr.strip()]
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # SSL Configuration
    SSL_VERIFY = os.getenv('SSL_VERIFY', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of missing required settings."""
        errors = []
        
        if not cls.INFURA_WSS_URL:
            errors.append("INFURA_WSS_URL is required")
        
        # TELEGRAM_BOT_TOKEN is optional - if not set, Telegram features will be disabled
        # TELEGRAM_CHAT_ID is optional - if not set, bot will listen to any private chat
        # MONITORED_ADDRESSES is optional as addresses can be managed via Telegram
        
        return errors
    
    @classmethod
    def has_telegram_config(cls) -> bool:
        """Check if Telegram is configured."""
        return bool(cls.TELEGRAM_BOT_TOKEN)
    
    @classmethod
    def is_channel_mode(cls) -> bool:
        """Check if running in channel mode (with specific chat ID)."""
        return bool(cls.TELEGRAM_CHAT_ID)
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)."""
        print("📋 当前配置:")
        print(f"   🌐 Infura WSS URL: {cls.INFURA_WSS_URL[:50]}..." if cls.INFURA_WSS_URL else "   🌐 Infura WSS URL: ❌ 未配置")
        print(f"   🤖 Telegram Bot Token: {'✓ 已配置' if cls.TELEGRAM_BOT_TOKEN else '❌ 未配置'}")
        if cls.TELEGRAM_CHAT_ID:
            print(f"   💬 Telegram Chat ID: ✓ 已配置 (频道模式)")
        else:
            print(f"   💬 Telegram Chat ID: 未配置 (私聊模式)")
        print(f"   📁 配置文件地址数量: {len(cls.MONITORED_ADDRESSES)}")
        print(f"   📝 日志级别: {cls.LOG_LEVEL}")
        print(f"   🔒 SSL验证: {'启用' if cls.SSL_VERIFY else '禁用'}")
        print("   💡 监听地址现在通过 Telegram 命令动态管理")

# Create a global config instance
config = Config()
