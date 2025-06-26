# Dummy LLMService
import pandas as pd
import logging # Added for logging

class LLMBundle:
    def __init__(self, llm_type, llm_name, **kwargs): # tenant_id removed
        # print(f"Mock LLMBundle initialized with tenant_id={tenant_id}, llm_type={llm_type}, llm_name={llm_name}")
        logging.info(f"Mock LLMBundle initialized with llm_type={llm_type}, llm_name='{llm_name}'")
        # self.tenant_id = tenant_id # Removed
        self.llm_type = llm_type
        self.llm_name = llm_name
        self.max_length = 4096 # Default max length

    def chat(self, system_prompt, messages, llm_config):
        print(f"Mock LLMBundle.chat called with system_prompt='{system_prompt}', messages={messages}, config={llm_config}")
        # Return a dummy response string
        return "This is a dummy response from the LLM."

    def chat_streamly(self, system_prompt, messages, llm_config):
        print(f"Mock LLMBundle.chat_streamly called with system_prompt='{system_prompt}', messages={messages}, config={llm_config}")
        # Yield a dummy response string
        yield "This is a dummy streamed response from the LLM."

    def encode(self, texts_to_embed: list[str], **kwargs) -> list[list[float]]:
        print(f"Mock LLMBundle.encode called for {len(texts_to_embed)} texts.")
        # Return dummy embeddings (list of lists of floats)
        # The dimensionality of embeddings can be arbitrary for a dummy, e.g., 4
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts_to_embed]

    def similarity(self, query_vector: list[float], candidate_vectors: list[list[float]]) -> list[float]:
        print(f"Mock LLMBundle.similarity called.")
        # Return dummy similarity scores
        return [0.5 for _ in candidate_vectors]

    def bind_tools(self, tool_session, tools_schema):
        print(f"Mock LLMBundle.bind_tools called with tool_session={tool_session}, tools_schema={tools_schema}")
        # No operation needed for dummy
        pass

    # Add other methods as needed, e.g., for reranking if LLMType.RERANK is used
    def rerank(self, query: str, documents: list[str], top_n: int = -1):
        print(f"Mock LLMBundle.rerank called with query='{query}', {len(documents)} documents, top_n={top_n}")
        # Return dummy reranked documents and scores
        # For simplicity, return the original documents with some dummy scores
        reranked_docs = documents[:top_n] if top_n > 0 else documents
        scores = [0.9 - i*0.1 for i in range(len(reranked_docs))] # Dummy scores
        return reranked_docs, scores

# LLMType might be defined in api.db.services.__init__ or here if not found
# For now, assume it's available from the __init__.py
# from . import LLMType
