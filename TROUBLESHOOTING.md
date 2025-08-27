# 故障排除指南

## Telegram 连接问题解决方案

### 问题诊断

根据您遇到的 Telegram 连接问题，我们已经进行了全面的诊断和修复：

#### 1. SSL 证书验证错误 ✅ 已修复

**错误信息：**

```
SSLCertVerificationError: certificate verify failed: self-signed certificate in certificate chain
```

**修复方案：**

- 在所有 Telegram API 请求中配置了跳过 SSL 验证的上下文
- 创建了统一的`create_ssl_context()`函数
- 更新了`TelegramBot`类的所有网络请求方法

#### 2. Chat ID 权限问题 ⚠️ 需要用户操作

**错误信息：**

```
Bad Request: need administrator rights in the channel chat
```

**解决方案（选择其一）：**

##### 方案 1：将机器人设为频道管理员（推荐）

1. 进入您的 Telegram 频道
2. 点击频道名称进入设置
3. 选择"管理员"
4. 点击"添加管理员"
5. 搜索并添加您的机器人 `@lashi_address_tracker_bot`
6. 给予必要的权限（发送消息、删除消息等）

##### 方案 2：使用私聊 Chat ID

1. 直接与机器人 `@lashi_address_tracker_bot` 开始私聊
2. 发送任意消息（如 `/start`）
3. 运行以下命令获取您的私聊 Chat ID：

```bash
python -c "
import asyncio
import aiohttp
import ssl
from config import config

async def get_chat_id():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        url = f'https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates'
        async with session.get(url) as response:
            data = await response.json()
            for update in data.get('result', []):
                if 'message' in update:
                    chat = update['message']['chat']
                    if chat['type'] == 'private':
                        print(f'您的私聊Chat ID: {chat[\"id\"]}')
                        break

asyncio.run(get_chat_id())
"
```

4. 将获得的 Chat ID 更新到`.env`文件中

### 当前状态

程序现在可以正常运行：

✅ **网络连接** - 正常  
✅ **SSL 配置** - 已修复  
✅ **WebSocket 连接** - 正常连接到 Infura  
✅ **区块订阅** - 成功订阅新区块  
✅ **地址监听** - 功能正常  
⚠️ **Telegram 通知** - 需要修复权限问题

### 验证修复

运行以下命令验证所有功能：

```bash
# 1. 测试程序启动
python main.py

# 2. 验证Telegram权限修复后，测试命令功能
# 发送以下命令到机器人：
/help
/list_addresses
/add_address 0x1234567890abcdef1234567890abcdef12345678
```

### 日志说明

正常运行时，您应该看到：

- `已连接到WebSocket` - 区块链连接正常
- `成功订阅新区块` - 订阅功能正常
- `开始监听 X 个地址的交易` - 监听功能启动
- `检测到新区块` - 实时接收区块数据

如果 Telegram 权限问题解决，还会看到：

- `Telegram bot连接测试成功` - Telegram 功能正常

### 技术细节

本次修复涉及的技术改进：

1. **SSL 配置统一化**

   - 创建`create_ssl_context()`函数
   - 在所有 aiohttp 连接中应用跳过 SSL 验证的配置

2. **错误处理增强**

   - 区分 SSL 错误和权限错误
   - 提供明确的解决建议

3. **会话管理改进**
   - 确保所有 Telegram API 调用使用相同的 SSL 配置
   - 正确管理 aiohttp 会话生命周期

### 联系支持

如果您在修复过程中遇到其他问题：

1. 检查`.env`文件配置是否正确
2. 确认网络连接正常
3. 查看程序日志文件`address_monitor.log`
4. 验证 Telegram Bot Token 有效性
