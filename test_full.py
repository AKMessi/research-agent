import sys
sys.path.insert(0, '.')

from research_agent.core.synthesis_engine import SynthesisEngine

engine = SynthesisEngine()
print(f'Model: {engine.ollama_model}')

# Test with actual text
text = """Here is the list of wireless earbuds extracted from the text:

1. Sony WF-1000XM5: $280
2. Apple AirPods Pro 2: $249
3. JBL Tune 130NC: $99
4. Bose Sport Earbuds: $179
5. Beats Fit Pro: $199"""

products = engine._parse_product_list(text)
print(f'\nParsed {len(products)} products:')
for p in products:
    print(f"  - {p['name']}: {p['price']}")
