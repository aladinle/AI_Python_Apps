# test chatbot.py
from chatbot import load_gpt_answer
import openai

def test_chat_with_gpt_mock(mocker):
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = "Hello! How can I help you?"
    
    # Patch the OpenAI API call
    mocker.patch.object(openai.ChatCompletion, "create", return_value=mock_response)
    
    result = load_gpt_answer("Hello AI!")
    assert result == "Hello! How can I assist you today?"