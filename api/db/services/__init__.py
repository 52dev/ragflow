# This file makes Python treat the `services` directory as a package.

# Define constants if they are imported directly from here
LLMType = type("LLMType", (), {"CHAT": "chat", "EMBEDDING": "embedding", "RERANK": "rerank"})
