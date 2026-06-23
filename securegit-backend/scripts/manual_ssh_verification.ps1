# Manual SSH Verification Script for SecureGit

# Prerequisites
# 1. Ensure you have two SSH keys generated:
#    C:\path\to\owner_key
#    C:\path\to\readonly_key
# 2. Add these keys to the respective users via the SecureGit UI (or API).
# 3. Ensure the SecureGit SSH server is running on localhost port 2222.

echo "--- Testing Owner Clone ---"
$env:GIT_SSH_COMMAND = "ssh -i C:\path\to\owner_key -o IdentitiesOnly=yes -v"
git clone ssh://git@localhost:2222/owner/test-repo.git owner-clone

echo "--- Testing Read Collaborator Clone ---"
$env:GIT_SSH_COMMAND = "ssh -i C:\path\to\readonly_key -o IdentitiesOnly=yes -v"
git clone ssh://git@localhost:2222/owner/test-repo.git readonly-clone

echo "--- Testing Read Collaborator Push Rejection ---"
cd readonly-clone
echo "readonly change" | Out-File readonly.txt
git add readonly.txt
git commit -m "readonly push attempt"
git push origin main
# Expected output:
# Push rejected by pre-receive hook.
# You do not have permission to perform this action.

echo "Verification complete. Ensure read collaborator push was rejected."
