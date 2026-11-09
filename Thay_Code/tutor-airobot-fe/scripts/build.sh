#!/usr/bin/env bash
set -e

echo "🔍 Type checking..."
npm run typecheck

echo "🏗️  Building..."
npm run build

echo "✅ Build complete → dist/"
