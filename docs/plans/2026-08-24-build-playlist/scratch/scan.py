import json

with open('plan.json', 'rb') as f:
    data = f.read()
try:
    text = data.decode('utf-8')
except UnicodeDecodeError:
    text = data.decode('cp1252')
plan = json.loads(text)

targets = ['DL-024','DL-025','DL-026','DL-028','DL-029','DL-031','DL-032','DL-035']

def walk(obj, path):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, path + '.' + str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, path + '[' + str(i) + ']')
    elif isinstance(obj, str):
        for dl in targets:
            if dl in obj:
                print(dl + ' -> ' + path)

walk(plan, 'root')
