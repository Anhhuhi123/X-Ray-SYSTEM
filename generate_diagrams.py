import re
import subprocess
import os

MAPPING = {
    "use_case.md": ["usecase_over.svg", "usecase_doc.svg", "usecase_chat.svg"],
    "activity_diagram.md": ["act_auth.svg", "act_doc.svg", "act_know.svg", "act_rag.svg"],
    "sequence_diagram.md": ["seq_up.svg", "seq_rag.svg", "seq_hist.svg"],
    "system_architecture.md": ["arch_overall.svg", "arch_rag.svg"]
}

os.makedirs("Architecture", exist_ok=True)

def sanitize_mermaid(block):
    block = block.strip()
    if block.startswith("activityDiagram"):
        block = block.replace("activityDiagram", "", 1).strip()
    if block.startswith("usecaseDiagram"):
        block = block.replace("usecaseDiagram", "flowchart LR", 1)
        # actor "Owner / Admin" as Admin
        block = re.sub(r'actor\s+"([^"]+)"\s+as\s+(\w+)', r'\2([ \1 ])', block)
        # actor User
        block = re.sub(r'actor\s+([A-Za-z0-9_]+)', r'\1([ \1 ])', block)
        # usecase "Name" as UC_X
        block = re.sub(r'usecase\s+"([^"]+)"\s+as\s+(\w+)', r'\2([ "\1" ])', block)
        # rectangle "Name" {
        block = re.sub(r'rectangle\s+"([^"]+)"\s+{', r'subgraph \1', block)
        # User <|-- Admin (not supported in flowchart)
        block = block.replace("<|--", "---")
    return block

for filename, svg_names in MAPPING.items():
    if not os.path.exists(filename):
        continue
        
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
        
    blocks = re.findall(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
    
    for i, block in enumerate(blocks):
        if i >= len(svg_names):
            break
        svg_name = svg_names[i]
        mmd_name = svg_name.replace(".svg", ".mmd")
        
        sanitized = sanitize_mermaid(block)
        
        with open(mmd_name, "w", encoding="utf-8") as f:
            f.write(sanitized)
            
        print(f"Generating {svg_name}...")
        try:
            subprocess.run(["npx", "@mermaid-js/mermaid-cli", "-i", mmd_name, "-o", f"Architecture/{svg_name}"], check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to generate {svg_name}. Check syntax.")
        finally:
            if os.path.exists(mmd_name):
                os.remove(mmd_name)

print("Finished generation process!")
