import re

text = """Here are the wireless earbuds extracted from the text with prices:

- Sony WF-1000XM5: $280
- Apple AirPods Pro 2: $249
- JBL Tune 130NC: $99"""

products = []
for line in text.split('\n'):
    line = line.strip()
    if not line:
        continue
    if line[0] not in '-*•' and not re.match(r'^\d+\.', line):
        continue
    
    # Remove bullet/number
    line = re.sub(r'^[\-*•\d]+\.?\s*', '', line).strip()
    if not line:
        continue
    
    print(f'Processing: {repr(line)}')
    
    # Extract name and price
    name = line
    price_match = re.search(r'\$([0-9,]+(?:\.\d{2})?)', line)
    if price_match:
        price = f'${price_match.group(1)}'
        name = re.sub(r'[:]\s*\$[0-9,]+(?:\.\d{2})?[^\w]*$', '', name).strip()
        print(f'  -> Name: {repr(name)}, Price: {price}')
        
        # Filter
        skip_keywords = ['http', 'www.', '.com', 'article', 'reddit', 'discussion']
        if any(kw in name.lower() for kw in skip_keywords):
            print('  -> SKIPPED (has skip keyword)')
            continue
        
        products.append({'name': name, 'price': price})

print(f'\nTotal products: {len(products)}')
for p in products:
    print(f"  - {p['name']}: {p['price']}")
