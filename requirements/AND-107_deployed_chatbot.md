# AND-107 Deployed Chatbot

## Overview

The chatbot is live on the deployed dashboard, accessible via the same public URL from Sprint 1. The deployed version uses a remote LLM provider with a free tier instead of local Ollama. All chatbot capabilities work in the deployed environment, not just locally.

## Requirements

- **Public URL:** The chatbot is accessible at the same Render dashboard URL established in AND-106 (https://rocketdash-dashboard.onrender.com).
- **Remote LLM provider:** The deployed version uses OpenRouter (free tier) instead of local Ollama, since Ollama cannot run on Render's free tier.
- **Feature parity:** All AND-107 capabilities — database queries, risk predictions, RAG knowledge base, source citations, and inspection scheduling — must work in the deployed environment, not just locally.
- **Local vs. deployed:** Local development continues to use Ollama. The remote provider is used only in the Render deployment (controlled via environment variable).
