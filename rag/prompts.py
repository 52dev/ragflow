# Dummy prompts.py

def kb_prompt(kbinfos: dict, max_length: int) -> str:
    """
    Dummy function for kb_prompt.
    Formats knowledge base information into a prompt string.
    """
    print(f"Mock kb_prompt called with kbinfos, max_length={max_length}")
    # kbinfos usually contains 'chunks' and 'doc_aggs'
    # Return a simple string representation for the dummy.
    chunks_content = []
    if "chunks" in kbinfos and kbinfos["chunks"]:
        for chunk in kbinfos["chunks"]:
            if isinstance(chunk, dict) and "content" in chunk:
                chunks_content.append(str(chunk["content"]))
            else: # older format from Tavily
                chunks_content.append(str(chunk))


    if not chunks_content:
        return "No relevant information found in knowledge base."

    prompt_str = "Relevant information from knowledge base:\n" + "\n".join(chunks_content)
    if len(prompt_str) > max_length:
        return prompt_str[:max_length] + "..."
    return prompt_str

def message_fit_in(messages: list, max_length: int):
    """
    Dummy function for message_fit_in.
    Ensures messages fit within a token limit.
    """
    print(f"Mock message_fit_in called with {len(messages)} messages, max_length={max_length}")
    # This function usually returns:
    # (total_length, list_of_messages_that_fit)
    # For simplicity, just return the original messages and a dummy length.

    # Calculate a rough estimate of length
    current_length = 0
    fitted_messages = []

    # System prompt is usually first and always included if present
    if messages and messages[0].get("role") == "system":
        system_message = messages[0]
        current_length += len(system_message.get("content", ""))
        fitted_messages.append(system_message)
        remaining_messages = messages[1:]
    else:
        remaining_messages = messages

    # Add messages from the end until max_length is approached
    temp_messages = []
    for msg in reversed(remaining_messages):
        msg_content = msg.get("content", "")
        if isinstance(msg_content, list): # Handle cases where content might be a list of parts (e.g. image and text)
            for part in msg_content:
                if isinstance(part, dict) and "type" in part:
                    if part["type"] == "text":
                        current_length += len(part.get("text", ""))
                    # Add more sophisticated handling if other types (e.g. image URLs) contribute to length
                else: # Fallback for unexpected format
                    current_length += len(str(part))

        else:
            current_length += len(str(msg_content))

        if current_length > max_length and temp_messages: # if it exceeds and we have messages, break
            break
        temp_messages.insert(0, msg)
        if current_length > max_length: # if it exceeds after adding the current one, break
            break

    fitted_messages.extend(temp_messages)

    # Ensure user message is present if the list is not empty and last one is not user
    # This is a common pattern for chat models
    if fitted_messages and fitted_messages[-1].get("role") != "user":
        # If the last message is not 'user', and we have space,
        # try to add a generic user message or ensure the last one is user.
        # This part can be tricky without knowing the exact logic.
        # For a dummy, we might just ensure the list isn't empty if it started with messages.
        pass # Simplified: actual logic might try to preserve conversation flow.

    final_length = sum(len(str(m.get("content", ""))) for m in fitted_messages) # Ensure content is string for len()
    return final_length, fitted_messages

def full_question(tenant_id: str, llm_id: str, messages: list[dict], language: str) -> str:
    """
    Mock function for generating a "full question" based on history.
    The original likely calls an LLM. This mock will return a simple transformation or fixed string.
    """
    logging.debug(f"Mock full_question called for tenant_id='{tenant_id}', llm_id='{llm_id}', language='{language}' with {len(messages)} messages.")

    last_user_message = "Could not find last user message."
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_message = str(msg.get("content", ""))
            break

    rewritten = f"Mock rewritten full question in {language if language else 'default language'} for: '{last_user_message}'"
    logging.info(f"Mock full_question returning: {rewritten}")
    return rewritten


import logging # Ensure logging is imported if not already

# Example usage in generate.py:
# df = pd.DataFrame({"content": kb_prompt(kbinfos, 200000), "chunks": json.dumps(kbinfos["chunks"])})
# _, msg = message_fit_in([{"role": "system", "content": prompt}, *msg], int(chat_mdl.max_length * 0.97))

# Example usage in rewrite.py:
# ans = full_question(self._canvas.get_tenant_id(), self._param.llm_id, messages, self.gen_lang(self._param.language))
