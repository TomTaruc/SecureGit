cd /tmp/testclient
rm -rf repo
mkdir repo
cd repo
git init
git config user.email test@example.com
git config user.name TestUser
echo test > test.txt
git add test.txt
git commit -m Initial
git branch -M main
export GIT_SSH_COMMAND='ssh -i /tmp/testclient/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222'
git remote add origin ssh://git@localhost:2222/testuser/sshtest-1611910980.git
git push -u origin main
