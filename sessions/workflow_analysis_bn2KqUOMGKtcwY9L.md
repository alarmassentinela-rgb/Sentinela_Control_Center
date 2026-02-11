# Workflow Analysis: Sentinela-0001-N8Nius-020126

**Date:** 2026-01-02
**Workflow ID:** `bn2KqUOMGKtcwY9L`
**Name:** `Sentinela-0001-N8Nius-020126`
**Status:** Active
**Server:** `gemini-local` (192.168.3.2:5678)

## Overview
This workflow implements an AI Sales Agent ("n8nius") designed to qualify leads and sell automation solutions via WhatsApp using Evolution API.

## Active Components (Enabled Nodes)
1.  **Webhook (`evolutionapi-n8nius`):** 
    - Entry point receiving POST requests from Evolution API.
2.  **Process Evolution Message1 (Code):**
    - Extracts `remoteJid` (phone number) and `conversation` text.
    - Filters out self-messages (`fromMe === true`).
    - Prepares the `chatInput` for the AI Agent.
3.  **Google Gemini Chat Model1:**
    - LLM provider connected to the AI Agent.
4.  **AI Agent (LangChain):**
    - The core decision-making node.
    - Currently configured to process the user input and generate a response.
5.  **Process AI Response Unipile Mx (Code):**
    - Parses the output from the AI Agent (handling potential JSON or string formats).
    - Truncates messages > 1000 characters.
6.  **HTTP Request Evolution API Mx:**
    - Sends the final text response back to the user via Evolution API (`/message/sendText/SentinelaOnline`).

## Disabled Components (Notable)
- **Memory & Context:**
    - `Postgres Chat Memory`: Disabled (The AI currently has no long-term memory of the conversation).
    - `Get row(s) in Google Sheets Mx`: Disabled (Cannot lookup product info).
- **Logging:**
    - `AV-008-n8nius-conversation-log` (Google Sheets logging): Disabled.
    - `Error Handler` & Telegram Error Notifications: Disabled.
- **Tools:**
    - `SerpAPI` (Web Search): Disabled.
    - `Send email`: Disabled.
- **Follow-up Logic:**
    - The entire "Follow up" / "Seguimiento" branch is disabled.

## Key Observations
- The bot is currently operating in a "stateless" mode (simple Q&A) without access to its product catalog or memory of past interactions.
- It relies entirely on the prompt instructions within the AI Agent node for its personality and logic.
