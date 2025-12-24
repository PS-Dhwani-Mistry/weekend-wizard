import asyncio
import json
import re
from typing import Dict, Any, List
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import chat
import streamlit as st

async def get_answer(user_prompt: str) -> str:
    import sys
    import os
    
    python_exe = sys.executable
    server_path = os.path.join(os.path.dirname(__file__), "server_fun.py")
    
    exit_stack = AsyncExitStack()
    try:
        stdio = await exit_stack.enter_async_context(
            stdio_client(StdioServerParameters(command=python_exe, args=[server_path]))
        )
        r_in, w_out = stdio
        session = await exit_stack.enter_async_context(ClientSession(r_in, w_out))
        await session.initialize()

        # Parse user request and call appropriate tools
        tool_results = []
        prompt_lower = user_prompt.lower()
        
        # Extract coordinates if present
        coords = re.search(r'\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)', user_prompt)
        
        # Get weather if coordinates found
        if coords or 'weather' in prompt_lower or 'temperature' in prompt_lower:
            lat = float(coords.group(1)) if coords else 40.7128
            lon = float(coords.group(2)) if coords else -74.0060
            result = await session.call_tool("get_weather", {"latitude": lat, "longitude": lon})
            weather_data = result.content[0].text if result.content else ""
            tool_results.append(f"Weather: {weather_data}")
        
        # Get books if requested
        if 'book' in prompt_lower or 'read' in prompt_lower:
            topic = "science fiction" if 'sci-fi' in prompt_lower or 'science fiction' in prompt_lower else "mystery"
            result = await session.call_tool("book_recs", {"topic": topic, "limit": 3})
            book_data = result.content[0].text if result.content else ""
            tool_results.append(f"Books: {book_data}")
        
        # Get joke if requested
        if 'joke' in prompt_lower:
            result = await session.call_tool("random_joke", {})
            joke_data = result.content[0].text if result.content else ""
            tool_results.append(f"Joke: {joke_data}")
        
        # Get dog pic if requested
        dog_url = None
        if 'dog' in prompt_lower:
            result = await session.call_tool("random_dog", {})
            dog_data = result.content[0].text if result.content else ""
            # Extract URL from JSON response
            import json
            try:
                dog_json = json.loads(dog_data)
                dog_url = dog_json.get("message", "")
                # Don't add to tool_results to avoid LLM narrative
            except:
                pass
        
        # Get trivia if requested
        if 'trivia' in prompt_lower:
            result = await session.call_tool("trivia", {})
            trivia_data = result.content[0].text if result.content else ""
            tool_results.append(f"Trivia: {trivia_data}")
        
        await exit_stack.aclose()
        
        # If only dog requested, skip LLM and just return empty text with image
        if dog_url and len(tool_results) == 0:
            return "", dog_url
        
        # Format response with single LLM call
        context = "\n".join(tool_results)
        response = chat(
            model="mistral:7b",
            messages=[
                {"role": "system", "content": "You are a friendly weekend planner. Use the provided data to create a fun, brief plan."},
                {"role": "user", "content": f"User request: {user_prompt}\n\nData available:\n{context}\n\nCreate a brief, friendly weekend plan using this data:"}
            ],
            options={"temperature": 0.7, "num_predict": 400}
        )
        
        return response["message"]["content"], dog_url
        
    except Exception as e:
        await exit_stack.aclose()
        raise
        
    return "Something went wrong!", None

# Streamlit UI
st.set_page_config(page_title="Weekend Wizard", page_icon="🎉")
st.title("🎉 Weekend Wizard")
st.markdown("Ask me to plan your weekend! I can check weather, suggest books, tell jokes, show dog pics, and trivia.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What should I do this weekend?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response, dog_url = asyncio.run(get_answer(prompt))
                
                # Show text response if available
                if response.strip():
                    st.markdown(response)
                
                # Display dog image if available
                if dog_url:
                    st.image(dog_url, caption="Here's a cute dog for you! 🐕", width='stretch')
                
                # Store in history
                msg = response if response.strip() else "🐕 [Dog picture]"
                st.session_state.messages.append({"role": "assistant", "content": msg})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Sidebar with examples
with st.sidebar:
    st.header("Example Prompts")
    if st.button("Plan Saturday in NYC"):
        st.session_state.example = "Plan a cozy Saturday in NYC at (40.7128, -74.0060) with mystery books and a joke"
    if st.button("Tell me a joke"):
        st.session_state.example = "Tell me a joke"
    if st.button("Weather in SF"):
        st.session_state.example = "What's the weather at (37.7749, -122.4194)?"
    if st.button("Random dog pic"):
        st.session_state.example = "Give me a random dog picture"
    if st.button("Trivia question"):
        st.session_state.example = "Show me a trivia question"
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
