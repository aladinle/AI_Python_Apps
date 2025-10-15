import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def chat_with_gpt(prompt):    
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
            messages=[
                {"role":"system", "content":"You are a helpful assistant."},
                {"role":"user", "content":prompt}
            ]
        )
    answer = response.choices[0].message.content
    return answer

if __name__ == "__main__":
    print("Welcome to AI Chatbot! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() == "exit":
            print("Bye Bye!")
            break
        print(f"AI: {chat_with_gpt(user_input)}")