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
import logging
import re
from abc import ABC

import pandas as pd

from api.db.services import LLMType # Adjusted import
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
# from api import settings # settings.retrievaler and settings.kg_retrievaler will be stubbed or removed
from agent.component.base import ComponentBase, ComponentParamBase
from rag.app.tag import label_question
from rag.prompts import kb_prompt
from rag.utils.tavily_conn import Tavily

# Mock for settings.retrievaler and settings.kg_retrievaler
class MockRetriever:
    def retrieval(self, query, embd_mdl, tenant_ids, kb_ids, page, top_n, similarity_threshold, vector_weight, aggs=False, rerank_mdl=None, rank_feature=None):
        logging.info(f"MockRetriever.retrieval called for query: {query}")
        # Return a structure that kb_prompt can handle, typically with 'chunks'
        return {"chunks": [{"content": "Mocked retrieval result.", "doc_id": "mock_doc_1", "docnm_kwd": "Mock Document 1"}], "doc_aggs": []}

# It's safer to define these globally or pass them around if they were truly dynamic.
# For now, a global mock instance.
class SettingsMock:
    def __init__(self):
        self.retrievaler = MockRetriever()
        self.kg_retrievaler = MockRetriever() # Assuming kg_retrievaler has a similar interface

settings = SettingsMock()


class RetrievalParam(ComponentParamBase):
    """
    Define the Retrieval component parameters.
    """

    def __init__(self):
        super().__init__()
        self.similarity_threshold = 0.2
        self.keywords_similarity_weight = 0.5
        self.top_n = 8
        self.top_k = 1024
        self.kb_ids = []
        self.kb_vars = []
        self.rerank_id = ""
        self.empty_response = ""
        self.tavily_api_key = ""
        self.use_kg = False

    def check(self):
        self.check_decimal_float(self.similarity_threshold, "[Retrieval] Similarity threshold")
        self.check_decimal_float(self.keywords_similarity_weight, "[Retrieval] Keyword similarity weight")
        self.check_positive_number(self.top_n, "[Retrieval] Top N")


class Retrieval(ComponentBase, ABC):
    component_name = "Retrieval"

    def _run(self, history, **kwargs):
        query = self.get_input()
        query = str(query["content"][0]) if "content" in query else ""
        query = re.split(r"(USER:|ASSISTANT:)", query)[-1]

        kb_ids: list[str] = self._param.kb_ids or []

        kb_vars = self._fetch_outputs_from(self._param.kb_vars)

        if len(kb_vars) > 0:
            for kb_var in kb_vars:
                if len(kb_var) == 1:
                    kb_var_value = str(kb_var["content"][0])

                    for v in kb_var_value.split(","):
                        kb_ids.append(v)
                else:
                    for v in kb_var.to_dict("records"):
                        kb_ids.append(v["content"])

        filtered_kb_ids: list[str] = [kb_id for kb_id in kb_ids if kb_id]

        kbs = KnowledgebaseService.get_by_ids(filtered_kb_ids)
        if not kbs:
            return Retrieval.be_output("")

        embd_nms = list(set([kb.embd_id for kb in kbs]))
        assert len(embd_nms) == 1, "Knowledge bases use different embedding models."

        embd_mdl = None
        if embd_nms:
            embd_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.EMBEDDING, embd_nms[0])
            self._canvas.set_embedding_model(embd_nms[0])

        rerank_mdl = None
        if self._param.rerank_id:
            rerank_mdl = LLMBundle(kbs[0].tenant_id, LLMType.RERANK, self._param.rerank_id)

        # if kbs: # kbs will be a list of mock objects now
        #     query = re.sub(r"^user[:：\s]*", "", query, flags=re.IGNORECASE)
        #     # Use the mocked settings.retrievaler
        #     kbinfos = settings.retrievaler.retrieval(
        #         query,
        #         embd_mdl, # This will be a Mock LLMBundle
        #         [kb.tenant_id for kb in kbs],
        #         filtered_kb_ids,
        #         1, # page
        #         self._param.top_n,
        #         self._param.similarity_threshold,
        #         1 - self._param.keywords_similarity_weight, # vector_weight
        #         aggs=False,
        #         rerank_mdl=rerank_mdl, # This will be a Mock LLMBundle or None
        #         rank_feature=label_question(query, kbs), # label_question is mocked
        #     )
        # else:
        #     kbinfos = {"chunks": [], "doc_aggs": []}

        # Simplified logic for stubbing:
        # If we have KBs, simulate a retrieval, otherwise return empty.
        kbinfos = {"chunks": [], "doc_aggs": []}
        if kbs:
            query = re.sub(r"^user[:：\s]*", "", query, flags=re.IGNORECASE)
            # Simulate some chunks being retrieved
            # The actual retrieval logic is complex and depends on external services.
            # We'll use the Tavily mock if API key is provided, or a generic mock if not.
            if not self._param.tavily_api_key: # Only use this generic mock if tavily is not used
                 kbinfos = settings.retrievaler.retrieval(
                    query, embd_mdl, [kb.tenant_id for kb in kbs], filtered_kb_ids,
                    1, self._param.top_n, self._param.similarity_threshold,
                    1 - self._param.keywords_similarity_weight,
                    rerank_mdl=rerank_mdl, rank_feature=label_question(query, kbs)
                )

        # The KG retrieval part is also complex. We'll simulate it adds a chunk if use_kg is true.
        if self._param.use_kg and kbs:
            # Simulate a KG chunk
            kg_chunk = {
                "content": f"Mock Knowledge Graph result for '{query}'.",
                "doc_id": "kg_mock_doc",
                "docnm_kwd": "Mock KG Document",
                "content_with_weight": True # Ensure this field exists if checked
            }
            # Use the mocked settings.kg_retrievaler or just add a dummy chunk
            # For simplicity, let's assume kg_retrievaler.retrieval would return something like kg_chunk
            # If kg_retrievaler.retrieval is called, it would use the MockRetriever.
            # To ensure it's distinct or controlled, we can directly add a chunk.
            if kg_chunk["content_with_weight"]: # This check was in original code for 'ck'
                 kbinfos["chunks"].insert(0, kg_chunk)

        if self._param.tavily_api_key:
            tav = Tavily(self._param.tavily_api_key) # Tavily is mocked
            tav_res = tav.retrieve_chunks(query, max_results=self._param.top_n) # Pass top_n for consistency
            kbinfos["chunks"].extend(tav_res["chunks"])
            kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])

        if not kbinfos["chunks"]:
            df = Retrieval.be_output(self._param.empty_response if self._param.empty_response and self._param.empty_response.strip() else "")
            # The original code added 'empty_response' as a column.
            # Let's ensure the output format is consistent.
            # If there's an empty_response parameter, it should be used as the content.
            if self._param.empty_response and self._param.empty_response.strip():
                 # Retrieval.be_output creates a DataFrame with a 'content' column.
                 # If we want a specific empty response, we set it here.
                 # The previous line already does this.
                 # However, the original code adds an 'empty_response' column if there are no chunks AND an empty_response is set.
                 # This seems redundant if be_output already handles the content.
                 # For now, we'll stick to be_output handling the content directly.
                 # If an 'empty_response' column is strictly needed by other components:
                 # df["empty_response"] = self._param.empty_response
                 pass # df already contains the empty response as content
            return df

        # Ensure chunks are serializable and kb_prompt can handle them
        serializable_chunks = []
        for chunk in kbinfos["chunks"]:
            if isinstance(chunk, dict):
                serializable_chunks.append({k: v for k, v in chunk.items() if not isinstance(v, (pd.Timestamp, complex))}) # Add more types if necessary
            else: # Should not happen with current mocks, but as a safeguard
                serializable_chunks.append({"content": str(chunk)})


        # Ensure kb_prompt gets what it expects. Our mock kb_prompt is simple.
        prompt_content = kb_prompt({"chunks": serializable_chunks, "doc_aggs": kbinfos["doc_aggs"]}, 200000)

        df = pd.DataFrame({"content": prompt_content, "chunks": json.dumps(serializable_chunks)})
        logging.debug(f"Retrieval component for query '{query}' output: {df.to_string()}")
        return df.dropna()
