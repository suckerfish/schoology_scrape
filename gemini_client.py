import google.generativeai as genai
import os


class Gemini:
    def __init__(self):
        self.api_key = os.getenv('gemini_key')
        genai.configure(api_key=self.api_key)
        self.llm_model = genai.GenerativeModel('gemini-2.0-flash-exp')
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
            
    def __del__(self):
        # Attempt to cleanup gRPC connections
        try:
            genai.close()
        except:
            pass