#!/usr/bin/env bash
set -e

if [ ! -f .env.development ]; then
  cp .env.development.example .env.development
  echo "⚠️  Created .env.development — fill in VITE_API_URL before continuing"
  exit 1
fi

echo "📦 Installing dependencies..."
npm install

echo "🚀 Starting dev server..."
npm run dev
