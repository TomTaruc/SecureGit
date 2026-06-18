#!/bin/bash
# =============================================================================
# SecureGit Git post-receive hook
# Install into: /srv/git/{user}/{project}.git/hooks/post-receive
# Must be executable: chmod +x post-receive
# =============================================================================
HOOK_SECRET="__HOOK_SECRET__"
FLASK_INTERNAL="http://127.0.0.1:5000"

while read oldrev newrev refname; do
    # Notify Flask backend to sync commits to PostgreSQL
    curl -s -f -X POST \
        "$FLASK_INTERNAL/internal/hook/post-receive" \
        -H "Content-Type: application/json" \
        -H "X-Hook-Secret: $HOOK_SECRET" \
        -d "{
            \"repo_path\": \"$(pwd)\",
            \"oldrev\":    \"$oldrev\",
            \"newrev\":    \"$newrev\",
            \"ref\":       \"$refname\"
        }" \
        --max-time 10 \
        > /dev/null 2>&1 || true  # Don't fail push on hook error
done
