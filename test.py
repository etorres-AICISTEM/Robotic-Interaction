from openai import OpenAI
import os

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

user_question = "Hello, can you introduce yourself?"

# 2. Uso del cliente (client.chat.completions.create) en vez de openai.ChatCompletion
response = client.chat.completions.create(
     model="nvidia/nemotron-3-nano-30b-a3b", # NVIDIA no tiene gpt-3.5, usa un modelo disponible en su API
    messages=[{"role": "user", "content": user_question}],
    temperature=0.5,
    max_tokens=1024
)

# 3. Acceso a la respuesta (Sintaxis de objetos, no diccionarios)
answer = response.choices[0].message.content
print("NVIDIA Model response:", answer)