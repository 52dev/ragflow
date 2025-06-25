# Dummy tavily_conn.py

class Tavily:
    def __init__(self, api_key: str):
        print(f"Mock Tavily initialized with api_key='{api_key[:5]}...'")
        self.api_key = api_key

    def retrieve_chunks(self, query: str, max_results: int = 5):
        """
        Dummy function for retrieving chunks using Tavily.
        """
        print(f"Mock Tavily.retrieve_chunks called with query='{query}', max_results={max_results}")
        # Return a structure similar to what the Retrieval component expects
        # when extending kbinfos.
        # kbinfos["chunks"].extend(tav_res["chunks"])
        # kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])

        dummy_chunks = []
        dummy_doc_aggs = []

        for i in range(min(max_results, 2)): # Create a couple of dummy chunks
            dummy_chunks.append({
                "content": f"Dummy Tavily content for query '{query}' - chunk {i+1}",
                "source": f"dummy_tavily_source_{i+1}.com",
                "doc_id": f"tavily_doc_{i+1}",
                "docnm_kwd": f"Dummy Tavily Doc {i+1}"
                # Add other fields if they are accessed by downstream code e.g. 'vector', 'content_ltks'
            })
            dummy_doc_aggs.append({
                "doc_id": f"tavily_doc_{i+1}",
                "doc_name": f"Dummy Tavily Doc {i+1}"
            })

        return {"chunks": dummy_chunks, "doc_aggs": dummy_doc_aggs}

# Example usage in retrieval.py:
# tav = Tavily(self._param.tavily_api_key)
# tav_res = tav.retrieve_chunks(query)
# kbinfos["chunks"].extend(tav_res["chunks"])
# kbinfos["doc_aggs"].extend(tav_res["doc_aggs"])
