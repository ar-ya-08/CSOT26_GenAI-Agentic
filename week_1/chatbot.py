import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ChatAgent:
    def __init__(self, modelname:str, systemprompt: str = "You are a helpful assistant.", maxtokens: int=75000):
        self.client=OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            )
        self.modelname=modelname
        self.systemprompt = systemprompt
        self.maxtokens=maxtokens
        self.history=[]

    def summarise(self):
        self.history.append({"role": "user", "content": "summarise the conversation so far into a short concise paragraph to yourself."})
        s = [{"role": "system", "content": self.systemprompt}] + self.history
        response = self.client.chat.completions.create(
            model=self.modelname,
            messages=s
        )
        summary = response.choices[0].message.content
        self.history = [
            {"role": "assistant", "content": f"Summary of past conversation: {summary}"}
        ]
        print("Token limit exceeded, conversation has been summarised.")

    def chat(self, userprompt: str)->str:
        self.history.append({"role": "user", "content": userprompt})

        s=[{"role": "system", "content": self.systemprompt}] + self.history
        try:
            response = self.client.chat.completions.create(
                model=self.modelname,
                messages=s
            )
        except Exception as e:
            print(f"selected model: {self.modelname} is unreachable. Rerouting to openrouter/free")
            self.modelname = "openrouter/free"
            
            response = self.client.chat.completions.create(
                model=self.modelname,
                messages=s
                )

        r=response.choices[0].message.content

        self.history.append({"role": "assistant", "content": r})

        if response.usage.total_tokens >= self.maxtokens:
            self.summarise()

        return r
        
    def reset(self):
        self.history = []
        print("Conversation history cleared.")

def main():
    print("----Welcome to the GenAI chatbot----")

    print("Select a model to use:")
    print("1. Deepseek V4 Flash (free)")
    print("2. Nvidia Nemotron Super 49B (free)")

    choice=input("Enter choice 1 or 2: ").strip()
    if choice=="1":
        selectedmodel="deepseek/deepseek-v4-flash:free"
    else: 
        selectedmodel="nvidia/nemotron-3-super-49b-a12b:free"

    print("what role would you like this chatbot to play?")
    print("1. Helpful assistant")
    print("2. Custom")
    role=input("enter 1 or 2: ")
    
    if role=="1":
        systemprompt="You are a helpful assistant."
    else:
        systemprompt=input("Describe your role: ").strip()

    agent=ChatAgent(modelname=selectedmodel, systemprompt=systemprompt)
    
    print(f"Chat session active using {selectedmodel}. Type 'exit' to quit session, '/reset' to clear history.")

    while True:
        userinput=input("user: ").strip()

        if userinput.lower()=="exit":
            print("Goodbye!")
            break

        if not userinput:
            continue

        if userinput=="/reset":
            agent.reset()
            continue

        reply=agent.chat(userinput)
        print(f"model: {reply}")

if __name__=="__main__":
    main()
