---
name: mcp-builder
description: 构建 MCP（模型上下文协议）服务器，为 Claude 提供新能力。适用于用户希望创建 MCP 服务器、为 Claude 添加工具或集成外部服务时。
---

# MCP 服务器构建技能

你现在具备构建 MCP（Model Context Protocol，模型上下文协议）服务器的专业能力。MCP 使 Claude 能够通过标准化协议与外部服务交互。

## 什么是 MCP？

MCP 服务器会公开：
- **工具**：Claude 可以调用的函数（类似 API 端点）
- **资源**：Claude 可以读取的数据（例如文件或数据库记录）
- **提示词**：预先构建的提示词模板

## 快速开始：Python MCP 服务器

### 1. 项目设置

```bash
# 创建项目
mkdir my-mcp-server && cd my-mcp-server
python3 -m venv venv && source venv/bin/activate

# 安装 MCP SDK
pip install mcp
```

### 2. 基础服务器模板

```python
#!/usr/bin/env python3
"""my_server.py——一个简单的 MCP 服务器"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 创建服务器实例
server = Server("my-server")

# 定义工具
@server.tool()
async def hello(name: str) -> str:
    """向某人问好。

    参数：
        name: 要问候的姓名
    """
    return f"Hello, {name}!"

@server.tool()
async def add_numbers(a: int, b: int) -> str:
    """将两个数相加。

    参数：
        a: 第一个数
        b: 第二个数
    """
    return str(a + b)

# 运行服务器
async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### 3. 注册到 Claude

添加到 `~/.claude/mcp.json`：
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python3",
      "args": ["/path/to/my_server.py"]
    }
  }
}
```

## TypeScript MCP 服务器

### 1. 设置

```bash
mkdir my-mcp-server && cd my-mcp-server
npm init -y
npm install @modelcontextprotocol/sdk
```

### 2. 模板

```typescript
// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "my-server",
  version: "1.0.0",
});

// 定义工具
server.setRequestHandler("tools/list", async () => ({
  tools: [
    {
      name: "hello",
      description: "向某人问好",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "要问候的姓名" },
        },
        required: ["name"],
      },
    },
  ],
}));

server.setRequestHandler("tools/call", async (request) => {
  if (request.params.name === "hello") {
    const name = request.params.arguments.name;
    return { content: [{ type: "text", text: `Hello, ${name}!` }] };
  }
  throw new Error("未知工具");
});

// 启动服务器
const transport = new StdioServerTransport();
server.connect(transport);
```

## 高级模式

### 外部 API 集成

```python
import httpx
from mcp.server import Server

server = Server("weather-server")

@server.tool()
async def get_weather(city: str) -> str:
    """获取某个城市的当前天气。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.weatherapi.com/v1/current.json",
            params={"key": "YOUR_API_KEY", "q": city}
        )
        data = resp.json()
        return f"{city}: {data['current']['temp_c']}C, {data['current']['condition']['text']}"
```

### 数据库访问

```python
import sqlite3
from mcp.server import Server

server = Server("db-server")

@server.tool()
async def query_db(sql: str) -> str:
    """执行只读 SQL 查询。"""
    if not sql.strip().upper().startswith("SELECT"):
        return "错误：只允许 SELECT 查询"

    conn = sqlite3.connect("data.db")
    cursor = conn.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    return str(rows)
```

### 资源（只读数据）

```python
@server.resource("config://settings")
async def get_settings() -> str:
    """应用程序设置。"""
    return open("settings.json").read()

@server.resource("file://{path}")
async def read_file(path: str) -> str:
    """从工作区读取文件。"""
    return open(path).read()
```

## 测试

```bash
# 使用 MCP Inspector 测试
npx @anthropics/mcp-inspector python3 my_server.py

# 或直接发送测试消息
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 my_server.py
```

## 最佳实践

1. **清晰的工具描述**：Claude 使用这些描述来决定何时调用工具
2. **输入验证**：始终验证并清理输入
3. **错误处理**：返回有意义的错误消息
4. **默认使用异步**：对 I/O 操作使用 async/await
5. **安全性**：绝不要在没有身份认证的情况下公开敏感操作
6. **幂等性**：工具应当可以安全重试
