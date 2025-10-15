# test_chatbot.py
from chatbot import chat_with_gpt
import openai

def test_chat_with_gpt_mock(mocker):
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = "Hello! How can I assist you today?"
    
    mocker.patch("openai.chat.completions.create", return_value=mock_response)
    
    result = chat_with_gpt("Hello AI!")
    assert result == "Hello! How can I assist you today?"
