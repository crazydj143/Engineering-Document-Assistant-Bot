import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = None
if GROQ_API_KEY and GROQ_API_KEY != "xxxxx":
    client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
else:
    client = OpenAI(
        api_key="mock_key",
        base_url="https://api.groq.com/openai/v1"
    )

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "deepseek-r1-distill-llama-70b"
OLLAMA_MODEL = "Qwen/Qwen3-4B-Instruct-GGUF"

def test_groq_connection() -> bool:
    """
    Tests connection to Groq API and prints model status.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "xxxxx":
        print("Model Name: N/A")
        print("API Status: OFFLINE (Key not configured)")
        return False

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5
        )
        print(f"Model Name: {DEFAULT_MODEL}")
        print("API Status: ONLINE")
        return True
    except Exception as e:
        print(f"[groq_client] Default model {DEFAULT_MODEL} failed: {e}. Trying fallback deepseek-r1...")
        try:
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            print(f"Model Name: {FALLBACK_MODEL}")
            print("API Status: ONLINE (Fallback)")
            return True
        except Exception as fallback_err:
            print(f"[groq_client] Fallback model {FALLBACK_MODEL} failed: {fallback_err}")
            print("Model Name: N/A")
            print("API Status: OFFLINE")
            return False

test_groq_connection()

def generate_ollama_response(system_prompt: str, user_prompt: str) -> str:
    """
    Calls local Ollama API as failover option when Groq is offline.
    """
    import requests
    try:
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.2}
        }
        print(f"[groq_client] Using local Ollama failover with model: {OLLAMA_MODEL}")
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("message", {}).get("content", "")
        else:
            return f"Error: Local Ollama failover returned status code {response.status_code}: {response.text}"
    except Exception as e:
        print(f"[groq_client] Local Ollama connection failed: {e}")
        return f"Error: Local Ollama failover failed: {str(e)}"

def generate_ollama_response_stream(system_prompt: str, user_prompt: str):
    """
    Streams response from local Ollama API as failover option when Groq is offline.
    """
    import json
    import requests
    try:
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True,
            "options": {"temperature": 0.2}
        }
        print(f"[groq_client] Streaming local Ollama failover with model: {OLLAMA_MODEL}")
        response = requests.post(url, json=payload, stream=True, timeout=30)
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                yield data.get("message", {}).get("content", "")
    except Exception as e:
        print(f"[groq_client] Local Ollama streaming connection failed: {e}")
        yield f"\n[Error: Local Ollama failover streaming failed: {str(e)}]"

def generate_groq_response(system_prompt: str, user_prompt: str) -> str:
    """
    Generates chat response using Groq, falling back to deepseek-r1, and then local Ollama.
    """
    if GROQ_API_KEY and GROQ_API_KEY != "xxxxx":
        try:
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[groq_client] Default model {DEFAULT_MODEL} failed: {e}. Trying fallback deepseek-r1...")
            try:
                response = client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                return response.choices[0].message.content
            except Exception as fallback_err:
                print(f"[groq_client] Fallback model {FALLBACK_MODEL} failed: {fallback_err}. Routing to Ollama failover...")

    return generate_ollama_response(system_prompt, user_prompt)

def generate_groq_response_stream(system_prompt: str, user_prompt: str):
    """
    Generates streaming response using Groq, falling back to deepseek-r1, and then local Ollama.
    """
    if GROQ_API_KEY and GROQ_API_KEY != "xxxxx":
        try:
            response_stream = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                stream=True
            )
            for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            print(f"[groq_client] Default streaming model {DEFAULT_MODEL} failed: {e}. Trying fallback deepseek-r1...")
            try:
                response_stream = client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    stream=True
                )
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as fallback_err:
                print(f"[groq_client] Fallback streaming model {FALLBACK_MODEL} failed: {fallback_err}. Routing to Ollama failover...")

    for token in generate_ollama_response_stream(system_prompt, user_prompt):
        yield token
