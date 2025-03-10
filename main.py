from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, AsyncGenerator
import models
from chat_model import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from fastapi.responses import StreamingResponse
import json
import asyncio

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ConversationCreate(BaseModel):
    title: str

class MessageCreate(BaseModel):
    content: str

class HTTPErrorResponse(BaseModel):
    detail: str
    error_code: int

@app.post("/conversations",
          tags=["Conversations"],
          summary="Create new conversation",
          response_model=dict,
          responses={
              201: {"description": "Conversation created successfully"},
              400: {"model": HTTPErrorResponse, "description": "Invalid request"}
          })
def create_conversation(conv: ConversationCreate, db: Session = Depends(get_db)):
    db_conv = models.Conversation(title=conv.title)
    db.add(db_conv)
    db.commit()
    db.refresh(db_conv)
    return {"id": db_conv.id, "title": db_conv.title}

@app.delete("/conversations/{conversation_id}",
             tags=["Conversations"],
             summary="Delete conversation",
             responses={
                 200: {"description": "Conversation deleted successfully"},
                 404: {"model": HTTPErrorResponse, "description": "Conversation not found"}
             })
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    db_conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not db_conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(db_conv)
    db.commit()
    return {"status": "success"}

@app.get("/conversations",
            tags=["Conversations"],
            summary="List all conversations",
            response_model=List[dict],
            responses={
                200: {"description": "List of conversations"}
            })
def get_conversations(db: Session = Depends(get_db)):
    conversations = db.query(models.Conversation).order_by(models.Conversation.updated_at.desc()).all()
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at} for c in conversations]

@app.get("/conversations/{conversation_id}/messages",
            tags=["Messages"],
            summary="Get conversation messages",
            response_model=List[dict],
            responses={
                200: {"description": "List of messages"},
                404: {"model": HTTPErrorResponse, "description": "Conversation not found"}
            })
def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()
    
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

@app.post("/conversations/{conversation_id}/messages",
             tags=["Messages"],
             summary="Send message",
             response_model=dict,
             responses={
                 201: {"description": "Message processed successfully"},
                 404: {"model": HTTPErrorResponse, "description": "Conversation not found"}
             })
def chat_message(conversation_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    # Save user message
    user_msg = models.Message(
        conversation_id=conversation_id,
        role="user",
        content=message.content
    )
    db.add(user_msg)
    
    # Get conversation history
    history = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()
    
    # Build prompt with history
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You're a helpful assistant"),
        *[(msg.role, msg.content) for msg in history],
        ("user", "{input}")
    ])
    
    # Generate response
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"input": message.content})
    
    # Save assistant response
    assistant_msg = models.Message(
        conversation_id=conversation_id,
        role="assistant",
        content=response
    )
    db.add(assistant_msg)
    db.commit()
    
    return {"role": "assistant", "content": response}

@app.post("/conversations/{conversation_id}/messages/stream",
             tags=["Messages"],
             summary="Send message with streaming response",
             responses={
                 200: {"description": "Streaming response started"},
                 404: {"model": HTTPErrorResponse, "description": "Conversation not found"}
             })
async def stream_chat_message(conversation_id: int, message: MessageCreate, db: Session = Depends(get_db)):
    # Save user message
    user_msg = models.Message(
        conversation_id=conversation_id,
        role="user",
        content=message.content
    )
    db.add(user_msg)
    db.commit()
    
    # 检查是否是第一条消息，如果是则在响应完成后更新标题
    is_first_message = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).count() == 1
    
    # Get conversation history
    history = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()
    
    # Build prompt with history
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You're a helpful assistant"),
        *[(msg.role, msg.content) for msg in history],
        ("user", "{input}")
    ])
    
    # 创建流式响应
    async def generate_stream() -> AsyncGenerator[str, None]:
        full_response = ""
        
        # 使用LangChain的流式输出
        chain = prompt | llm | StrOutputParser()
        
        async for chunk in chain.astream({"input": message.content}):
            full_response += chunk
            # 添加 ensure_ascii=False 禁用ASCII转码
            yield json.dumps({"chunk": chunk, "done": False}, ensure_ascii=False) + "\n"
        
        # 保存完整的助手回复
        assistant_msg = models.Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response
        )
        db.add(assistant_msg)
        db.commit()
        
        # 如果是第一条消息，生成并更新标题
        if is_first_message:
            # 异步更新标题，不阻塞当前响应
            asyncio.create_task(update_conversation_title(conversation_id, message.content, full_response))
        
        # 同样需要修改完成标记的编码
        yield json.dumps({"chunk": "", "done": True}, ensure_ascii=False) + "\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson"
    )

# 添加更新对话标题的API
@app.post("/conversations/{conversation_id}/title",
          tags=["Conversations"],
          summary="Update conversation title",
          response_model=dict,
          responses={
              200: {"description": "Title updated successfully"},
              404: {"model": HTTPErrorResponse, "description": "Conversation not found"}
          })
def update_title(conversation_id: int, title_data: dict, db: Session = Depends(get_db)):
    db_conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not db_conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db_conv.title = title_data.get("title")
    db.commit()
    db.refresh(db_conv)
    
    return {"id": db_conv.id, "title": db_conv.title}

# 添加自动生成标题的异步函数
async def update_conversation_title(conversation_id: int, user_message: str, assistant_response: str):
    # 创建一个新的数据库会话
    db = models.SessionLocal()
    try:
        # 构建生成标题的提示
        title_prompt = ChatPromptTemplate.from_messages([
            ("system", "根据用户的问题和助手的回答，生成一个简短、具体的对话标题（不超过20个字）。只返回标题文本，不要有任何其他内容。"),
            ("user", f"用户问题: {user_message}\n\n助手回答: {assistant_response}")
        ])
        
        # 生成标题
        title_chain = title_prompt | llm | StrOutputParser()
        title = await title_chain.ainvoke({})
        
        # 清理标题（去除引号、多余空格等）
        title = title.strip().strip('"\'').strip()
        
        # 如果标题为空或过长，使用用户消息的前20个字符
        if not title or len(title) > 30:
            title = user_message[:20] + ("..." if len(user_message) > 20 else "")
        
        # 更新数据库中的标题
        db_conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if db_conv:
            db_conv.title = title
            db.commit()
    except Exception as e:
        print(f"Error updating conversation title: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)