import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client=OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def runchatbot():

    messages=[{ 
        "role":"system", "content":"you are a helpful assistant"
    }
    ]

    lastuse=None

    print("chat started.")
    print("type 'exit' to quit.")
    print("type '/reset' to clear history.")
    print("type '/tokens' to view token usage.")

    while True:
        userinput=input("user: ")
        
        if userinput.lower()=="exit":
            print("Goodbye!")
            break
        
        if userinput=='/reset':
            messages=[{ "role":"system", "content":"you are a helpful assistant"}]
            lastuse=None
            print("system: the model has forgotten everything")
            continue

        if userinput=='/tokens':
            if lastuse is None:
                print("no API calls have been made yet")
            else:
                print("-----TOKENS USAGE-----")
                print(f"prompt tokens: {lastuse.prompt_tokens}")
                print(f"completion tokens: {lastuse.completion_tokens}")
                print(f"total tokens: {lastuse.total_tokens}")
                print("----------------------")
            continue


        messages.append({"role":"user", "content":userinput})

        response=client.chat.completions.create(
        model="openrouter/free",
        messages=messages
     )
        lastuse=response.usage
        
        reply= response.choices[0].message.content

        messages.append({"role":"assistant", "content":reply})
        
        print(f"model: {reply}")


if __name__=="__main__":
    runchatbot()
