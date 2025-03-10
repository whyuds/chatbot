# ChatBox 聊天应用

一个基于FastAPI和JavaScript的简洁聊天应用，支持Markdown渲染和代码高亮功能。

## 功能特点

- 多会话管理：创建、切换和删除对话
- Markdown支持：AI回复支持Markdown格式，包括代码块、表格等
- 代码高亮：自动识别并高亮显示代码块
- 流式响应：实时显示AI回复，提升用户体验
- 自动生成标题：根据对话内容自动生成会话标题

## 环境要求

- Python 3.7+
- Node.js (可选，用于前端开发)

## 安装配置

### 1. 克隆仓库

```bash
git clone https://github.com/whyuds/chatbox.git
cd chatbox
```

### 2. 创建虚拟环境
```bash
python -m venv venv
```

### 激活虚拟环境：
- Windows: 
```bash
.\venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖包括：
- fastapi==0.109.0
- uvicorn==0.27.0
- sqlalchemy==2.0.23
- python-dotenv==1.0.0
- langchain相关包

### 3. 配置AI模型

在`chat_model.py`中配置您的AI模型参数：

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model_name="your-model-name",
    openai_api_key="your-api-key",
    openai_api_base="your-api-base-url",
    temperature=0.7
)
```

## 启动应用

### 使用启动脚本

在Windows系统中，可以直接运行提供的批处理文件：

```bash
.\start.bat
```

该脚本会：
1. 检查Python环境
2. 安装必要的依赖
3. 初始化数据库
4. 启动后端服务器

### 手动启动

1. 初始化数据库：

```bash
python init_db.py
```

2. 启动后端服务：

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

3. 启动前端服务：
```bash
   python -m http.server 8080
```

4. 访问前端页面：
```bash
   start http://localhost:8080/frontend/
```

## 后端API接口

### 会话管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/conversations` | GET | 获取所有会话列表 |
| `/conversations` | POST | 创建新会话 |
| `/conversations/{conversation_id}` | DELETE | 删除指定会话 |
| `/conversations/{conversation_id}/title` | POST | 更新会话标题 |

### 消息管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/conversations/{conversation_id}/messages` | GET | 获取会话中的所有消息 |
| `/conversations/{conversation_id}/messages` | POST | 发送消息并获取回复 |
| `/conversations/{conversation_id}/messages/stream` | POST | 发送消息并获取流式回复 |

## 前端交互功能

### 会话管理

- 创建新会话：点击左侧边栏的"+ New Chat"按钮
- 切换会话：点击左侧边栏中的会话项
- 删除会话：点击会话项右侧的"×