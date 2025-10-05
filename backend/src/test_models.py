import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("AIzaSyAdXQlqtuDic-DeRmY0hGFd-472gJ2FjaA"))

for m in genai.list_models():
    print(m.name)
