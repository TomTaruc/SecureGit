#!/bin/bash
set -e

echo "Setting up test environment..."
mkdir -p /tmp/testclient
cd /tmp/testclient
rm -rf id_ed25519* repo

echo "Generating SSH key..."
ssh-keygen -t ed25519 -f id_ed25519 -N "" -q
PUB_KEY=$(cat id_ed25519.pub)

echo "Authenticating to API..."
TOKEN=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"SecurePass123"}' \
  | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

echo "Adding SSH key to API..."
curl -s -X POST http://localhost:5000/api/ssh-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"test_key\",\"public_key\":\"$PUB_KEY\"}" > /dev/null

echo "Creating Repository..."
REPO_NAME="sshtest-$RANDOM"
curl -s -X POST http://localhost:5000/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"project_name\":\"$REPO_NAME\", \"description\":\"Test\", \"visibility\":\"private\"}" > /dev/null

echo "Setting up local Git repo..."
mkdir repo
cd repo
git init
git config user.email "test@example.com"
git config user.name "Test User"
echo "Test file" > test.txt
git add test.txt
git commit -m "Initial commit"
git branch -M main

export GIT_SSH_COMMAND="ssh -i /tmp/testclient/id_ed25519 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222"
git remote add origin "ssh://git@localhost:2222/testuser/$REPO_NAME.git"

echo "Pushing via SSH..."
git push -u origin main
echo "Push successful!"
