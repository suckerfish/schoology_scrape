import google.generativeai as genai
import os
from absl import logging

logging.set_verbosity(logging.ERROR)


class Gemini:
    def __init__(self):
        self.api_key = os.getenv('gemini_key')
        genai.configure(api_key=self.api_key)
        self.llm_model = genai.GenerativeModel('gemini-2.0-flash')
        self.safety = {
            'HARASSMENT': 'block_none',
            'SEXUALLY_EXPLICIT': 'block_none',
            'HATE_SPEECH': 'block_none'
        }

    def ask(self, question):
        try:
            response = self.llm_model.generate_content(question, safety_settings=self.safety)
            return response.text
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

if __name__ == "__main__":
    client = Gemini()
    test_question = "What is the capital of France?"
    response = client.ask(test_question)
    print(f"\nQuestion: {test_question}")
    print(f"Response: {response}")