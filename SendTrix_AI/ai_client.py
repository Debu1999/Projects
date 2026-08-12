from openai import OpenAI
import os
 
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
 
 
def ask_ai(prompt):
 
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
 
    return response.output_text