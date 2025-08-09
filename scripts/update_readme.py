# scripts/update_readme.py
import toml
from datetime import datetime
import subprocess

pyproject = toml.load("pyproject.toml")
dependencies = pyproject.get("tool", {}).get("poetry", {}).get("dependencies", {})

version = pyproject.get("tool", {}).get("poetry", {}).get("version", "0.0.0")

commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).decode().strip()
commit_date = subprocess.check_output(["git", "log", "-1", "--date=short", "--pretty=%ad"]).decode().strip()

next_feature = "Integración de Celery + Redis"

deps_table = "\n".join(f"| {pkg} | {ver} |" for pkg, ver in dependencies.items())

with open("README.md", "r", encoding="utf-8") as f:
    readme = f.read()

version_section = f"""[![Versión](https://img.shields.io/badge/versión-v{version}-brightgreen?style=for-the-badge)](#)
[![Última actualización](https://img.shields.io/badge/última%20actualización-{commit_date}-blue?style=for-the-badge)](#)
[![Estado](https://img.shields.io/badge/estado-en%20desarrollo-orange?style=for-the-badge)](#)

| Versión actual | Última mejora | Fecha último commit | Próxima feature planificada |
|----------------|--------------|---------------------|-----------------------------|
| **v{version}** | {commit_msg} | {commit_date} | {next_feature} |
"""

readme = readme.split("<!-- AUTO-SECTION:VERSION -->")[0] + \
         f"<!-- AUTO-SECTION:VERSION -->\n{version_section}<!-- /AUTO-SECTION:VERSION -->" + \
         readme.split("<!-- /AUTO-SECTION:VERSION -->")[1]

deps_section = f"""## 📦 Dependencias

| Paquete | Versión |
|---------|---------|
{deps_table}
"""

readme = readme.split("<!-- AUTO-SECTION:DEPENDENCIAS -->")[0] + \
         f"<!-- AUTO-SECTION:DEPENDENCIAS -->\n{deps_section}<!-- /AUTO-SECTION:DEPENDENCIAS -->" + \
         readme.split("<!-- /AUTO-SECTION:DEPENDENCIAS -->")[1]

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)
