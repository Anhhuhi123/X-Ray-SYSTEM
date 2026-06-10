import toml
import os
import re

with open("pyproject.toml") as f:
    config = toml.load(f)

deps = config["project"]["dependencies"]
package_names = []
for d in deps:
    # Handle forms like 'package>=1.0', 'package[extra]', 'package@url'
    name = re.split(r'[>=<\[@]', d)[0]
    package_names.append(name.lower())

print("Dependencies found:", package_names)

def find_imports(pkg):
    # Some packages have different import names
    mapping = {
        "pyarrow": "pyarrow",
        "discord-py": "discord",
        "google-api-python-client": "googleapiclient",
        "google-auth-oauthlib": "google_auth_oauthlib",
        "llama-cloud-services": "llama_cloud",
        "markdown": "markdown",
        "notion-client": "notion_client",
        "sentence-transformers": "sentence_transformers",
        "slack-sdk": "slack_sdk",
        "en-core-web-sm": "en_core_web_sm",
        "fastapi-users": "fastapi_users",
        "langgraph-checkpoint-postgres": "langgraph.checkpoint.postgres",
        "psycopg": "psycopg",
        "langchain-community": "langchain_community",
        "langchain-litellm": "langchain_litellm",
        "langchain-unstructured": "langchain_unstructured",
        "langchain-daytona": "langchain_daytona",
        "langchain-openai": "langchain_openai",
        "langchain-google-genai": "langchain_google_genai",
        "autogen-agentchat": "autogen",
        "autogen-ext": "autogen_ext",
        "static-ffmpeg": "static_ffmpeg",
        "huggingface_hub": "huggingface_hub",
        "fake-useragent": "fake_useragent",
        "lxml_html_clean": "lxml.html.clean",
        "pypandoc_binary": "pypandoc",
    }
    import_name = mapping.get(pkg, pkg.replace("-", "_"))
    
    # Run grep
    res = os.popen(f"grep -rnw 'app' -e 'import {import_name}' -e 'from {import_name}'").read()
    return len(res.strip()) > 0

unused = []
for pkg in package_names:
    if not find_imports(pkg):
        unused.append(pkg)

print("Potentially Unused Dependencies:", unused)
