import chainlit as cl  
from chainlit import on_chat_start,on_message
import sys
import os

# Add the parent directory to the path so we can import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main 

@on_chat_start
async def start_chat():
    cl.user_session.set("history", [])
    await cl.Message(
        content="Welcome to the  DACA Chatbot! How can I Guide you?").send()
    
    
@on_message
async def handle_message(message:cl.Message):
    history = cl.user_session.get("history") or []
    history.append({"role":"user", "content": message.content})
    result = await main.main(query=history)
    history.append({"role":"assistant", "content": result})
    cl.user_session.set("history", history)
    await cl.Message(
        content=str(result)
    ).send()
    