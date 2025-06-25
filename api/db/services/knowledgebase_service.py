# Dummy KnowledgebaseService
import pandas as pd

class KnowledgebaseService:
    @staticmethod
    def get_by_ids(kb_ids):
        # Return a list of mock knowledge base objects
        # Each object should have attributes like embd_id, tenant_id
        # as expected by the Retrieval component.
        print(f"Mock KnowledgebaseService.get_by_ids called with {kb_ids}")
        if not kb_ids:
            return []

        mock_kbs = []
        for i, kb_id in enumerate(kb_ids):
            mock_kb = type("MockKB", (), {
                "embd_id": f"dummy_embd_id_{i}",
                "tenant_id": f"dummy_tenant_id_{i}",
                "id": kb_id
            })()
            mock_kbs.append(mock_kb)
        return mock_kbs

    # Add any other methods that might be called, returning default values.
    # For example, if there's a method to get a specific KB:
    # @staticmethod
    # def get(kb_id):
    #     print(f"Mock KnowledgebaseService.get called with {kb_id}")
    #     return type("MockKB", (), {
    #         "embd_id": "dummy_embd_id",
    #         "tenant_id": "dummy_tenant_id",
    #         "id": kb_id
    #     })()

# Example of how it might be used in retrieval.py:
# kbs = KnowledgebaseService.get_by_ids(filtered_kb_ids)
# if not kbs: return Retrieval.be_output("")
# embd_nms = list(set([kb.embd_id for kb in kbs]))
# embd_mdl = LLMBundle(kbs[0].tenant_id, LLMType.EMBEDDING, embd_nms[0])
