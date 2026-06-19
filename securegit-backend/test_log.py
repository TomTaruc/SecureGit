from app.services.git_service import git_log, _run
print("Testing dubious ownership...")
try:
    print(_run('/srv/git/user1/dandannn22.git', 'log', 'master', '--oneline'))
except Exception as e:
    print("Error:", e)
