import os

def remove_user_git(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return
        
    content = content.replace('', '')
    content = content.replace('', '')
    content = content.replace('\\n        ', '')
    content = content.replace('\\n        group="git"', '')
    content = content.replace('', '')
    content = content.replace('', '')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

base_dir = r"c:\\Users\\motar\\SecureGit\\SecureGit\\securegit-backend"
for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith('.py'):
            remove_user_git(os.path.join(root, file))

print("Replaced user='git' everywhere.")

