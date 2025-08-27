# Ethereum Address Transaction Monitor

一个监听以太坊地址交易并通过 Telegram 机器人发送通知的 Python 应用程序。

## 功能特性

- 🔍 实时监听指定以太坊地址的交易
- 📱 通过 Telegram 机器人发送交易通知
- 🌐 支持 Sepolia 测试网络
- 📊 详细的交易信息展示
- 🛡️ 错误处理和重连机制
- 📝 完整的日志记录
- ⚙️ 模块化设计，易于扩展
- 🤖 **Telegram 命令动态管理监听地址**
  - `/add_address` - 添加新的监听地址
  - `/remove_address` - 移除监听地址
  - `/list_addresses` - 查看当前监听地址
  - `/clear_addresses` - 清空所有监听地址
  - `/help` - 显示命令帮助
- 💾 **持久化地址存储** - 地址信息保存在本地文件中

## 项目结构

```
address-tracker/
├── main.py                    # 主入口文件
├── config.py                  # 配置管理模块
├── address_monitor.py         # 地址监听模块
├── telegram_bot.py            # Telegram 机器人模块
├── address_storage.py         # 地址存储管理模块
├── requirements.txt           # 依赖包列表
├── setup.py                   # 自动安装脚本
├── monitored_addresses.json   # 监听地址存储文件（自动生成）
├── .env.example              # 环境变量示例文件
├── .env                      # 环境变量配置文件（需要创建）
├── .gitignore                # Git 忽略文件
└── README.md                 # 项目说明文档
```

## 安装步骤

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd address-tracker
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制示例配置文件并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下配置：

```env
# Infura WebSocket URL配置
INFURA_WSS_URL=wss://sepolia.infura.io/ws/v3/YOUR_PROJECT_ID

# Telegram机器人配置
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 监听地址（用逗号分隔）
MONITORED_ADDRESSES=0x1234...,0x5678...  # 可选，也可以通过 Telegram 命令添加

# 日志级别
LOG_LEVEL=INFO

# SSL验证（开发环境可设为false）
SSL_VERIFY=false
```

### 4. 获取必要的 API 密钥

#### 获取 Infura 项目 ID：

1. 访问 [Infura.io](https://infura.io/)
2. 注册并创建新项目
3. 复制项目 ID 并替换 URL 中的 `YOUR_PROJECT_ID`

#### 创建 Telegram 机器人：

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 命令创建新机器人
3. 按提示设置机器人名称和用户名
4. 获取机器人 Token 并设置到 `TELEGRAM_BOT_TOKEN`

#### 获取 Telegram 聊天 ID：

1. 在 Telegram 中搜索 `@userinfobot`
2. 发送任意消息获取你的用户 ID
3. 将用户 ID 设置到 `TELEGRAM_CHAT_ID`

## 使用方法

### 启动监听器

```bash
python main.py
```

### 通过 Telegram 管理监听地址

启动程序后，你可以通过 Telegram 发送以下命令来管理监听地址：

#### 添加地址

```
/add_address 0x1234567890abcdef1234567890abcdef12345678
```

#### 查看当前监听的地址

```
/list_addresses
```

#### 移除地址

```
/remove_address 0x1234567890abcdef1234567890abcdef12345678
```

#### 清空所有地址

```
/clear_addresses
```

#### 获取帮助

```
/help
```

### 停止监听器

按 `Ctrl+C` 停止程序

## 配置说明

### 环境变量说明

| 变量名                | 必需 | 说明                           | 示例值                                      |
| --------------------- | ---- | ------------------------------ | ------------------------------------------- |
| `INFURA_WSS_URL`      | 是   | Infura WebSocket 连接 URL      | `wss://sepolia.infura.io/ws/v3/abc123`      |
| `TELEGRAM_BOT_TOKEN`  | 是   | Telegram 机器人 Token          | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `TELEGRAM_CHAT_ID`    | 是   | Telegram 聊天 ID               | `123456789`                                 |
| `MONITORED_ADDRESSES` | 否   | 初始监听地址（逗号分隔，可选） | `0x123...,0x456...`                         |
| `LOG_LEVEL`           | 否   | 日志级别                       | `INFO`, `DEBUG`, `WARNING`, `ERROR`         |
| `SSL_VERIFY`          | 否   | 是否验证 SSL 证书              | `true`, `false`                             |

### 监听地址格式

支持以下格式的以太坊地址：

- 完整地址：`0x1234567890abcdef1234567890abcdef12345678`
- 地址大小写不敏感
- 配置文件中多个地址用逗号分隔
- **推荐通过 Telegram 命令动态管理地址，无需重启程序**

## 输出示例

### 控制台输出

```
🚀 以太坊地址交易监听器
==================================================
📱 版本: 2.0.0
🌐 网络: Sepolia 测试网

📋 当前配置:
   🌐 Infura WSS URL: wss://sepolia.infura.io/ws/v3/fc313b7f...
   🤖 Telegram Bot Token: ✓ 已配置
   💬 Telegram Chat ID: ✓ 已配置
   👀 监听地址数量: 2
   📝 日志级别: INFO
   🔒 SSL验证: 禁用

🧪 测试Telegram连接...
✅ Telegram连接测试成功

🔄 按 Ctrl+C 停止监听
--------------------------------------------------
```

### Telegram 通知示例

```
🔗 新交易检测到!

📊 区块号: 0x123456
🔑 交易哈希:
0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890

📤 发送方:
0x1234567890abcdef1234567890abcdef12345678

📥 接收方:
0x9876543210fedcba9876543210fedcba98765432

💰 金额: 0.001000 ETH
⛽ Gas价格: 20.00 Gwei

🔍 在 Etherscan 上查看
```

## 开发指南

### 模块说明

- **main.py**: 应用程序入口点，负责初始化和协调各个模块
- **config.py**: 配置管理，处理环境变量加载和验证
- **address_monitor.py**: 核心监听逻辑，连接区块链网络并监听交易
- **telegram_bot.py**: Telegram 机器人功能，负责发送通知消息和处理命令
- **address_storage.py**: 地址存储管理，负责持久化监听地址数据

### 扩展功能

1. **添加新的网络支持**：修改 `config.py` 中的 WebSocket URL 配置
2. **自定义通知格式**：修改 `telegram_bot.py` 中的消息格式函数
3. **添加过滤条件**：在 `address_monitor.py` 中扩展交易过滤逻辑
4. **新增 Telegram 命令**：在 `telegram_bot.py` 中添加更多命令处理器
5. **数据备份和恢复**：扩展 `address_storage.py` 的功能
6. **交易历史记录**：添加数据库模块保存交易记录

## 故障排除

### 常见问题

1. **SSL 证书错误**

   - 设置 `SSL_VERIFY=false` 在开发环境中
   - 生产环境建议使用有效的 SSL 证书

2. **Telegram 消息发送失败**

   - 检查机器人 Token 是否正确
   - 确认聊天 ID 格式正确
   - 确保机器人有发送消息的权限

3. **WebSocket 连接失败**

   - 检查 Infura 项目 ID 是否正确
   - 确认网络连接正常
   - 验证 WebSocket URL 格式

4. **没有检测到交易**

   - 确认监听的地址格式正确
   - 检查地址是否在指定的网络上有活动
   - 验证网络选择（主网/测试网）
   - 使用 `/list_addresses` 确认地址已正确添加

5. **Telegram 命令无响应**
   - 确认机器人有接收消息的权限
   - 检查 `TELEGRAM_CHAT_ID` 是否正确
   - 确认与机器人的聊天是活跃状态
   - 查看程序日志了解具体错误

### 日志分析

程序会在控制台和 `address_monitor.log` 文件中记录详细日志：

```bash
# 查看最新日志
tail -f address_monitor.log

# 查看错误日志
grep ERROR address_monitor.log
```

## 安全注意事项

1. **保护敏感信息**

   - 不要将 `.env` 文件提交到版本控制
   - 定期更换 API 密钥
   - 使用环境变量管理敏感配置

2. **网络安全**
   - 生产环境启用 SSL 验证
   - 使用 VPN 或安全网络连接
   - 定期更新依赖包

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request 来改进此项目。

## 联系方式

如有问题或建议，请创建 Issue 或联系开发者。
