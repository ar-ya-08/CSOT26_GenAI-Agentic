## What I learnt this week

This week I first learnt how tool calling works, and through build 1 I learnt about the `re` module which works with regular expressions or RegEx. I used the `re.search` function to find the first occurrence of `<tool_call>` in the response to extract the tool and arguments being called. I also learnt about `re.DOTALL` which allows the `.` to also match newline characters.

I also learnt about the `(.*?)` notation, which allows us to parse for tags and the `.` allows us to match every character, the `*` allows us to match anything of any length, and the `?` allows us to stop at the first closing of the tag and the `()` is used for capturing the text. I also learnt that the `re.search` function returns a match object and we can access the captured text using `.group()`. We used the `re.sub()` function to return either an empty string if a tool was called or return the response text if no tool was called. I also learnt about the `json` module and how `json.loads()` is used to convert a string to a dictionary and how `json.dumps()` is used to convert a dictionary to a string. I learnt about the `sys` module and how we can use `sys.stderr` to print error or iteration messages.

I also learnt about OpenAI SDK’s `tools=` parameter. I learnt how to append the message with the tools called to the model and how to use the different components of the response to find out which tools are being called.

I learnt about textual and learned that if I make an API call to OpenRouter on the main thread, the entire terminal freezes for ten seconds while waiting for the internet and learned we can use `self.run_worker(self._get_response(), thread=True)` to work around this.

I also learnt that the API call to OpenRouter in Build 3 is handled by a background thread running through `self.run_worker(..., thread=True)`, and during this `_get_response` uses the async keyword. I learnt what `async` is and how it can be used for the `_get_response` function so that the rest of the programme can run while we wait for a response from the model. I learned how to use the `Horizontal()` container.

Through the textual tutorial of the stopwatch I learnt about the built in `toggle_dark` feature and added it to my agent.

The hardest and most challenging part was integrating the MCP servers. I learnt that unlike an API AlphaXiv's MCP server was locked behind a Google OAuth wall. I imported components like `FileTokenStorage` and `wait_for_callback` and `open_browser` from the `alphaxiv_search_cli.py` code. 

I noticed that the `alphaxiv_search_cli.py` code’s `streamable_http_client` outputted a read and write stream, and I saw that the `ClientSession` from lesson 3 required those read and write pipes to initialize. I learnt how to pass the authenticated pipes from the OAuth client directly to the MCP.

Through this I also learnt why we had to include the `httpx` library in our project. I learnt that the standard `requests` library is synchronous and blocks the thread. Since connecting to the MCP server requires a continuous async HTTP connection in the background the requests would freeze the terminal. I learnt how using `httpx.AsyncClient` allows the network to stay open asynchronously without locking up the Textual UI.

I merged tools by using `await session.list_tools()` to ask AlphaXiv what tools it had and then appended those to my local web tools to create an `alltools` list to send to the model. I added an if/else statement so that if the model called a tool in `TOOL_REGISTRY` it ran my python dispatch function, but if it asked for an academic tool I used `await session.call_tool()` to send it to the MCP.

## What I built and how the agent loop works

I built a terminal researchbot that works similar to Perplexity. The user types a question into a Textual TUI. The agent first initializes a session with the AlphaXiv MCP server. It finds all the tools available to it and then combines it with the webtools written in the code. The model then runs upto 8 times and allows the llm to analyse the research question given to decide whether to search the web or look up academic papers on AlphaXiv. Then the agent either searches the web using Serper, reads relevant pages and uses `trafilatura` or `markdownify` to extract clean text or queries the AlphaXiv MCP server for relevant academic papers. 

The agent loop in `run_agent` keeps calling the model in a loop. If the model returns `finish_reason == "tool_calls"`, the requested tool runs and the result is fed back into the messages list. This continues until the model returns `finish_reason == "stop"`, when it has enough information to give a final answer. The loop is capped at 8 iterations to prevent infinite loops.

## A design decision I made

I noticed that in the `agent(withmcp).py` code the function `fetch_as_markdown` was never called and so the `markdownify` module was never used. The main `smart_fetch` function only ever routed to `fetch_for_agent`, which relied entirely on `trafilatura`. Since we learnt that `trafilatura` is great for pulling clean text out of news articles but it can be overly aggressive and can remove structured data like tables or lists. I didn't want my bot to go blind just because a webpage was heavily formatted. So in the final `agent(final).py`, the `fetch_clean` function first extracts the text using `trafilatura`, but if the resulting text comes back empty or very short (less than 200 characters), it runs `markdownify` on the page to retain its structure.

After submitting my project to the grader initially I was told I could improve by "Surfacing MCP connection failures into the loop" and "consider request retries" and to implement this I added a try and except block to the `run_agent` function so that OAuth/network errors can be recovered by the model by falling back to web tools. For the request retries I added a `retry` wrapper function to the start of my code, so that if when the webtools make serper requests, they recieve an error then the retry allows the request to be made 3 times before displaying an error.

## Something that surprised me

The OAuth requirement for AlphaXiv surprised me. I assumed connecting to an MCP server would work the same way as calling an API with a key, but AlphaXiv requires a full Google login through a browser. The first time you run the agent a browser tab opens and you have to log in. Then the token gets saved to `.alphaxiv_tokens.json` for future runs. 

I was also surprised that initially the model would sometimes not call any tools at all and just answer from its training data, even for questions that clearly need a web search. I had to make the system prompt more descriptive about always searching before answering to fix this.

## What I'd improve given more time

If I had more time I would try to implement token by token streaming as right now because the agent waits for the model to complete on each iteration, there is a noticeable pause where the terminal freezes before text suddenly appears on the screen.
