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

def fetch_as_markdown(url: str) -> str:
    html = web_fetch(url)
    md = markdownify(html, heading_style="ATX", strip=["script", "style", "nav", "footer"])
    import re
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    return md

def fetch_clean(url: str) -> str:
    html = web_fetch(url)
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
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
    """
    Execute a single tool_call object from the API response.

    tool_call has:
        tool_call.function.name       (the tool name)
        tool_call.function.arguments  (a JSON string of arguments)

    Return a JSON string of the result dict.
    On unknown tool or exception, return a JSON error dict.

    Note: tool_call.function.arguments is a *string*, not a dict. Parse it first.
    """
    # TODO: implement
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

    pass

#agent loop

def run_agent(history: list[dict], log_tool) -> str:
    """
    Run the agent loop using native SDK tool calling.

    Steps:
      1. Append the user message to history.
      2. Call client.chat.completions.create() with tools=TOOLS.
      3. If response.choices[0].finish_reason == "tool_calls":
           a. Append the assistant message (it contains .tool_calls) to history.
           b. For each tool_call in message.tool_calls:
                - dispatch it
                - append a {"role": "tool", "tool_call_id": ..., "content": ...} message
           c. Go to 2.
      4. If finish_reason == "stop": return message.content.
      5. If MAX_ITERATIONS reached: return an error string.

    Print to stderr whenever a tool executes so you can follow the loop.

    Hint: the assistant message you append in step 3a must be the raw message object,
    not a dict. The SDK accepts both, but keep it consistent with what the API returned.
    """
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=history,
            tools=TOOLS,
        )
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # TODO: handle finish_reason == "tool_calls"
        # TODO: handle finish_reason == "stop"

        if finish_reason == "tool_calls":

            history.append(message)

            for tool in message.tool_calls:
                log_tool(f"[Tool Call] Running {tool.function.name} with args: {tool.function.arguments}")
                r=dispatch(tool)
                history.append({
                    "role": "tool",
                    "tool_call_id": tool.id,
                    "content": r
                })

        elif finish_reason== "stop":
            return message.content

        pass

    return f"[Agent stopped after {MAX_ITERATIONS} iterations without a final answer]"

def trim_history(messages: list[dict], max_turns: int) -> list[dict]:
    """
    Keep the system message and only the last `max_turns` user/assistant pairs.

    messages[0] is assumed to be the system message.
    Drop oldest pairs from messages[1:] when over the limit.
    A 'pair' is one user message + one assistant message = 2 entries.
    """
    # TODO: implement
    n=max_turns*2

    if len(messages)-1>n:
        return [messages[0]]+messages[-n:]
    
    return messages
    pass

# TUI

class ResearchApp(App):
    """A full-screen terminal chatbot."""

    TITLE = "Week 2 Researchbot TUI"
    CSS = """
    Screen {
        layout: vertical;
    }

    Horizontal {
        height: 1fr;
    }

    #chat {
        width: 65%;
        border: solid $primary;
        padding: 0 1;
    }

    #tools {
        width: 35%;
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
            {"role": "system", "content": "You are a helpful assistant."}
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

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Called when the user presses Enter."""
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.clear()

        chat = self.query_one("#chat", RichLog)
        chat.write(f"[bold cyan][You][/bold cyan] {user_text}\n")

        # Append user message to history
        self.messages.append({"role": "user", "content": user_text})
        self.messages = trim_history(self.messages, MAX_HISTORY_TURNS)

        # Run the API call in a background thread so the UI stays responsive
        # TODO: call self.run_worker(self._get_response(), thread=True)
        self.run_worker(self._get_response(), thread=True)
        pass

    async def _get_response(self) -> None:
        """
        Fetch the model response and update the UI.
        This runs in a background thread (called via run_worker).

        Steps:
          1. Call call_model(self.messages)  [blocking, OK in a thread]
          2. Append the assistant reply to self.messages
          3. Use self.call_from_thread(log.write, ...) to update the UI safely

        Handle exceptions: if call_model raises, display an error in the log.
        """
        chat = self.query_one("#chat", RichLog)
        tool_log = self.query_one("#tools", RichLog)

        def log_tool(txt):
            self.call_from_thread(tool_log.write, f"[yellow]{txt}[/yellow]\n")

        # TODO: implement
        try:
            r=run_agent(self.messages, log_tool)

            self.messages.append({"role": "assistant", "content": r})

            self.call_from_thread(chat.write, f"[green][Agent][/green] {r}\n")

        except Exception as e:
            self.call_from_thread(chat.write, f"[red]Error[/red] {str(e)}\n")
        pass

    # -----------------------------------------------------------------------
    # Actions (bound to keyboard shortcuts)
    # -----------------------------------------------------------------------

    def action_clear_display(self) -> None:
        """Clear the visible log without touching conversation history."""
        # TODO: implement
        self.query_one("#chat", RichLog).clear()
        self.query_one("#tools", RichLog).clear()
        pass

    def action_clear_history(self) -> None:
        """Reset conversation history and clear the display."""
        # TODO: reset self.messages to just the system message
        self.messages=[self.messages[0]]
        # TODO: clear the display
        self.query_one("#chat", RichLog).clear()
        # TODO: write a "History cleared." notice to the log
        self.query_one("#chat", RichLog).write("[yellow]History cleared.[/yellow]")
        pass


if __name__ == "__main__":
    ResearchApp().run()