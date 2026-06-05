import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client=OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

def callmodel(prompt:str)->str:

    response=client.chat.completions.create(
        model="openrouter/free",
        messages=[ 
            {"role":"user", "content":prompt}
        ],
    )
    print("--------- raw data --------")
    print(response)
    print("---------------------------")

    return response.choices[0].message.content

if __name__=="__main__":
    print(callmodel("Whats the capital of austraila?"))
    print(callmodel("my name is arya"))
