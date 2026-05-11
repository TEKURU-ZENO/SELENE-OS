# 🚀 Deployment Guide

This document outlines the standard deployment procedure for the SELENE Cognitive Runtime.

## Architecture Prerequisites
- Python 3.14 (Backend Runtime)
- Node.js 20+ (Frontend Next.js)
- Environment variable configuration (`.env`) for MCP server paths.

## Backend Startup
SELENE's backend orchestrates the LangGraph DAG, Policy Gate, and MCP ecosystem.
```bash
cd backend
export PYTHONPATH="."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Startup
The React 19 / Next.js 16 frontend serves the Trust Dashboard and Cognitive Flight Recorder.
```bash
cd frontend
npm install
npm run dev
```

## MCP Setup
MCP servers must be registered in the `ServerRegistry` (backend/mcp/registry/server_registry.py) with valid `MCPServerManifest` configurations outlining their capabilities and Trust Classifications before they can be routed to by the Planner.
