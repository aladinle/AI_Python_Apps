import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def chat_with_gpt():
    print("Welcome to AI Chatbot! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() == "exit":
            print("Bye Bye!")
            break
        answer = load_gpt_answer(user_input)
        print(f"AI: {answer}")

def load_gpt_answer(prompt):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system", "content":"You are a helpful assistant."},
            {"role":"user", "content":prompt}
        ]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    chat_with_gpt()