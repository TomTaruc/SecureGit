cd /tmp/testclient3
mkdir repo1
cd repo1
git init
git config user.email test@example.com
git config user.name TestUser
echo "Initial content" > data.txt
git add data.txt
git commit -m "Initial commit"
git branch -M main
export GIT_SSH_COMMAND='ssh -i /tmp/testclient3/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222'
git remote add origin ssh://git@localhost:2222/testuser/sshtest-lifecycle-744190066.git
git push -u origin main

cd /tmp/testclient3
git clone ssh://git@localhost:2222/testuser/sshtest-lifecycle-744190066.git repo2
cd repo2
git config user.email test@example.com
git config user.name TestUser
cat data.txt

cd /tmp/testclient3/repo1
echo "Second content" >> data.txt
git add data.txt
git commit -m "Second commit"
git push

cd /tmp/testclient3/repo2
git pull
cat data.txt
