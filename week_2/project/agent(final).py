"""
ResearchBot: Week 2 Project Starter
======================================
This file currently makes a basic single-turn call to OpenRouter.
Your job is to evolve it into a full research agent with:
  - Web search and web fetch tools (using OpenAI SDK tool calling)
  - An agent loop that iterates until the model stops requesting tools
  - A Textual TUI with a chat panel and a tool activity log
  - Keyboard shortcuts: Ctrl+L (clear display), Ctrl+K (clear history), Ctrl+Q (quit),
    and at least one more of your choice

Start by getting this file working, then add tools, then add the TUI.
Don't try to build everything at once.
"""
import os
import requests
import trafilatura
import markdownify
import json
import httpx
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientMetadata
from mcp.client.streamable_http import streamable_http_client
from alphaxiv_search_cli import FileTokenStorage, open_browser, wait_for_callback
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Horizontal
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "openrouter/free"
MAX_ITERATIONS = 8
MAX_CHARS = 8000
MAX_HISTORY_TURNS = 20
ALPHAXIV_MCP_URL = "https://api.alphaxiv.org/mcp/v1"
REDIRECT_URI = "http://localhost:8765/callback"

#webtools

def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web. Returns a list of {title, link, snippet} dicts."""
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": os.environ["SERPER_API_KEY"], "Content-Type": "application/json"},
        json={"q": query, "num": num_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })
    return results

def web_fetch(url: str) -> str:
    """Fetch the content of a URL and return it as text."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
    response.raise_for_status()
    return response.text

def fetch_clean(url: str) -> str:
    html = web_fetch(url)
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    if not text or len(text.strip()) < 200:
            md = markdownify.markdownify(html, heading_style="ATX", strip=["script", "style", "nav", "footer"])
            import re
            text = re.sub(r'\n{3,}', '\n\n', md).strip()
    return text or ""

def fetch_for_agent(url: str) -> str:
    content = fetch_clean(url)
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "\n\n[...truncated]"
    return content

def smart_fetch(url: str) -> str:
    from urllib.parse import urlparse
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    try:
        resp = requests.get(f"{base}/llms.txt", timeout=5)
        if resp.status_code == 200:
            return f"[llms.txt found]\n\n{resp.text}\n\n---\nOriginal URL: {url}"
    except Exception:
        pass

    return fetch_for_agent(url)

#standard tool declarations

search_tool = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use this when the user asks "
            "about recent events, specific facts, or anything you are uncertain about. "
            "Returns a list of search results with titles, URLs, and snippets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and targeted.",
                }
            },
            "required": ["query"],
        },
    },
}

fetch_tool = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": (
            "Fetch and read the full content of a web page. Use this after web_search "
            "to read a specific result in detail. Prefer this for documentation, articles, "
            "and pages where the snippet is not enough."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch, including https://",
                }
            },
            "required": ["url"],
        },
    },
}

TOOLS = [search_tool, fetch_tool]

#dispatcher

TOOL_REGISTRY = {
    "web_search": web_search,
    "web_fetch": smart_fetch,
}

def dispatch(tool_call) -> str:
    name=tool_call.function.name
    argsstring=tool_call.function.arguments
    
    try:
        args=json.loads(argsstring)
    except Exception as e:
        return json.dumps({"error": str(e)})
    
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": f"unknown tool: {name}"})
    
    try:
        tool=TOOL_REGISTRY[name]
        res=tool(**args)
        return json.dumps(res)
    except Exception as e:
        return json.dumps({"error": str(e)})

#agent loop (with mcp)

async def run_agent(history: list[dict], log_tool) -> str:
    log_tool("[system] verifying alphaxiv credentials... ")

    storage= FileTokenStorage()

    if not storage.tokens:
        log_tool("[red]action required:[/red] log in to AlphaXiv on your browser to continue")

    auth = OAuthClientProvider(
        server_url=ALPHAXIV_MCP_URL,
        client_metadata=OAuthClientMetadata(
            client_name="AlphaXiv Search CLI",
            redirect_uris=[REDIRECT_URI],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="read",
        ),
        storage=storage,
        redirect_handler=open_browser,
        callback_handler=wait_for_callback,
    )
    
    async with httpx.AsyncClient(auth=auth, follow_redirects=True, timeout=60) as http:
            async with streamable_http_client(ALPHAXIV_MCP_URL, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    log_tool("[System] Successfully authenticated with AlphaXiv MCP Server.")

                    mcp_tools = await session.list_tools()
                    
                    alltools = list(TOOLS)
                    for tool in mcp_tools.tools:
                        alltools.append({
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.inputSchema,
                            },
                        })

                    for _ in range(MAX_ITERATIONS):
                        response = client.chat.completions.create(
                            model=MODEL,
                            messages=history,
                            tools=alltools,
                        )
                        message = response.choices[0].message
                        finish_reason = response.choices[0].finish_reason

                        if finish_reason == "tool_calls":

                            history.append(message)
                            
                            for tool in message.tool_calls:
                                log_tool(f"[Tool Call] Running {tool.function.name} with args: {tool.function.arguments}")
                                if tool.function.name in TOOL_REGISTRY:
                                    r=dispatch(tool)
                                else:
                                    try:
                                        args = json.loads(tool.function.arguments)
                                        mcp_result = await session.call_tool(tool.function.name, args)
                                        r = mcp_result.content[0].text if mcp_result.content else ""
                                    except Exception as e:
                                        r = json.dumps({"error": str(e)})

                                history.append({
                                    "role": "tool",
                                    "tool_call_id": tool.id,
                                    "content": r
                                })

                        elif finish_reason== "stop":
                            return message.content

                    return f"[Agent stopped after {MAX_ITERATIONS} iterations without a final answer]"

def trim_history(messages: list[dict], max_turns: int) -> list[dict]:
    n=max_turns*2

    if len(messages)-1>n:
        return [messages[0]]+messages[-n:]
    
    return messages

# TUI

class ResearchApp(App):

    TITLE = "Week 2 Researchbot TUI"
    CSS = """
    Screen {
        layout: vertical;
    }

    Horizontal {
        height: 1fr;
    }

    #chat {
        width: 60%;
        border: solid $primary;
        padding: 0 1;
    }

    #tools {
        width: 40%;
        border: solid $warning;
        padding: 0 1;
    }

    Input {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display"),
        Binding("ctrl+k", "clear_history", "Clear history"),
        Binding("ctrl+t", "toggle_dark", "Toggle Dark Mode"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.messages: list[dict] = [
            {"role": "system", "content": "You are a helpful research assistant. You have access to AlphaXiv tools to search for and read academic papers if required. You may search the web for general facts."}
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RichLog(id="chat", wrap=True, markup=True, highlight=True)
            yield RichLog(id="tools", wrap=True, markup=True, highlight=True)
        yield Input(placeholder="Research question: ")
        yield Footer()

    def on_mount(self) -> None:
        chat = self.query_one("#chat", RichLog)
        tools= self.query_one("#tools", RichLog)
            
        chat.write("[bold green]Chat started.[/bold green] Ctrl+Q to quit, Ctrl+L to clear.\n")
        tools.write("[yellow]Tool Log:[/yellow]\n")
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.clear()

        chat = self.query_one("#chat", RichLog)
        chat.write(f"[bold cyan][You][/bold cyan] {user_text}\n")

        self.messages.append({"role": "user", "content": user_text})
        self.messages = trim_history(self.messages, MAX_HISTORY_TURNS)

        self.run_worker(self._get_response(), thread=True)

    async def _get_response(self) -> None:
        chat = self.query_one("#chat", RichLog)
        tool_log = self.query_one("#tools", RichLog)

        def log_tool(txt):
            self.call_from_thread(tool_log.write, f"[yellow]{txt}[/yellow]\n")

        try:
            r= await run_agent(self.messages, log_tool)

            self.messages.append({"role": "assistant", "content": r})

            self.call_from_thread(chat.write, f"[green][Agent][/green] {r}\n")

        except Exception as e:
            self.call_from_thread(chat.write, f"[red]Error[/red] {str(e)}\n")

    def action_clear_display(self) -> None:
        self.query_one("#chat", RichLog).clear()
        self.query_one("#tools", RichLog).clear()

    def action_clear_history(self) -> None:
        self.messages=[self.messages[0]]
        self.query_one("#chat", RichLog).clear()
        self.query_one("#chat", RichLog).write("[yellow]History cleared.[/yellow]")
        self.query_one("#tools", RichLog).clear()


if __name__ == "__main__":
    ResearchApp().run()