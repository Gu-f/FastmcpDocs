import os
import json
from string import Template

with open('docs_template.json', 'r', encoding='utf-8') as t:
    template_docs_json = json.loads(t.read())

languages = template_docs_json['navigation']['languages']

config_path = 'json_config'

json_config = files = [f for f in os.listdir(config_path) if os.path.isfile(os.path.join(config_path, f))]

for config in json_config:
    with open(os.path.join(config_path, config), 'r', encoding='utf-8') as c:
        template = Template(c.read())
        data = template.safe_substitute(LANGUAGE_CODE=config.split('.')[0])
        languages.append(json.loads(data))

with open('docs.json', 'w', encoding='utf-8') as docs:
    docs.write(json.dumps(template_docs_json, indent=2, ensure_ascii=False))
