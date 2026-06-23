# Replace paths and repo URL with your actual SecureGit SSH setup
$env:GIT_SSH_COMMAND = "ssh -i C:\path\to\readonly_user_key -o IdentitiesOnly=yes -v"
git clone ssh://git@localhost:2222/owner/test-repo.git readonly-clone
cd readonly-clone
"readonly push test" | Out-File readonly-test.txt
git add readonly-test.txt
git commit -m "readonly push test"
git push origin main
