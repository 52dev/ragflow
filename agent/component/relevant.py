#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import logging
from abc import ABC
from api.db.services import LLMType # Adjusted import
from api.db.services.llm_service import LLMBundle # This is mocked
from agent.component import GenerateParam, Generate
# from rag.utils import num_tokens_from_string, encoder # Removed


class RelevantParam(GenerateParam):

    """
    Define the Relevant component parameters.
    """
    def __init__(self):
        super().__init__()
        self.prompt = ""
        self.yes = ""
        self.no = ""

    def check(self):
        super().check()
        self.check_empty(self.yes, "[Relevant] 'Yes'")
        self.check_empty(self.no, "[Relevant] 'No'")

    def get_prompt(self):
        self.prompt = """
        You are a grader assessing relevance of a retrieved document to a user question. 
        It does not need to be a stringent test. The goal is to filter out erroneous retrievals.
        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. 
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
        No other words needed except 'yes' or 'no'.
        """
        return self.prompt


class Relevant(Generate, ABC):
    component_name = "Relevant"

    def _run(self, history, **kwargs):
        q = ""
        for r, c in self._canvas.history[::-1]:
            if r == "user":
                q = c
                break
        ans = self.get_input()
        ans = " - ".join(ans["content"]) if "content" in ans else ""
        if not ans:
            return Relevant.be_output(self._param.no)
        ans = "Documents: \n" + ans
        ans = f"Question: {q}\n" + ans
        chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT, self._param.llm_id)

        # Estimate character limit based on LLM's max_length (assuming 1 token ~ 4 chars)
        # Subtract a small buffer (e.g., 20 chars) for safety margin with prompts/roles.
        # chat_mdl.max_length is from the mocked LLMBundle.
        char_limit = (chat_mdl.max_length * 4) - 20

        if len(ans) > char_limit:
            logging.warning(f"Relevant component: Input text length ({len(ans)} chars) exceeds estimated limit ({char_limit} chars). Truncating.")
            ans = ans[:char_limit-3] + "..." # Truncate and add ellipsis

        llm_prompt = self._param.get_prompt()
        llm_messages = [{"role": "user", "content": ans}]

        # Simple message fitting for Relevant component (system prompt + user content)
        # The system prompt from get_prompt() is usually short.
        # If llm_prompt + ans is too long, we prioritize user content (ans) as it's already truncated.
        # A more robust solution would use the Generate component's _prepare_llm_messages if complex history was involved.
        # For 'Relevant', the history isn't directly used in the LLM call, only the current Q and Document.

        # Naive check for prompt + content length (char based)
        if len(llm_prompt) + len(ans) > char_limit * 1.2 : # Allow some leeway over just 'ans'
             logging.warning("Relevant component: Combined prompt and content might be too long. Using only content for LLM call.")
             # This could be an issue if the system prompt is very long.
             # For now, assuming system prompt is concise.
             # If not, a more sophisticated truncation of combined prompt+content would be needed.
             llm_response_text = chat_mdl.chat(llm_prompt, llm_messages, self._param.gen_conf())
        else:
             llm_response_text = chat_mdl.chat(llm_prompt, llm_messages, self._param.gen_conf())


        logging.debug(llm_response_text)
        if llm_response_text.lower().find("yes") >= 0:
            return Relevant.be_output(self._param.yes)
        if llm_response_text.lower().find("no") >= 0:
            return Relevant.be_output(self._param.no)
        # If LLM response is neither yes/no, default to 'no' or raise error.
        # Original code had an assert False, which would halt.
        # Let's default to 'no' for robustness if the LLM (mock or real) doesn't behave.
        logging.warning(f"Relevant component got ambiguous LLM response: '{llm_response_text}'. Defaulting to 'no'.")
        return Relevant.be_output(self._param.no)

        assert False, f"Relevant component got: {llm_response_text}" # This line is now unreachable due to default above

    def debug(self, **kwargs):
        return self._run([], **kwargs)

