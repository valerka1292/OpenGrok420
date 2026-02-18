
try:
    import openai
    print("openai imported successfully")
except ImportError:
    print("openai import failed")

try:
    import dotenv
    print("dotenv imported successfully")
except ImportError:
    print("dotenv import failed")
