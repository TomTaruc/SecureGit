#!/bin/bash
OUTPUT=$(python /app/e2e_setup.py)
echo "$OUTPUT"
PROJ=$(echo "$OUTPUT" | grep PROJECT_NAME= | cut -d= -f2)
echo "Target repo: $PROJ"
cd /tmp
rm -rf "$PROJ"
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no"
git clone "ssh://git@127.0.0.1:2222/user1/$PROJ.git"
cd "$PROJ"
git config user.email "e2e@example.com"
git config user.name "E2E Tester"

echo "Init" > readme.md
git add readme.md
git commit -m "Initial commit"
git push origin main

echo "Second" >> readme.md
git commit -am "Second commit"
git push origin main

git checkout -b feature-test
echo "Feature" > feature.txt
git add feature.txt
git commit -m "Feature commit"
git push origin feature-test

echo "E2E SSH PUSHES SUCCESSFUL"
