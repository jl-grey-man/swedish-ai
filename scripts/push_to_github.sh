#!/bin/bash
# Helper script to push changes to GitHub
# Run this on your machine where you have git credentials set up

echo "Swedish AI - Push to GitHub"
echo "============================"
echo ""

# Check if we're in the right directory
if [ ! -f "IMPLEMENTATION_STATUS.json" ]; then
    echo "Error: Not in swedish-ai directory"
    echo "Please run from: /path/to/swedish-ai"
    exit 1
fi

# Check git status
echo "Current status:"
git status
echo ""

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted changes"
    echo "Commit them first with:"
    echo "  git add -A"
    echo "  git commit -m 'Your message'"
    exit 1
fi

# Push
echo "Pushing to GitHub..."
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to https://github.com/jl-grey-man/swedish-ai"
    echo ""
    echo "Latest commit:"
    git log -1 --oneline
else
    echo ""
    echo "❌ Push failed"
    echo ""
    echo "Possible issues:"
    echo "1. No git credentials configured"
    echo "   Solution: git config credential.helper store"
    echo ""
    echo "2. Using HTTPS instead of SSH"
    echo "   Solution: git remote set-url origin git@github.com:jl-grey-man/swedish-ai.git"
    echo ""
    echo "3. Need to authenticate"
    echo "   Solution: Create a Personal Access Token at https://github.com/settings/tokens"
    exit 1
fi
