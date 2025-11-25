from pathlib import Path

analysis = Path('app/api/routes/apify/facebook/routes/analysis.py').resolve()
root = Path.cwd()

print('Root:', root)
print('Analysis:', analysis)
print()

for i in range(1, 10):
    p = analysis
    for j in range(i):
        p = p.parent
    print(f'{i} parents: {p}')
    if p == root:
        print(f'  ✅ MATCH at {i} levels')
        break
