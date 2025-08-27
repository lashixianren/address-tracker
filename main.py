"""
Ethereum Address Transaction Monitor with Telegram Notifications

This is the main entry point for the address monitoring application.
It monitors specified Ethereum addresses for transactions and sends 
notifications via Telegram bot.

Author: AI Assistant
"""

import asyncio
import logging
import sys
from config import config
from address_monitor import create_address_monitor
from telegram_bot import get_telegram_bot, send_status_notification, send_error_notification, start_bot_polling, stop_bot_polling
from webhook_server import start_webhook_server, stop_webhook_server, setup_webhook, cleanup_webhook
from address_storage import initialize_address_storage

# Configure logging
def setup_logging():
    """Setup logging configuration."""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('address_monitor.log', encoding='utf-8')
        ]
    )

logger = logging.getLogger(__name__)

async def validate_configuration():
    """
    Validate application configuration.
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    config_errors = config.validate()
    
    if config_errors:
        print("❌ 配置验证失败:")
        for error in config_errors:
            print(f"   • {error}")
        print("\n💡 请检查以下文件:")
        print("   • .env 文件（复制 .env.example 并填写正确的值）")
        print("   • 确保所有必需的环境变量都已设置")
        return False
    
    return True

async def test_telegram_connection():
    """
    Test Telegram bot connection.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    if not config.has_telegram_config():
        print("ℹ️  未配置Telegram Bot Token，将跳过Telegram功能")
        return False
        
    print("🧪 测试Telegram连接...")
    bot = await get_telegram_bot()
    
    if not bot:
        print("⚠️  Telegram配置异常，将跳过Telegram通知")
        return False
    
    # Test connection without using context manager to avoid closing session
    success = await bot.test_connection()
    if success:
        if config.is_channel_mode():
            print("✅ Telegram连接测试成功 (频道模式)")
        else:
            print("✅ Telegram连接测试成功 (私聊模式)")
    else:
        if config.is_channel_mode():
            print("⚠️  Telegram连接测试失败（可能是权限问题）")
            print("💡 程序将继续运行，但Telegram通知可能无法正常工作")
            print("   请检查：")
            print("   1. 机器人是否在频道中有管理员权限")
            print("   2. 或考虑使用私聊模式（删除TELEGRAM_CHAT_ID配置）")
        else:
            print("⚠️  Telegram连接测试失败")
            print("💡 程序将继续运行，私聊模式下用户仍可发送命令")
    return success

def print_startup_info():
    """Print application startup information."""
    print("🚀 以太坊地址交易监听器")
    print("=" * 50)
    print(f"📱 版本: 2.0.0")
    print(f"🌐 网络: Sepolia 测试网")
    print("")
    
    # Print configuration
    config.print_config()
    print("")

async def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    
    # Print startup information
    print_startup_info()
    
    # Validate configuration
    if not await validate_configuration():
        return 1
    
    # Initialize address storage
    print("📁 初始化地址存储...")
    await initialize_address_storage()
    
    # Test Telegram connection
    telegram_available = await test_telegram_connection()
    
    # Create address monitor
    print("🔧 创建地址监听器...")
    monitor = await create_address_monitor()
    
    # Start webhook server or polling for commands
    webhook_server = None
    bot_task = None
    
    if config.has_telegram_config():
        if config.WEBHOOK_URL:
            # Use webhook mode
            if config.is_channel_mode():
                print("🤖 启动 Telegram Webhook 服务器 (频道模式)...")
            else:
                print("🤖 启动 Telegram Webhook 服务器 (私聊模式)...")
            
            # Start webhook server on port 8081 to avoid conflict with ngrok
            webhook_server = await start_webhook_server(port=8081)
            if webhook_server:
                # Setup webhook with Telegram
                webhook_success = await setup_webhook(config.WEBHOOK_URL)
                if not webhook_success:
                    print("⚠️  Webhook设置失败，将回退到轮询模式")
                    await stop_webhook_server()
                    webhook_server = None
                    bot_task = await start_bot_polling()
                else:
                    print(f"✅ Webhook模式启动成功: {config.WEBHOOK_URL}")
            else:
                print("⚠️  Webhook服务器启动失败，将回退到轮询模式")
                bot_task = await start_bot_polling()
        else:
            # Use polling mode
            if config.is_channel_mode():
                print("🤖 启动 Telegram 命令监听 (频道模式)...")
            else:
                print("🤖 启动 Telegram 命令监听 (私聊模式)...")
            bot_task = await start_bot_polling()
    else:
        print("ℹ️  Telegram功能已禁用")
    
    print("")
    print("🔄 按 Ctrl+C 停止监听")
    print("-" * 50)
    
    try:
        # Start monitoring
        await monitor.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n")
        logger.info("接收到中断信号，正在关闭...")
        if config.has_telegram_config() and telegram_available:
            await send_status_notification("⏹️ 监听已停止")
        
    except Exception as e:
        error_msg = f"程序运行出错: {e}"
        logger.error(error_msg)
        print(f"❌ {error_msg}")
        if config.has_telegram_config() and telegram_available:
            await send_error_notification(f"程序异常退出: {str(e)}")
        return 1
        
    finally:
        # Clean up
        print("🛑 正在停止服务...")
        
        # Stop webhook server or bot polling
        if config.has_telegram_config():
            if webhook_server:
                # Clean up webhook and stop server
                await cleanup_webhook()
                await stop_webhook_server()
            elif bot_task:
                await stop_bot_polling(bot_task)
        
        # Close monitor
        await monitor.close()
        print("👋 程序已退出")
    
    return 0

if __name__ == "__main__":
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)