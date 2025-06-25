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
        self.parameters = []
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
    component_name = "Generate"

    def get_dependent_components(self):
        inputs = self.get_input_elements()
        cpnts = set([i["key"] for i in inputs[1:] if i["key"].lower().find("answer") < 0 and i["key"].lower().find("begin") < 0])
        return list(cpnts)

    def set_cite(self, retrieval_res, answer):
        # retrieval_res is a DataFrame. Ensure "chunks" column exists and has valid JSON.
        if "chunks" not in retrieval_res.columns or retrieval_res.empty or not retrieval_res["chunks"].iloc[0]:
            logging.warning("No chunks found in retrieval_res for citation.")
            res = {"content": answer, "reference": {"chunks": [], "doc_aggs": []}}
            return structure_answer(None, res, "", "") # structure_answer is mocked

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
        chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT, self._param.llm_id) # LLMBundle is mocked

        # if len(self._param.llm_enabled_tools) > 0: # Removed plugin logic
            # tools = GlobalPluginManager.get_llm_tools_by_names(self._param.llm_enabled_tools)
            # if tools:
            #     chat_mdl.bind_tools(
            #         LLMToolPluginCallSession(),
            #         [llm_tool_metadata_to_openai_tool(t.get_metadata()) for t in tools]
            #     )
            # else:
            #     logging.warning(f"LLM tools {self._param.llm_enabled_tools} configured but not found by mock GlobalPluginManager.")
        if self._param.llm_enabled_tools:
            logging.warning("LLM tools are configured but plugin system has been removed. Tools will not be used.")

        prompt = self._param.prompt

        retrieval_res = []
        self._param.inputs = []
        for para in self.get_input_elements()[1:]:
            if para["key"].lower().find("begin@") == 0:
                cpn_id, key = para["key"].split("@")
                for p in self._canvas.get_component(cpn_id)["obj"]._param.query:
                    if p["key"] == key:
                        kwargs[para["key"]] = p.get("value", "")
                        self._param.inputs.append(
                            {"component_id": para["key"], "content": kwargs[para["key"]]})
                        break
                else:
                    assert False, f"Can't find parameter '{key}' for {cpn_id}"
                continue

            component_id = para["key"]
            cpn = self._canvas.get_component(component_id)["obj"]
            if cpn.component_name.lower() == "answer":
                hist = self._canvas.get_history(1)
                if hist:
                    hist = hist[0]["content"]
                else:
                    hist = ""
                kwargs[para["key"]] = hist
                continue
            _, out = cpn.output(allow_partial=False)
            if "content" not in out.columns:
                kwargs[para["key"]] = ""
            else:
                if cpn.component_name.lower() == "retrieval":
                    retrieval_res.append(out)
                kwargs[para["key"]] = "  - " + "\n - ".join([o if isinstance(o, str) else str(o) for o in out["content"]])
            self._param.inputs.append({"component_id": para["key"], "content": kwargs[para["key"]]})

        if retrieval_res:
            retrieval_res = pd.concat(retrieval_res, ignore_index=True)
        else:
            retrieval_res = pd.DataFrame([])

        for n, v in kwargs.items():
            prompt = re.sub(r"\{%s\}" % re.escape(n), str(v).replace("\\", " "), prompt)

        if not self._param.inputs and prompt.find("{input}") >= 0:
            retrieval_res = self.get_input()
            input = ("  - " + "\n  - ".join(
                [c for c in retrieval_res["content"] if isinstance(c, str)])) if "content" in retrieval_res else ""
            prompt = re.sub(r"\{input\}", re.escape(input), prompt)

        downstreams = self._canvas.get_component(self._id)["downstream"]
        if kwargs.get("stream") and len(downstreams) == 1 and self._canvas.get_component(downstreams[0])[
            "obj"].component_name.lower() == "answer":
            return partial(self.stream_output, chat_mdl, prompt, retrieval_res)

        # Check retrieval_res for content before deciding it's an "empty_response" case
        # The "empty_response" column itself might not be the primary indicator if content is also empty.
        # If retrieval_res is empty or its "content" column is empty/None.
        is_retrieval_empty = retrieval_res.empty or \
                             ("content" not in retrieval_res.columns) or \
                             retrieval_res["content"].isnull().all() or \
                             (not retrieval_res["content"].astype(str).str.strip().any())

        if is_retrieval_empty and "empty_response" in retrieval_res.columns and retrieval_res["empty_response"].iloc[0]:
            # This case handles when Retrieval component itself produces a specific "empty_response"
            empty_res_content = str(retrieval_res["empty_response"].iloc[0])
            res = {"content": empty_res_content, "reference": []}
            logging.info("Using empty_response from retrieval result.")
            return pd.DataFrame([res])
        elif is_retrieval_empty: # General case if retrieval found nothing and no specific empty_response was set by it
            res = {"content": "Nothing found in knowledgebase (mock response).", "reference": []}
            logging.info("Retrieval result is empty, returning default empty message.")
            return pd.DataFrame([res])


        history_messages = self._canvas.get_history(self._param.message_history_window_size)

        # Construct messages for the LLM
        llm_messages = [{"role": "system", "content": prompt}] + history_messages

        # Ensure the last message is 'user' if history is not empty, or add a dummy user message.
        # The mock LLM might not care, but good practice.
        if not llm_messages or llm_messages[-1]["role"] != "user":
             # Check if the last message from history_messages was assistant, if so, append user output
            if history_messages and history_messages[-1]["role"] == "assistant":
                llm_messages.append({"role": "user", "content": "Output: "}) # Default user turn
            elif not history_messages and llm_messages[0]["role"] == "system": # Only system prompt
                llm_messages.append({"role": "user", "content": "Output: "})


        # message_fit_in is mocked. chat_mdl.max_length comes from mocked LLMBundle.
        _, fitted_messages = message_fit_in(llm_messages, int(chat_mdl.max_length * 0.97))

        if not fitted_messages or fitted_messages[0]["role"] != "system": # Ensure system prompt is first if present
            # This case should ideally be handled by message_fit_in logic.
            # If fitted_messages is empty or system prompt is missing, we might need to adjust.
            # For now, assume message_fit_in mock handles it reasonably.
            # If only user message is left, that's also fine.
            if not fitted_messages: # if message_fit_in returns empty, add a default
                 fitted_messages=[{"role": "user", "content": "Output: "}]


        system_prompt_for_llm = ""
        chat_history_for_llm = []
        if fitted_messages[0]["role"] == "system":
            system_prompt_for_llm = fitted_messages[0]["content"]
            chat_history_for_llm = fitted_messages[1:]
        else:
            chat_history_for_llm = fitted_messages

        if not chat_history_for_llm: # Ensure chat history is not empty
            chat_history_for_llm.append({"role":"user", "content":"Output:"})


        # chat_mdl.chat is mocked
        ans = chat_mdl.chat(system_prompt_for_llm, chat_history_for_llm, self._param.gen_conf())
        ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL) # This post-processing can remain

        self._canvas.set_component_infor(self._id, {"prompt": system_prompt_for_llm, "messages": chat_history_for_llm, "conf": self._param.gen_conf()})

        if self._param.cite and "chunks" in retrieval_res.columns and not retrieval_res["chunks"].isnull().all():
            # Make sure retrieval_res is not empty and has actual chunks before citing
            if not retrieval_res.empty and retrieval_res["chunks"].iloc[0] and json.loads(retrieval_res["chunks"].iloc[0]):
                res = self.set_cite(retrieval_res, ans)
                return pd.DataFrame([res])
            else: # No valid chunks to cite
                logging.info("Citation skipped as no valid chunks found in retrieval_res.")
                return Generate.be_output(ans) # ans already has the LLM response

        return Generate.be_output(ans) # ans is the direct LLM response

    def stream_output(self, chat_mdl, prompt, retrieval_res):
        res = None # Final response to be set by set_output

        is_retrieval_empty = retrieval_res.empty or \
                             ("content" not in retrieval_res.columns) or \
                             retrieval_res["content"].isnull().all() or \
                             (not retrieval_res["content"].astype(str).str.strip().any())

        if is_retrieval_empty and "empty_response" in retrieval_res.columns and retrieval_res["empty_response"].iloc[0]:
            empty_res_content = str(retrieval_res["empty_response"].iloc[0])
            current_res_dict = {"content": empty_res_content, "reference": []}
            logging.info("Stream: Using empty_response from retrieval result.")
            yield current_res_dict
            self.set_output(pd.DataFrame([current_res_dict])) # Set final output for the component
            return
        elif is_retrieval_empty:
            current_res_dict = {"content": "Nothing found in knowledgebase (mock stream response).", "reference": []}
            logging.info("Stream: Retrieval result is empty, yielding default empty message.")
            yield current_res_dict
            self.set_output(pd.DataFrame([current_res_dict]))
            return

        history_messages = self._canvas.get_history(self._param.message_history_window_size)
        # Remove last assistant message from history if it exists, to prevent double assistant responses
        if history_messages and history_messages[-1]['role'] == 'assistant':
             history_messages.pop() # Critical fix: was msg[0] before, should be history_messages[-1]

        llm_messages = [{"role": "system", "content": prompt}] + history_messages
        if not llm_messages or llm_messages[-1]["role"] != "user":
            if history_messages and history_messages[-1]["role"] == "assistant": # This condition may no longer be met due to pop above
                 llm_messages.append({"role": "user", "content": "Output: "})
            elif not history_messages and llm_messages[0]["role"] == "system":
                 llm_messages.append({"role": "user", "content": "Output: "})


        _, fitted_messages = message_fit_in(llm_messages, int(chat_mdl.max_length * 0.97))
        if not fitted_messages: fitted_messages=[{"role": "user", "content": "Output: "}]

        system_prompt_for_llm = ""
        chat_history_for_llm = []
        if fitted_messages[0]["role"] == "system":
            system_prompt_for_llm = fitted_messages[0]["content"]
            chat_history_for_llm = fitted_messages[1:]
        else:
            chat_history_for_llm = fitted_messages

        if not chat_history_for_llm: chat_history_for_llm.append({"role":"user", "content":"Output:"})

        streamed_answer_content = ""
        # chat_mdl.chat_streamly is mocked
        for ans_chunk in chat_mdl.chat_streamly(system_prompt_for_llm, chat_history_for_llm, self._param.gen_conf()):
            current_res_dict = {"content": ans_chunk, "reference": []} # Mock reference for stream
            streamed_answer_content = ans_chunk # The mock yields the full answer at once. If it were real stream, this would build up.
            yield current_res_dict

        # After stream finishes, set the component's information
        self._canvas.set_component_infor(self._id, {"prompt": system_prompt_for_llm, "messages": chat_history_for_llm, "conf": self._param.gen_conf()})

        # Final processing for citation, using the fully streamed answer
        final_res_dict = {"content": streamed_answer_content, "reference": []} # Default if no citation
        if self._param.cite and "chunks" in retrieval_res.columns and not retrieval_res["chunks"].isnull().all():
            if not retrieval_res.empty and retrieval_res["chunks"].iloc[0] and json.loads(retrieval_res["chunks"].iloc[0]):
                # Use the fully accumulated answer for citation
                final_res_dict = self.set_cite(retrieval_res, streamed_answer_content)
                yield final_res_dict # Yield the cited version as the last item
            else:
                logging.info("Stream: Citation skipped as no valid chunks found.")

        self.set_output(pd.DataFrame([final_res_dict])) # Set the final output of the component

    # This is the start of the properly indented debug method
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
