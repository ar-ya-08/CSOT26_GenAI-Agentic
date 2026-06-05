import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ChatAgent:
    def __init__(self, modelname:str, maxturns: int):
        self.client=OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            )
        self.modelname=modelname
        self.maxturns=maxturns
        self.history=[]
        pass

    def chat(self, userprompt: str)->str:
        self.history.append({"role": "user", "content": userprompt})

        s=[{"role": "system", "content": "you are a helpful assistant"}] + self.history

        response = self.client.chat.completions.create(
            model=self.modelname,
            messages=s
        )

        r=response.choices[0].message.content

        self.history.append({"role": "assistant", "content": r})
        
        return r


def main():
    print("----Welcome to the GenAI chatbot----")

    print("Select a model to use:")
    print("1. Deepseek flash v4 (free)")
    print("2. Google Gemma 29B (free)")

    choice=input("Enter choice 1 or 2: ").strip()
    if choice=="1":
        selectedmodel="deepseek/deepseek-v4-flash:free"
    else: 
        selectedmodel="google/gemma-2-9b-it:free"

    agent=ChatAgent(modelname=selectedmodel, maxturns=3)
    print(f"\nChat session active using {selectedmodel}. Type 'exit' to quit session.")

    while True:
        userinput=input("user: ").strip()

        if userinput.lower()=="exit":
            print("Goodbye!")
            break

        reply=agent.chat(userinput)
        print(f"model: {reply}")



if __name__=="__main__":
    main()
