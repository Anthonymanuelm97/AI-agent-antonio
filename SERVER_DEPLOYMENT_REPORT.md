# Report: Preparing the Agent for Server Deployment

## Current limitation

The application is currently built around one interactive terminal session:

- [`main.py`](main.py) creates a single `Agent` and starts the command-line conversation.
- [`ai_agent/conversation.py`](ai_agent/conversation.py) reads input with `input()`, so that process can serve only the person using that terminal.
- [`ai_agent/agent.py`](ai_agent/agent.py) keeps conversation history and the customer's name in memory on the `Agent` instance. A single shared instance on a server would risk mixing different customers' conversations.
- [`ai_agent/data_access.py`](ai_agent/data_access.py) saves orders by editing an Excel workbook. Concurrent requests or multiple server instances could conflict while writing it.

## Recommended solution

Put an HTTP API in front of the agent, using **FastAPI**, and treat each customer conversation as a separate, persisted session.

A typical interaction would be:

1. A client starts a conversation and receives a conversation ID.
2. The client sends a message and that ID to an API endpoint.
3. The API loads that conversation's history, processes the message with the agent, saves the updated history, and returns the reply.
4. The client reuses the ID for its next message.

The agent should be created or initialized for the request using only that conversation's state—not kept as one globally shared conversation. The existing terminal interface can remain as an optional development tool.

## Suggested architecture

```text
Customer-facing client
        |
     HTTPS
        |
FastAPI application
        |
Conversation/agent service ---- Groq API
        |
     PostgreSQL
  conversations, messages,
  and orders
```

PostgreSQL is a good first persistence choice: it can store conversation histories and orders, and its transactions avoid the concurrent-write problems of using an Excel file as the order database. Keep the existing business workbook as a temporary source for relatively static menu and business information, or migrate that data to the database later.

## Deployment and safeguards

- Store the Groq API key in the hosting provider's secret configuration; never expose it to the client.
- Use HTTPS, validate requests, and add basic rate limiting.
- Ensure customers can access only their own conversation IDs.
- Make order creation transactional and safe to retry so network retries do not create duplicate orders.
- Add health checks and operational logging that avoid recording secrets or unnecessary customer data.
- Package the API for a container-based host. Redis is not essential for the first version if PostgreSQL stores sessions; it can be added later for caching or rate limiting.

## Suggested implementation sequence

1. Separate the conversation/agent logic from terminal input and output.
2. Add API endpoints to create a conversation and send a message.
3. Persist conversation and order data in PostgreSQL; replace Excel-based order writes before allowing concurrent production traffic.
4. Test that simultaneous conversations remain isolated and that repeated requests cannot duplicate orders.
5. Deploy the API with secrets, HTTPS, health checks, and basic monitoring.

## Recommendation

Start with FastAPI and PostgreSQL. This directly addresses the single-terminal limitation while keeping the design simple enough to deploy and extend.
