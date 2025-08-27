"""
Telegram Bot module for sending transaction notifications and handling commands.
"""

import asyncio
import aiohttp
import logging
import json
import ssl
import os
from typing import Optional, Dict, Any, Callable, List, Set
from config import config
from address_storage import get_address_storage

logger = logging.getLogger(__name__)

def create_ssl_context():
    """Create SSL context that skips verification."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

class UpdateIdManager:
    """Manages persistent storage of last update ID to avoid reprocessing old messages."""
    
    def __init__(self, storage_file: str = "last_update_id.txt"):
        self.storage_file = storage_file
    
    def load_last_update_id(self) -> int:
        """Load the last processed update ID from file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    update_id = int(f.read().strip())
                    logger.info(f"加载上次处理的update ID: {update_id}")
                    return update_id
        except (ValueError, IOError) as e:
            logger.warning(f"加载update ID失败: {e}")
        
        return 0
    
    def save_last_update_id(self, update_id: int):
        """Save the last processed update ID to file."""
        try:
            with open(self.storage_file, 'w') as f:
                f.write(str(update_id))
        except IOError as e:
            logger.error(f"保存update ID失败: {e}")

class TelegramBot:
    """Telegram Bot client for sending messages and handling commands."""
    
    def __init__(self, bot_token: str, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id  # None means accept any private chat
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.session = None
        self.commands: Dict[str, Callable] = {}
        self.update_manager = UpdateIdManager()
        self.last_update_id = self.update_manager.load_last_update_id()
        self.polling = False
        self.webhook_mode = False
        self.authorized_users: Set[str] = set()  # Track authorized users in private mode
    
    async def __aenter__(self):
        """Async context manager entry."""
        if not self.session:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def send_message(self, text: str, parse_mode: str = "HTML", chat_id: Optional[str] = None) -> bool:
        """
        Send a message to a Telegram chat.
        
        Args:
            text: Message text to send
            parse_mode: Parse mode for the message (HTML, Markdown, or None)
            chat_id: Optional chat ID to send to (uses default if not provided)
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        target_chat_id = chat_id or self.chat_id
        
        # Skip sending if no target chat_id
        if not target_chat_id:
            logger.debug("跳过发送消息：未配置Chat ID且未提供chat_id参数")
            return True
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": target_chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            if not self.session:
                # Create SSL context that skips verification
                ssl_context = create_ssl_context()
                
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                self.session = aiohttp.ClientSession(connector=connector)
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.debug(f"消息发送成功: {text[:50]}...")
                    return True
                else:
                    error_text = await response.text()
                    if response.status == 400 and "need administrator rights" in error_text:
                        logger.warning(f"Telegram权限不足: 机器人需要在频道中有管理员权限")
                        logger.info("提示: 请将机器人设为频道管理员，或使用私聊Chat ID")
                    else:
                        logger.error(f"发送Telegram消息失败 (状态码: {response.status}): {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"发送Telegram消息时发生错误: {e}")
            return False
    
    async def send_transaction_alert(self, transaction_info: dict) -> bool:
        """
        Send a formatted transaction alert to Telegram.
        
        Args:
            transaction_info: Dictionary containing transaction details
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            # Format transaction info for Telegram
            tx_hash = transaction_info.get("hash", "")
            tx_from = transaction_info.get("from", "")
            tx_to = transaction_info.get("to", "")
            value = transaction_info.get("value", "0")
            gas_price = transaction_info.get("gasPrice", "0")
            block_number = transaction_info.get("blockNumber", "")
            
            # Convert Wei to ETH
            try:
                value_eth = int(value, 16) / 10**18 if value != "0x0" else 0
            except (ValueError, TypeError):
                value_eth = 0
            
            # Convert Wei to Gwei for gas price
            try:
                gas_price_gwei = int(gas_price, 16) / 10**9 if gas_price != "0x0" else 0
            except (ValueError, TypeError):
                gas_price_gwei = 0
            
            # Create formatted message
            message = (
                f"🔗 <b>新交易检测到!</b>\n\n"
                f"📊 <b>区块号:</b> {block_number}\n"
                f"🔑 <b>交易哈希:</b>\n<code>{tx_hash}</code>\n\n"
                f"📤 <b>发送方:</b>\n<code>{tx_from}</code>\n\n"
                f"📥 <b>接收方:</b>\n<code>{tx_to}</code>\n\n"
                f"💰 <b>金额:</b> {value_eth:.6f} ETH\n"
                f"⛽ <b>Gas价格:</b> {gas_price_gwei:.2f} Gwei\n\n"
                f"🔍 <a href='https://sepolia.etherscan.io/tx/{tx_hash}'>在 Etherscan 上查看</a>"
            )
            
            return await self.send_message(message)
            
        except Exception as e:
            logger.error(f"格式化交易警报时发生错误: {e}")
            return False
    
    async def send_status_message(self, message: str) -> bool:
        """
        Send a status/info message to Telegram.
        
        Args:
            message: Status message to send
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        formatted_message = f"ℹ️ <b>状态更新</b>\n\n{message}"
        return await self.send_message(formatted_message)
    
    async def send_error_message(self, error_message: str) -> bool:
        """
        Send an error message to Telegram.
        
        Args:
            error_message: Error message to send
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        formatted_message = f"❌ <b>错误警报</b>\n\n{error_message}"
        return await self.send_message(formatted_message)
    
    async def test_connection(self) -> bool:
        """
        Test the Telegram bot connection by sending a test message.
        
        Returns:
            bool: True if connection test successful, False otherwise
        """
        # Initialize session with SSL configuration if needed
        if not self.session:
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)
        
        test_message = "✅ Telegram通知已连接，监听器准备就绪"
        result = await self.send_message(test_message)
        
        if result:
            logger.info("Telegram bot连接测试成功")
        else:
            logger.error("Telegram bot连接测试失败")
        
        return result
    
    def register_command(self, command: str, handler: Callable):
        """Register a command handler."""
        self.commands[command] = handler
        logger.debug(f"注册命令处理器: {command}")
    
    async def get_updates(self) -> List[Dict[str, Any]]:
        """Get updates from Telegram bot API."""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "limit": 10,
                "timeout": 10
            }
            
            if not self.session:
                # Create SSL context that skips verification
                ssl_context = create_ssl_context()
                
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                self.session = aiohttp.ClientSession(connector=connector)
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        return data.get("result", [])
                    else:
                        logger.error(f"获取更新失败: {data}")
                        return []
                else:
                    error_text = await response.text()
                    logger.error(f"获取更新请求失败 (状态码: {response.status}): {error_text}")
                    return []
                    
        except Exception as e:
            # Don't log every network error to avoid spam
            if "Connect call failed" not in str(e) and "Connection refused" not in str(e):
                logger.error(f"获取更新时发生错误: {e}")
            return []
    
    async def process_update(self, update: Dict[str, Any]):
        """Process a single update from Telegram."""
        try:
            if "message" in update:
                message = update["message"]
                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))
                text = message.get("text", "")
                user = message.get("from", {})
                username = user.get("username", "")
                first_name = user.get("first_name", "")
                
                # Print all received messages for monitoring
                logger.info(f"收到消息 - 聊天ID: {chat_id}, 用户: {first_name} (@{username}), 内容: {text}")
                print(f"📨 收到消息:")
                print(f"   聊天ID: {chat_id}")
                print(f"   用户: {first_name} (@{username})")
                print(f"   聊天类型: {chat.get('type', 'unknown')}")
                print(f"   内容: {text}")
                print("-" * 40)
                
                # If no specific chat_id configured, process commands from any private chat
                if not self.chat_id:
                    if chat.get("type") == "private" and text.startswith("/"):
                        await self.handle_command(text, message)
                    return
                
                # If chat_id is configured, only process messages from that chat
                if chat_id != self.chat_id:
                    logger.debug(f"忽略来自其他聊天的消息: {chat_id}")
                    return
                
                # Process commands
                if text.startswith("/"):
                    await self.handle_command(text, message)
                    
        except Exception as e:
            logger.error(f"处理更新时发生错误: {e}")
    
    async def handle_command(self, text: str, message: Dict[str, Any]):
        """Handle bot commands."""
        try:
            parts = text.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            chat_id = str(message.get("chat", {}).get("id", ""))
            
            if command in self.commands:
                await self.commands[command](args, message)
            elif command == "/help":
                await self.send_help_message(chat_id)
            else:
                await self.send_unknown_command_message(command, chat_id)
                
        except Exception as e:
            logger.error(f"处理命令时发生错误: {e}")
            chat_id = str(message.get("chat", {}).get("id", ""))
            await send_reply_message(chat_id, f"❌ 处理命令时发生错误: {str(e)}")
    
    async def send_help_message(self, chat_id: str = None):
        """Send help message with available commands."""
        help_text = (
            "📋 <b>以太坊地址监听器命令帮助</b>\n\n"
            "🔧 <b>地址管理命令:</b>\n"
            "/add_address &lt;地址&gt; - 添加新的监听地址到您的订阅\n"
            "/remove_address &lt;地址&gt; - 从您的订阅中移除指定地址\n"
            "/list_addresses - 显示您订阅的所有地址\n"
            "/clear_addresses - 清空您的所有地址订阅\n\n"
            "📊 <b>统计命令:</b>\n"
            "/stats - 显示系统统计信息\n\n"
            "ℹ️ <b>其他命令:</b>\n"
            "/help - 显示此帮助信息\n\n"
            "📝 <b>使用示例:</b>\n"
            "<code>/add_address 0x1234567890abcdef1234567890abcdef12345678</code>\n"
            "<code>/remove_address 0x1234567890abcdef1234567890abcdef12345678</code>\n\n"
            "💡 <b>提示:</b> 地址格式支持带或不带 0x 前缀\n"
            "🔔 <b>通知:</b> 当您订阅的地址有新交易时，会自动发送通知"
        )
        if chat_id:
            await send_reply_message(chat_id, help_text)
        else:
            await self.send_message(help_text)
    
    async def send_unknown_command_message(self, command: str, chat_id: str = None):
        """Send message for unknown command."""
        message = f"❓ 未知命令: {command}\n\n发送 /help 查看可用命令"
        if chat_id:
            await send_reply_message(chat_id, message)
        else:
            await self.send_message(message)
    
    async def start_polling(self):
        """Start polling for updates."""
        self.polling = True
        logger.info("开始监听Telegram命令...")
        
        # Ensure session is initialized for polling
        if not self.session:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(connector=connector)
        
        while self.polling:
            try:
                updates = await self.get_updates()
                
                if updates:
                    logger.info(f"收到 {len(updates)} 个更新")
                
                for update in updates:
                    current_update_id = update.get("update_id", 0)
                    
                    # Skip if this update was already processed
                    if current_update_id <= self.last_update_id:
                        logger.debug(f"跳过已处理的update: {current_update_id}")
                        continue
                    
                    logger.info(f"处理新update: {current_update_id}")
                    await self.process_update(update)
                    
                    # Update and save the last processed update ID
                    self.last_update_id = current_update_id
                    self.update_manager.save_last_update_id(self.last_update_id)
                
                # Small delay to prevent too frequent requests
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"轮询更新时发生错误: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    def stop_polling(self):
        """Stop polling for updates."""
        self.polling = False
        logger.info("停止监听Telegram命令")
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL for receiving updates."""
        try:
            if not self.session:
                ssl_context = create_ssl_context()
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                self.session = aiohttp.ClientSession(connector=connector)
            
            url = f"{self.base_url}/setWebhook"
            data = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
            
            async with self.session.post(url, json=data) as response:
                result = await response.json()
                if result.get("ok"):
                    logger.info(f"Webhook设置成功: {webhook_url}")
                    self.webhook_mode = True
                    return True
                else:
                    logger.error(f"Webhook设置失败: {result.get('description')}")
                    return False
                    
        except Exception as e:
            logger.error(f"设置webhook时发生错误: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """Delete webhook and return to polling mode."""
        try:
            if not self.session:
                ssl_context = create_ssl_context()
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                self.session = aiohttp.ClientSession(connector=connector)
            
            url = f"{self.base_url}/deleteWebhook"
            
            async with self.session.post(url) as response:
                result = await response.json()
                if result.get("ok"):
                    logger.info("Webhook删除成功")
                    self.webhook_mode = False
                    return True
                else:
                    logger.error(f"Webhook删除失败: {result.get('description')}")
                    return False
                    
        except Exception as e:
            logger.error(f"删除webhook时发生错误: {e}")
            return False
    
    async def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Get current webhook information."""
        try:
            if not self.session:
                ssl_context = create_ssl_context()
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                self.session = aiohttp.ClientSession(connector=connector)
            
            url = f"{self.base_url}/getWebhookInfo"
            
            async with self.session.get(url) as response:
                result = await response.json()
                if result.get("ok"):
                    return result.get("result")
                else:
                    logger.error(f"获取webhook信息失败: {result.get('description')}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取webhook信息时发生错误: {e}")
            return None
    
    async def process_webhook_update(self, update: Dict[str, Any]):
        """Process update received from webhook."""
        try:
            current_update_id = update.get("update_id", 0)
            
            # Skip if this update was already processed
            if current_update_id <= self.last_update_id:
                logger.debug(f"跳过已处理的update: {current_update_id}")
                return
            
            logger.info(f"处理webhook update: {current_update_id}")
            await self.process_update(update)
            
            # Update and save the last processed update ID
            self.last_update_id = current_update_id
            self.update_manager.save_last_update_id(self.last_update_id)
            
        except Exception as e:
            logger.error(f"处理webhook更新时发生错误: {e}")

# Global Telegram bot instance
telegram_bot = None

async def get_telegram_bot() -> Optional[TelegramBot]:
    """Get the global Telegram bot instance."""
    global telegram_bot
    
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram Bot Token未配置，跳过Telegram功能")
        return None
    
    if telegram_bot is None:
        # Use empty string for chat_id if not configured (private chat mode)
        chat_id = config.TELEGRAM_CHAT_ID or ""
        telegram_bot = TelegramBot(config.TELEGRAM_BOT_TOKEN, chat_id)
    
    return telegram_bot

async def send_transaction_notification(transaction_info: dict) -> bool:
    """
    Send a transaction notification via Telegram.
    
    Args:
        transaction_info: Dictionary containing transaction details
    
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    bot = await get_telegram_bot()
    if not bot:
        return False
    
    return await bot.send_transaction_alert(transaction_info)

async def send_status_notification(message: str) -> bool:
    """
    Send a status notification via Telegram.
    
    Args:
        message: Status message to send
    
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    bot = await get_telegram_bot()
    if not bot:
        return False
    
    return await bot.send_status_message(message)

async def send_error_notification(error_message: str) -> bool:
    """
    Send an error notification via Telegram.
    
    Args:
        error_message: Error message to send
    
    Returns:
        bool: True if notification was sent successfully, False otherwise
    """
    bot = await get_telegram_bot()
    if not bot:
        return False
    
    return await bot.send_error_message(error_message)

async def send_reply_message(chat_id: str, text: str) -> bool:
    """
    Send a reply message to a specific chat.
    
    Args:
        chat_id: Target chat ID
        text: Message text to send
    
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    bot = await get_telegram_bot()
    if not bot:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if not bot.session:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            bot.session = aiohttp.ClientSession(connector=connector)
        
        async with bot.session.post(url, json=payload) as response:
            if response.status == 200:
                logger.debug(f"回复消息发送成功: {text[:50]}...")
                return True
            else:
                error_text = await response.text()
                logger.error(f"回复消息发送失败 (状态码: {response.status}): {error_text}")
                return False
                
    except Exception as e:
        logger.error(f"发送回复消息时发生错误: {e}")
        return False

# Command handlers
async def handle_add_address(args: List[str], message: Dict[str, Any]):
    """Handle /add_address command."""
    try:
        bot = await get_telegram_bot()
        if not bot:
            logger.error("无法获取Telegram bot实例")
            return
        
        # Get chat_id from the message
        chat_id = str(message.get("chat", {}).get("id", ""))
        logger.info(f"处理add_address命令，聊天ID: {chat_id}")
        
        if not args:
            logger.info("add_address命令缺少参数")
            await send_reply_message(chat_id, "❌ 请提供要添加的地址\n\n用法: /add_address <地址>")
            return
        
        address = args[0]
        logger.info(f"尝试添加地址: {address}")
        storage = get_address_storage()
        
        success, msg = await storage.add_address(address, int(chat_id))
        logger.info(f"添加地址结果: success={success}, msg={msg}")
        
        if success:
            count = await storage.get_address_count()
            response = f"✅ {msg}\n\n📊 当前监听地址总数: {count}"
        else:
            response = f"❌ {msg}"
        
        logger.info(f"发送回复消息: {response}")
        await send_reply_message(chat_id, response)
        logger.info("add_address命令处理完成")
        
    except Exception as e:
        logger.error(f"处理add_address命令时发生错误: {e}")
        chat_id = str(message.get("chat", {}).get("id", ""))
        await send_reply_message(chat_id, f"❌ 处理命令时发生错误: {str(e)}")

async def handle_remove_address(args: List[str], message: Dict[str, Any]):
    """Handle /remove_address command."""
    bot = await get_telegram_bot()
    if not bot:
        return
    
    # Get chat_id from the message
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    if not args:
        await send_reply_message(chat_id, "❌ 请提供要移除的地址\n\n用法: /remove_address <地址>")
        return
    
    address = args[0]
    storage = get_address_storage()
    
    success, msg = await storage.remove_address(address, int(chat_id))
    
    if success:
        count = await storage.get_address_count()
        response = f"✅ {msg}\n\n📊 当前监听地址总数: {count}"
    else:
        response = f"❌ {msg}"
    
    await send_reply_message(chat_id, response)

async def handle_list_addresses(args: List[str], message: Dict[str, Any]):
    """Handle /list_addresses command."""
    bot = await get_telegram_bot()
    if not bot:
        return
    
    # Get chat_id from the message
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    storage = get_address_storage()
    addresses = await storage.get_user_addresses(int(chat_id))
    count = len(addresses)
    
    if count == 0:
        response = "📭 您当前没有订阅任何地址\n\n使用 /add_address &lt;地址&gt; 添加监听地址"
    else:
        response = f"📋 <b>您的监听地址列表</b> ({count} 个)\n\n"
        
        for i, addr in enumerate(addresses, 1):
            response += f"{i}. <code>{addr}</code>\n"
        
        response += f"\n📊 总计: {count} 个地址"
    
    await send_reply_message(chat_id, response)

async def handle_clear_addresses(args: List[str], message: Dict[str, Any]):
    """Handle /clear_addresses command."""
    bot = await get_telegram_bot()
    if not bot:
        return
    
    # Get chat_id from the message
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    storage = get_address_storage()
    user_addresses = await storage.get_user_addresses(int(chat_id))
    count_before = len(user_addresses)
    
    if count_before == 0:
        await send_reply_message(chat_id, "📭 您当前没有订阅任何地址，无需清空")
        return
    
    success, msg = await storage.clear_addresses(int(chat_id))
    
    if success:
        response = f"✅ {msg}"
    else:
        response = f"❌ {msg}"
    
    await send_reply_message(chat_id, response)

async def handle_stats(args: List[str], message: Dict[str, Any]):
    """Handle /stats command - show global statistics."""
    bot = await get_telegram_bot()
    if not bot:
        return
    
    # Get chat_id from the message
    chat_id = str(message.get("chat", {}).get("id", ""))
    
    storage = get_address_storage()
    all_addresses = await storage.get_addresses()
    total_addresses = len(all_addresses)
    
    if total_addresses == 0:
        response = "📊 <b>系统统计</b>\n\n📭 当前系统中没有任何监听地址"
    else:
        # Count total subscribers
        total_subscribers = 0
        for address in all_addresses:
            subscribers = await storage.get_address_subscribers(address)
            total_subscribers += len(subscribers)
        
        response = f"📊 <b>系统统计</b>\n\n"
        response += f"📍 监听地址总数: {total_addresses}\n"
        response += f"👥 订阅总数: {total_subscribers}\n"
        response += f"📈 平均每地址订阅数: {total_subscribers/total_addresses:.1f}"
    
    await send_reply_message(chat_id, response)

async def setup_bot_commands(bot: TelegramBot):
    """Setup bot commands."""
    bot.register_command("/add_address", handle_add_address)
    bot.register_command("/remove_address", handle_remove_address)
    bot.register_command("/list_addresses", handle_list_addresses)
    bot.register_command("/clear_addresses", handle_clear_addresses)
    bot.register_command("/stats", handle_stats)
    logger.info("Telegram bot命令已注册")

async def start_bot_polling():
    """Start bot polling in background."""
    bot = await get_telegram_bot()
    if not bot:
        logger.warning("无法启动bot轮询：bot未配置")
        return None
    
    await setup_bot_commands(bot)
    
    # Start polling in background
    task = asyncio.create_task(bot.start_polling())
    logger.info("Telegram bot轮询已启动")
    return task

async def stop_bot_polling(task: Optional[asyncio.Task]):
    """Stop bot polling."""
    if task and not task.done():
        bot = await get_telegram_bot()
        if bot:
            bot.stop_polling()
        
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
            logger.warning("强制取消bot轮询任务")
        
        # Close the session when stopping
        if bot and bot.session:
            await bot.session.close()
            bot.session = None
        
        logger.info("Telegram bot轮询已停止")
