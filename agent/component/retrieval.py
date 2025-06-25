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
# from api.db.services.knowledgebase_service import KnowledgebaseService # Removed
from api.db.services.llm_service import LLMBundle # Mocked
# from api import settings # settings.retrievaler and settings.kg_retrievaler will be stubbed or removed
from agent.component.base import ComponentBase, ComponentParamBase
from rag.app.tag import label_question
from rag.prompts import kb_prompt
from rag.utils.tavily_conn import Tavily

# MockRetriever and SettingsMock are no longer needed as DB-specific retrieval path is removed.
# settings = SettingsMock() # Removed


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
        query = str(query["content"][0]) if "content" in query and not query.empty else ""
        query = re.split(r"(USER:|ASSISTANT:)", query)[-1]
        query = re.sub(r"^user[:：\s]*", "", query, flags=re.IGNORECASE)

        # kb_ids and kb_vars are now largely non-functional as KnowledgebaseService is removed.
        # Log if they are used.
        if self._param.kb_ids or self._param.kb_vars:
            logging.warning("Retrieval component: kb_ids/kb_vars are set, but KnowledgebaseService for DB-backed KBs has been removed. These parameters will be ignored.")

        # embd_mdl and rerank_mdl would have been configured based on KBs from DB.
        # For Tavily or other non-DB sources, these might need to be configured differently
        # or use global defaults if available. For now, they will be None unless Tavily sets them.
        # The mock LLMBundle can be instantiated with default/dummy values if needed by Tavily's part or other logic.
        # However, Tavily mock itself doesn't use embd_mdl or rerank_mdl.
        # If a real Tavily call was made and needed an embedding model for some internal step,
        # we'd need to instantiate a default LLMBundle here.
        # For now, this is simplified as the Tavily mock is self-contained.

        # The canvas embedding model should be set if we expect to use embeddings later (e.g. for citation)
        # This would typically come from a configured model, not necessarily tied to a specific DB KB.
        # If there's a default embedding model configured elsewhere (e.g. in Begin node or global settings),
        # that could be used. For now, we will use a dummy one if needed by citation.
        # self._canvas.set_embedding_model("default_mock_embedding_model_id") # Or get from a global config if available

        kbinfos = {"chunks": [], "doc_aggs": []}

        # KG (Knowledge Graph) logic might also have relied on DB KBs.
        # If self._param.use_kg is True, it implies some KG source.
        # The previous mock used settings.kg_retrievaler or added a dummy chunk.
        # We'll keep the dummy chunk logic if use_kg is true, assuming KG is a non-DB source or also mocked.
        if self._param.use_kg:
            logging.info("Retrieval component: use_kg is true. Adding a mock KG chunk.")
            kg_chunk = {
                "content": f"Mock Knowledge Graph result for '{query}'.",
                "doc_id": "kg_mock_doc",
                "docnm_kwd": "Mock KG Document",
                "content_with_weight": True
            }
            kbinfos["chunks"].insert(0, kg_chunk)
            # Note: The original settings.kg_retrievaler.retrieval call also needed embd_mdl and LLMBundle for chat.
            # These would need to be default/mocked instances if that path was kept.

        # Tavily is the primary remaining retrieval source
        if self._param.tavily_api_key:
            logging.info(f"Retrieval component: Attempting retrieval via Tavily for query: {query}")
            tav = Tavily(self._param.tavily_api_key) # Tavily mock is used
            try:
                tav_res = tav.retrieve_chunks(query, max_results=self._param.top_n)
                kbinfos["chunks"].extend(tav_res.get("chunks", []))
                kbinfos["doc_aggs"].extend(tav_res.get("doc_aggs", []))
            except Exception as e:
                logging.error(f"Error during Tavily retrieval: {e}")
                # Optionally, add an error message to the output
                # kbinfos["chunks"].append({"content": f"Error retrieving from Tavily: {e}", "doc_id": "tavily_error", "docnm_kwd": "Tavily Error"})
        else:
            logging.info("Retrieval component: No Tavily API key provided. Skipping Tavily search.")
            # If no Tavily and no KG, and DB KBs removed, there are no sources.
            # If only KG was used and produced chunks, those will be processed.
            # If no chunks from KG either, then kbinfos will be empty.

        # If still no chunks after attempting all sources (KG, Tavily)
        if not kbinfos["chunks"]:
            # Previously, if not self._param.tavily_api_key and kbs (DB KBs) existed,
            # settings.retrievaler.retrieval was called. This path is now removed.
            # So, if Tavily is not used (or fails) and KG is not used (or empty), we'll have no chunks.
            logging.info("Retrieval component: No chunks found from any source.")
            df = Retrieval.be_output(self._param.empty_response if self._param.empty_response and self._param.empty_response.strip() else "")
            # The 'empty_response' column logic seems to have been for specific downstream handling,
            # but for now, just ensuring the content is set is primary.
            return df

        # Ensure chunks are serializable and kb_prompt can handle them
        serializable_chunks = []
        for chunk in kbinfos["chunks"]:
            if isinstance(chunk, dict):
                # Ensure all values in the chunk dict are JSON serializable
                serializable_chunk = {}
                for k, v in chunk.items():
                    if isinstance(v, (pd.Timestamp, complex)): # Add other non-serializable types if encountered
                        serializable_chunk[k] = str(v)
                    else:
                        serializable_chunk[k] = v
                serializable_chunks.append(serializable_chunk)
            else:
                serializable_chunks.append({"content": str(chunk)})


        # Ensure kb_prompt gets what it expects. Our mock kb_prompt is simple.
        # The kb_prompt will be based on Tavily results or KG mock results.
        prompt_content = kb_prompt({"chunks": serializable_chunks, "doc_aggs": kbinfos.get("doc_aggs", [])}, 200000)

        df = pd.DataFrame({"content": prompt_content, "chunks": json.dumps(serializable_chunks)})
        logging.debug(f"Retrieval component for query '{query}' output: {df.to_string()}")
        # Stray lines removed here

        if not kbinfos["chunks"]:
            # This case is handled above now by the "No chunks found from any source" log and return.
            # This specific block might be redundant unless there's a path where kbinfos["chunks"] is empty
            # but the earlier "No chunks found" wasn't hit (e.g. if only doc_aggs were populated).
            # For safety, keeping a fall-through.
            logging.info("Retrieval component: Final check, no chunks to process.")
            df = Retrieval.be_output(self._param.empty_response if self._param.empty_response and self._param.empty_response.strip() else "")
            return df

        # Ensure kb_prompt gets what it expects. Our mock kb_prompt is simple.
        prompt_content = kb_prompt({"chunks": serializable_chunks, "doc_aggs": kbinfos.get("doc_aggs", [])}, 200000)

        df = pd.DataFrame({"content": prompt_content, "chunks": json.dumps(serializable_chunks)})
        logging.debug(f"Retrieval component for query '{query}' output: {df.to_string()}")
        return df.dropna()
