# 🎉 Weekend Wizard

AI agent that plans your weekend using MCP, Ollama, and 5 free APIs (no keys needed).

## Features

✅ Weather • Books • Jokes • Dog Photos • Trivia

## Quick Start

```bash
# 1. Install dependencies
pip install "mcp>=1.2" requests ollama streamlit

# 2. Get Ollama model
ollama pull mistral:7b

# 3. Run
streamlit run ui.py
```

Open http://localhost:8501

## Example Prompts

- `Plan Saturday in NYC at (40.7128, -74.0060) with sci-fi books`
- `What's the weather at (37.7749, -122.4194)?`
- `Show me a random dog picture`
- `Tell me a joke`

## Architecture

```
Streamlit UI → Agent (ui.py) → MCP Server (server_fun.py) → 5 Free APIs
                                        ↓
                                 Ollama (mistral:7b)
```

## Files

- `server_fun.py` - MCP tools server
- `agent_fun.py` - CLI version  
- `ui.py` - Web interface

## APIs Used (Free)

1. Open-Meteo - Weather
2. Open Library - Books
3. JokeAPI - Jokes
4. Dog CEO - Dog photos
5. Open Trivia DB - Trivia

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com)
- Internet connection

---

**Happy weekend planning! 🎉**
