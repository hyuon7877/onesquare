# -*- coding: utf-8 -*-
import json
import os

project_path = f"/var/www/html/{os.environ['PROJECT_NAME']}"
secrets = {
    "SECRET_KEY": os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production'),
    "EMAIL_HOST_PASSWORD": ""
}

with open(f"{project_path}/secrets.json", 'w', encoding='utf-8') as f:
    json.dump(secrets, f, indent=4, ensure_ascii=False)

print("✅ secrets.json 생성 완료!")
