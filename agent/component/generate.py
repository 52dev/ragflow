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
import json
import re
from functools import partial
from typing import Any
import pandas as pd
import logging # Added for logging
from api.db.services import LLMType # Adjusted import
from api.db.services.conversation_service import structure_answer
from api.db.services.llm_service import LLMBundle
# from api import settings # settings.retrievaler will be stubbed or removed
from agent.component.base import ComponentBase, ComponentParamBase
# from plugin import GlobalPluginManager # Removed
# from plugin.llm_tool_plugin import llm_tool_metadata_to_openai_tool # Removed
# from rag.llm.chat_model import ToolCallSession # ToolCallSession was used by LLMToolPluginCallSession, removing if not used elsewhere
from rag.prompts import message_fit_in # This is now mocked

# Mock for settings.retrievaler (specifically for insert_citations)
class MockRetrieverForCite:
    def insert_citations(self, answer, content_ltks, vectors, llm_bundle, tkweight, vtweight):
        logging.info(f"MockRetrieverForCite.insert_citations called for answer: {answer[:50]}...")
        # Return the original answer and a dummy list of indices
        # The number of dummy indices could correspond to how many citations might be expected, e.g. 1 or 2.
        # Or, more simply, an empty list if no citations are to be added by the mock.
        # Let's return a couple of dummy indices if chunks were provided.
        num_dummy_citations = min(len(content_ltks), 2) if content_ltks else 0
        return answer + " [Mock Citation(s)]" if num_dummy_citations > 0 else answer, list(range(num_dummy_citations))

class SettingsMockGenerate:
    def __init__(self):
        self.retrievaler = MockRetrieverForCite()

settings = SettingsMockGenerate()

# class LLMToolPluginCallSession(ToolCallSession): # Removed as plugin system is being removed
#     def tool_call(self, name: str, arguments: dict[str, Any]) -> str:
#         tool = GlobalPluginManager.get_llm_tool_by_name(name)
#
#         if tool is None:
#             raise ValueError(f"LLM tool {name} does not exist")
#
#         return tool().invoke(**arguments)

class GenerateParam(ComponentParamBase):
    """
    Define the Generate component parameters.
    """

    def __init__(self):
        super().__init__()
        self.llm_id = ""
        self.prompt = ""
        self.max_tokens = 0
        self.temperature = 0
        self.top_p = 0
        self.presence_penalty = 0
        self.frequency_penalty = 0
        self.cite = True
        # self.parameters = [] # Removed unused parameter
        self.llm_enabled_tools = []

    def check(self):
        self.check_decimal_float(self.temperature, "[Generate] Temperature")
        self.check_decimal_float(self.presence_penalty, "[Generate] Presence penalty")
        self.check_decimal_float(self.frequency_penalty, "[Generate] Frequency penalty")
        self.check_nonnegative_number(self.max_tokens, "[Generate] Max tokens")
        self.check_decimal_float(self.top_p, "[Generate] Top P")
        self.check_empty(self.llm_id, "[Generate] LLM")
        # self.check_defined_type(self.parameters, "Parameters", ["list"])

    def gen_conf(self):
        conf = {}
        if self.max_tokens > 0:
            conf["max_tokens"] = self.max_tokens
        if self.temperature > 0:
            conf["temperature"] = self.temperature
        if self.top_p > 0:
            conf["top_p"] = self.top_p
        if self.presence_penalty > 0:
            conf["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty > 0:
            conf["frequency_penalty"] = self.frequency_penalty
        return conf


class Generate(ComponentBase):
    """
    The Generate component interacts with a Language Model (LLM) to generate text
    based on a given prompt template and context from other components or history.
    It can also handle citations if provided with retrieval results.
    """
    component_name = "Generate"

    def get_dependent_components(self):
        """
        Determines dependent components based on variables in the prompt template.
        """
        inputs = self.get_input_elements()
        # Exclude 'answer' and 'begin' components from explicit dependencies if they are special keywords
        cpnts = set([i["key"] for i in inputs[1:] if i["key"].lower().find("answer") < 0 and i["key"].lower().find("begin") < 0])
        return list(cpnts)

    def _get_prompt_inputs(self, current_kwargs: dict) -> tuple[dict, list[pd.DataFrame]]:
        """
        Fetches inputs from dependent components as specified in the prompt
        template's input elements. Updates self._param.inputs.

        :param current_kwargs: Dictionary to be populated with fetched input values.
                               This dict is modified in place.
        :return: A tuple containing the populated current_kwargs and a list of retrieval result DataFrames.
        """
        retrieval_results_dfs = []
        self._param.inputs = [] # Clear previous inputs logged in params

        # Iterate through input elements identified from the prompt template
        # Skip the first one if it's the generic "user input" placeholder, actual inputs start from index 1.
        for para_spec in self.get_input_elements()[1:]:
            component_key = para_spec["key"]
            input_content_str = "" # Default to empty string

            if component_key.lower().find("begin@") == 0: # Input from Begin node's parameters
                cpn_id, key_in_begin = component_key.split("@", 1)
                begin_cpn_obj = self._canvas.get_component(cpn_id)["obj"]
                # Assuming BeginParam stores its queryable parameters in a list of dicts called 'query'
                found_param = False
                for p_query_item in begin_cpn_obj._param.query:
                    if p_query_item.get("key") == key_in_begin:
                        input_content_str = p_query_item.get("value", "")
                        found_param = True
                        break
                if not found_param:
                    logging.warning(f"Could not find parameter '{key_in_begin}' in Begin component '{cpn_id}' for prompt variable '{component_key}'. Using empty string.")

            else: # Input from a standard component's output
                component_obj = self._canvas.get_component(component_key)["obj"]
                if component_obj.component_name.lower() == "answer": # Special case for "answer" component (current user input/history)
                    history_list = self._canvas.get_history(1) # Get latest history entry
                    input_content_str = history_list[0]["content"] if history_list else ""
                else: # Output from other components
                    _, output_df = component_obj.output(allow_partial=False)
                    if "content" not in output_df.columns or output_df.empty:
                        input_content_str = ""
                    else:
                        # Consolidate potentially multiple rows of content into a single string
                        input_content_str = "  - " + "\n  - ".join([str(o) for o in output_df["content"].dropna()])
                        if component_obj.component_name.lower() == "retrieval":
                            retrieval_results_dfs.append(output_df)

            current_kwargs[component_key] = input_content_str # Populate the dictionary passed in
            self._param.inputs.append({"component_id": component_key, "content": input_content_str})

        return current_kwargs, retrieval_results_dfs

    def _substitute_prompt_variables(self, prompt_template: str, prompt_vars: dict) -> str:
        """
        Substitutes variables in the prompt template with their fetched values.
        Also handles a generic {input} placeholder.
        """
        prompt = prompt_template
        for var_name, var_value in prompt_vars.items():
            # Escape regex special characters in var_name for re.sub
            # Also ensure var_value is a string and its backslashes are handled.
            prompt = re.sub(r"\{%s\}" % re.escape(var_name), str(var_value).replace("\\", r"\\"), prompt)

        # Fallback for a generic {input} placeholder if it wasn't in prompt_vars (e.g. not in get_input_elements)
        # This typically means it should take its input from the single, direct upstream non-control component.
        if "{input}" in prompt and "input" not in prompt_vars:
            # self.get_input() is from ComponentBase, gets data from immediate upstream.
            generic_input_df = self.get_input()
            if "content" in generic_input_df and not generic_input_df.empty:
                input_str = "  - " + "\n  - ".join([str(c).replace("\\", r"\\") for c in generic_input_df["content"].dropna()])
                prompt = re.sub(r"\{input\}", input_str, prompt) # No re.escape for replacement string itself
            else:
                prompt = re.sub(r"\{input\}", "", prompt) # Replace with empty if no content
        return prompt

    def _prepare_llm_messages(self, system_prompt_str: str, chat_model_max_length: int) -> tuple[str, list[dict[str, Any]]]:
        """
        Prepares the system prompt and message list for the LLM call,
        including history and ensuring it fits within token limits.
        """
        history_messages = self._canvas.get_history(self._param.message_history_window_size)

        # Ensure history doesn't end with an assistant message if we're retrying/continuing
        if history_messages and history_messages[-1]['role'] == 'assistant':
            history_messages.pop()

        # Assemble messages for token fitting: system prompt + historical messages
        messages_to_fit = [{"role": "system", "content": system_prompt_str}] + history_messages

        # Ensure there's a user message at the end if the history is now empty or ends with system
        if not messages_to_fit or messages_to_fit[-1]["role"] != "user":
            # If history_messages was empty and only system prompt is there, add a default user turn
            if len(messages_to_fit) == 1 and messages_to_fit[0]["role"] == "system":
                 messages_to_fit.append({"role": "user", "content": "Output: "}) # Default user turn
            # If messages_to_fit became empty (e.g. only assistant message popped), add default user turn
            elif not messages_to_fit:
                 messages_to_fit = [{"role": "user", "content": "Output: "}]

        # Fit messages into token limit (message_fit_in is mocked)
        # The mock LLMBundle has a max_length attribute.
        _, fitted_messages = message_fit_in(messages_to_fit, int(chat_model_max_length * 0.97))

        # Fallback if fitting results in empty messages (should be handled by message_fit_in ideally)
        if not fitted_messages:
            fitted_messages = [{"role": "user", "content": "Output: "}]

        # Separate system prompt from chat history for the LLM
        final_system_prompt = ""
        final_chat_history = []
        if fitted_messages[0]["role"] == "system":
            final_system_prompt = fitted_messages[0]["content"]
            final_chat_history = fitted_messages[1:]
        else:
            final_chat_history = fitted_messages

        # Ensure chat history for LLM is not empty (add default user turn if necessary)
        if not final_chat_history:
            final_chat_history.append({"role":"user", "content":"Output:"})

        return final_system_prompt, final_chat_history

    def set_cite(self, retrieval_res_df: pd.DataFrame, answer: str):
        """
        Processes retrieval results to insert citations into the answer and format references.
        :param retrieval_res_df: DataFrame containing retrieval results, expects a 'chunks' column with JSON strings.
        :param answer: The raw answer string from the LLM.
        :return: A dictionary with 'content' (answer with citations) and 'reference' (structured chunk data).
        """
        if not isinstance(retrieval_res_df, pd.DataFrame) or \
           "chunks" not in retrieval_res_df.columns or \
           retrieval_res_df.empty or \
           not retrieval_res_df["chunks"].iloc[0]:
            logging.warning("No valid chunks found in retrieval_res_df for citation.")
            res = {"content": answer, "reference": {"chunks": [], "doc_aggs": []}}
            return structure_answer(None, res, "", "")

        try:
            # Assuming chunks are stored as a JSON string in the first row of the 'chunks' column
            chunks_json_str = retrieval_res["chunks"].iloc[0]
            chunks = json.loads(chunks_json_str)
            if not isinstance(chunks, list): # Ensure chunks is a list
                logging.warning(f"Parsed chunks is not a list: {chunks}")
                chunks = []
        except (json.JSONDecodeError, IndexError, TypeError) as e:
            logging.error(f"Error decoding chunks from retrieval_res: {e}. Chunks data: {retrieval_res.get('chunks')}")
            chunks = []

        if not chunks:
            logging.warning("Chunks list is empty after parsing for citation.")
            res = {"content": answer, "reference": {"chunks": [], "doc_aggs": []}}
            return structure_answer(None, res, "", "")

        # Mocked insert_citations. The original needs 'content_ltks' and 'vector'.
        # Our mocked chunks from Retrieval component might not have these.
        # The MockRetrieverForCite.insert_citations is simplified.
        # We need to ensure it gets some list-like structure for content_ltks and vectors.
        mock_content_ltks = [chunk.get("content", "") for chunk in chunks]
        mock_vectors = [[0.0] for _ in chunks] # Dummy vectors

        answer, idx = settings.retrievaler.insert_citations(
            answer,
            mock_content_ltks,
            mock_vectors,
            LLMBundle(self._canvas.get_tenant_id(), LLMType.EMBEDDING, self._canvas.get_embedding_model()), # LLMBundle is mocked
            tkweight=0.7,
            vtweight=0.3
        )

        doc_ids = set([])
        recall_docs = []
        valid_indices = [i for i in idx if isinstance(i, int) and 0 <= i < len(chunks)]

        for i in valid_indices:
            chunk = chunks[i]
            did = chunk.get("doc_id", f"unknown_doc_{i}")
            if did in doc_ids:
                continue
            doc_ids.add(did)
            recall_docs.append({"doc_id": did, "doc_name": chunk.get("docnm_kwd", f"Unknown Document {i}")})

        # Sanitize chunks for reference: remove complex objects if any were added by mistake
        # (though current mocks for Retrieval output serializable chunks).
        sanitized_chunks_for_reference = []
        for c in chunks:
            s_chunk = c.copy() # work on a copy
            s_chunk.pop("vector", None) # Remove keys that were problematic or large
            s_chunk.pop("content_ltks", None)
            # Ensure all values are serializable
            for k, v in s_chunk.items():
                if not isinstance(v, (str, int, float, bool, list, dict, type(None))):
                    s_chunk[k] = str(v)
            sanitized_chunks_for_reference.append(s_chunk)


        reference = {
            "chunks": sanitized_chunks_for_reference, # Use the sanitized chunks
            "doc_aggs": recall_docs
        }

        # This warning seems like a good practice to keep if LLM itself returns it.
        if "invalid key" in answer.lower() or "invalid api" in answer.lower():
            answer += " Please set LLM API-Key in 'User Setting -> Model providers -> API-Key'"

        res = {"content": answer, "reference": reference}
        # structure_answer is mocked, will just return the dict or wrap it.
        return structure_answer(None, res, "", "")

    def get_input_elements(self):
        key_set = set([])
        res = [{"key": "user", "name": "Input your question here:"}]
        for r in re.finditer(r"\{([a-z]+[:@][a-z0-9_-]+)\}", self._param.prompt, flags=re.IGNORECASE):
            cpn_id = r.group(1)
            if cpn_id in key_set:
                continue
            if cpn_id.lower().find("begin@") == 0:
                cpn_id, key = cpn_id.split("@")
                for p in self._canvas.get_component(cpn_id)["obj"]._param.query:
                    if p["key"] != key:
                        continue
                    res.append({"key": r.group(1), "name": p["name"]})
                    key_set.add(r.group(1))
                continue
            cpn_nm = self._canvas.get_component_name(cpn_id)
            if not cpn_nm:
                continue
            res.append({"key": cpn_id, "name": cpn_nm})
            key_set.add(cpn_id)
        return res

    def _run(self, history, **kwargs):
        """
        Main execution logic for the Generate component.
        The `history` and `**kwargs` from the original signature are kept for compatibility
        with ComponentBase.run, but specific prompt inputs are now fetched by _get_prompt_inputs.
        """
        chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT, self._param.llm_id)

        if self._param.llm_enabled_tools: # Logic for handling removed plugin system
            logging.warning("LLM tools are configured but plugin system has been removed. Tools will not be used.")

        # Fetch and prepare prompt inputs
        # Initialize prompt_template_vars with current_kwargs to capture any direct kwargs passed to run
        prompt_template_vars = kwargs.copy()
        _, retrieval_dfs = self._get_prompt_inputs(prompt_template_vars)

        retrieval_res_df = pd.DataFrame([])
        if retrieval_dfs: # Consolidate if multiple retrieval sources
            retrieval_res_df = pd.concat(retrieval_dfs, ignore_index=True)

        final_prompt_str = self._substitute_prompt_variables(self._param.prompt, prompt_template_vars)

        # Determine if streaming output is required
        downstreams = self._canvas.get_component(self._id)["downstream"]
        is_streaming_to_answer = kwargs.get("stream", False) and \
                                 len(downstreams) == 1 and \
                                 self._canvas.get_component(downstreams[0])["obj"].component_name.lower() == "answer"

        if is_streaming_to_answer:
            return partial(self.stream_output, chat_mdl, final_prompt_str, retrieval_res_df)

        # Handle case where retrieval found nothing and direct empty response is appropriate
        is_retrieval_empty = retrieval_res_df.empty or \
                             ("content" not in retrieval_res_df.columns) or \
                             retrieval_res_df["content"].isnull().all() or \
                             (not retrieval_res_df["content"].astype(str).str.strip().any())

        retrieval_has_specific_empty_response = not retrieval_res_df.empty and \
                                               "empty_response" in retrieval_res_df.columns and \
                                               retrieval_res_df["empty_response"].iloc[0]
        if is_retrieval_empty:
            empty_message_content = "Nothing found in knowledgebase (mock response)."
            if retrieval_has_specific_empty_response:
                 empty_message_content = str(retrieval_res_df["empty_response"].iloc[0])

            logging.info(f"Retrieval result is empty. Short-circuiting with: '{empty_message_content}'")
            res = {"content": empty_message_content, "reference": []}
            return pd.DataFrame([res])

        # Prepare messages for LLM
        system_prompt_for_llm, chat_history_for_llm = self._prepare_llm_messages(final_prompt_str, chat_mdl.max_length)

        # LLM call
        ans = chat_mdl.chat(system_prompt_for_llm, chat_history_for_llm, self._param.gen_conf())
        ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)

        self._canvas.set_component_infor(self._id, {"prompt": system_prompt_for_llm, "messages": chat_history_for_llm, "conf": self._param.gen_conf()})

        # Handle citation
        if self._param.cite and "chunks" in retrieval_res_df.columns and not retrieval_res_df["chunks"].isnull().all():
            if not retrieval_res_df.empty and retrieval_res_df["chunks"].iloc[0]:
                try:
                    json_chunks = json.loads(retrieval_res_df["chunks"].iloc[0])
                    if isinstance(json_chunks, list) and json_chunks:
                        res = self.set_cite(retrieval_res_df, ans)
                        return pd.DataFrame([res])
                except (json.JSONDecodeError, TypeError) as e:
                    logging.warning(f"Citation skipped: Chunks data in retrieval_res_df is not valid JSON list or is empty. Error: {e}")
            else:
                logging.info("Citation skipped as no valid chunks data found in retrieval_res_df.")

        # Default case if no citation or citation path wasn't taken
        return Generate.be_output(ans)

    def stream_output(self, chat_mdl: LLMBundle, final_prompt_str: str, retrieval_res_df: pd.DataFrame):
        """
        Handles streaming output from the LLM, including potential citation processing.
        """
        final_streamed_response_dict = {"content": "", "reference": []}

        is_retrieval_empty = retrieval_res_df.empty or \
                             ("content" not in retrieval_res_df.columns) or \
                             retrieval_res_df["content"].isnull().all() or \
                             (not retrieval_res_df["content"].astype(str).str.strip().any())

        retrieval_has_specific_empty_response = not retrieval_res_df.empty and \
                                               "empty_response" in retrieval_res_df.columns and \
                                               retrieval_res_df["empty_response"].iloc[0]

        if is_retrieval_empty:
            empty_message_content = "Nothing found in knowledgebase (mock stream response)."
            if retrieval_has_specific_empty_response:
                empty_message_content = str(retrieval_res_df["empty_response"].iloc[0])

            logging.info(f"Stream: Retrieval result is empty, yielding: '{empty_message_content}'")
            final_streamed_response_dict = {"content": empty_message_content, "reference": []}
            yield final_streamed_response_dict
            self.set_output(pd.DataFrame([final_streamed_response_dict]))
            return

        system_prompt_for_llm, chat_history_for_llm = self._prepare_llm_messages(final_prompt_str, chat_mdl.max_length)

        streamed_answer_content = ""
        for ans_chunk in chat_mdl.chat_streamly(system_prompt_for_llm, chat_history_for_llm, self._param.gen_conf()):
            current_yield_dict = {"content": ans_chunk, "reference": []}
            streamed_answer_content = ans_chunk
            yield current_yield_dict
            final_streamed_response_dict = current_yield_dict

        self._canvas.set_component_infor(self._id, {"prompt": system_prompt_for_llm, "messages": chat_history_for_llm, "conf": self._param.gen_conf()})

        if self._param.cite and "chunks" in retrieval_res_df.columns and not retrieval_res_df["chunks"].isnull().all():
            if not retrieval_res_df.empty and retrieval_res_df["chunks"].iloc[0]:
                try:
                    json_chunks = json.loads(retrieval_res_df["chunks"].iloc[0])
                    if isinstance(json_chunks, list) and json_chunks:
                        cited_response_dict = self.set_cite(retrieval_res_df, streamed_answer_content)
                        yield cited_response_dict
                        final_streamed_response_dict = cited_response_dict
                    else:
                        logging.info("Stream: Citation skipped as chunks data is empty or not a list.")
                except (json.JSONDecodeError, TypeError) as e:
                    logging.warning(f"Stream: Citation skipped due to error decoding chunks. Error: {e}")
            else:
                logging.info("Stream: Citation skipped as no valid chunk data found in retrieval_res_df.")

        self.set_output(pd.DataFrame([final_streamed_response_dict]))

    def debug(self, **kwargs):
        # LLMBundle is mocked
        logging.info(f"Generate.debug called with llm_id: {self._param.llm_id}, prompt: {self._param.prompt[:50]}...")
        chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT, self._param.llm_id)
        prompt_template = self._param.prompt # Use the prompt template from params

        # Process debug inputs to fill in template
        # kwargs provided to debug() can override or add to self._param.debug_inputs
        # For simplicity, let's assume self._param.debug_inputs is primary for template filling here
        # and direct kwargs are for other controls if any.

        current_kwargs = {}
        if hasattr(self._param, 'debug_inputs') and self._param.debug_inputs:
            for para_spec in self._param.debug_inputs:
                # Assuming para_spec is a dict like {"key": "...", "value": "..."}
                # The original code in _run method uses get_input_elements() then processes.
                # Here, we simplify for debug:
                if isinstance(para_spec, dict) and "key" in para_spec and "value" in para_spec:
                    current_kwargs[para_spec["key"]] = para_spec.get("value", "")

        # Override with any direct kwargs passed to debug
        current_kwargs.update(kwargs)


        final_prompt = prompt_template
        for n, v in current_kwargs.items():
            # Ensure placeholder exists before trying to replace, to avoid issues with unused debug_inputs
            placeholder = "{%s}" % re.escape(n)
            if placeholder in final_prompt:
                final_prompt = re.sub(placeholder, str(v).replace("\\", " "), final_prompt)
            else:
                logging.debug(f"Placeholder {placeholder} not found in prompt template for debug.")

        # The 'user' kwarg for chat history seems conventional in the original code
        user_input_for_chat = current_kwargs.get("user", "Debug input: Output please.")

        # The mock chat method expects (system_prompt, messages_list, config)
        # In debug, the 'prompt' becomes the system prompt.
        # The user input forms a minimal history.
        logging.info(f"Debug final prompt for LLM: {final_prompt[:100]}...")
        logging.info(f"Debug user input for LLM chat: {user_input_for_chat}")

        ans = chat_mdl.chat(
            system_prompt=final_prompt,
            messages=[{"role": "user", "content": user_input_for_chat}],
            llm_config=self._param.gen_conf()
        )

        # The component output is typically a DataFrame
        return pd.DataFrame([{"content": ans}])
