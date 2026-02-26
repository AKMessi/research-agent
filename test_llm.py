import requests
import re

prompt = """Extract wireless earbuds from this text about \"best wireless earbuds for workout\".

TEXT:
[1] Best workout earbuds 2024 - RTings
The Sony WF-1000XM5 are great for gym at $280. Apple AirPods Pro 2 at $249 are sweat resistant. JBL Tune 130NC at $99 is the budget pick.

[2] Best Headphones for Workouts 2026 - CNET
Bose Sport Earbuds at $179 good for runners. Beats Fit Pro at $199 popular for workouts.

List ONLY earbuds:
- Earbud Model Name: $Price

Earbud List:"""

resp = requests.post(
    'http://localhost:11434/api/generate',
    json={
        'model': 'llama3.2',
        'prompt': prompt,
        'stream': False,
        'options': {'temperature': 0.1, 'num_predict': 800}
    },
    timeout=45
)

text = resp.json().get('response', '')
print('Response:')
print(repr(text))
print()
print('Formatted:')
print(text)
