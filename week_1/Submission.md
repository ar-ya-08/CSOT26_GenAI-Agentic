What I Learnt This Week:

This was my first time ever using API keys, through this task I learned that we must take security precautions so our keys don't get leaked. I learned how to use a .env file to hide my key locally and how to use .gitignore.
From the resources, I learned how LLMs work and from this task I learned what kind of structured response dictionary we get back from them. I figured out how to dig into that dictionary and pull out just the clean text message using response.choices[0].message.content.
I also learnt that APIs do not have a memory and to get around this, we need to keep reminding them about the previous chat history by saving our conversation turns into a local Python list and sending the entire history back with every prompt.

What decisions I took:

The user has two choices. First they can choose between two models (DeepSeek V4 Flash or Nvidia Nemotron). Secondly the user can pick a system prompt to give the chatbot. They can go with a default helpful assistant or type in a custom role description to change how the chatbot behaves.
I also ran into a problem where the specific free models I picked kept giving me a 404 error. To fix this, I implemented a try-except block inside the chat method. The code automatically reroutes the session to "openrouter/free" so the conversation can keep going smoothly. 
