import json
from pathlib import Path

path = Path(__file__).resolve().parent / "lession3.ipynb"
nb = json.loads(path.read_text(encoding='utf-8'))
changed = False
for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code' and cell.get('source', []) and cell['source'][0].startswith('#學生總分為300'):
        cell['source'] = [
            '#學生總分為300\n',
            '#有些學生可以加5%\n',
            '\n',
            'score = int(input("請輸入學生的分數(最高300分)："))\n',
            'bonus = input("學生是否符合加分條件?(Y/N)：")\n',
            '\n',
            'if bonus == "Y": #單項選擇\n',
            '    score = score * 1.05\n',
            '\n',
            'score = min(score, 300)\n',
            'print("學生的總分為：", round(score))  \n',
        ]
        changed = True
        break
if not changed:
    raise SystemExit('target cell not found')
path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
print('updated lession3.ipynb')
