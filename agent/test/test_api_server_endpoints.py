# agent/test/test_api_server_endpoints.py
import json
import unittest
from fastapi.testclient import TestClient

# Need to ensure agent.api_server can be imported.
# This might require PYTHONPATH adjustments or running tests in a specific way.
# For now, assume it can be imported if tests are run with `python -m unittest discover` from root.
try:
    from agent.api_server import app
except ModuleNotFoundError:
    # This fallback might be needed if running the test file directly without proper module path setup
    # It's better to run tests using a test runner that handles paths (e.g. `python -m unittest`)
    import sys
    import os
    # Add project root to path - this is a bit of a hack for direct script run
    # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    # print(f"Adjusted sys.path: {sys.path}")
    from agent.api_server import app


class TestWorkflowAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear any in-memory data from previous tests if necessary
        # For now, WORKFLOWS_DB and WORKFLOW_METADATA are global in api_server,
        # so they persist across test client instantiations within the same test run.
        # This is usually fine for one-off tests but can be an issue for larger suites.
        # A proper fixture setup or app factory pattern would be better for isolated tests.
        from agent.api_server import WORKFLOWS_DB, WORKFLOW_METADATA
        WORKFLOWS_DB.clear()
        WORKFLOW_METADATA.clear()


    def test_create_and_run_simple_workflow(self):
        # 1. Define a simple workflow DSL
        simple_dsl = {
            "components": {
                "begin": {
                    "obj": {"component_name": "Begin", "params": {"prologue": "Test API: Hello!"}},
                    "downstream": ["answer_out"], "upstream": []
                },
                "answer_out": {
                    "obj": {"component_name": "Answer", "params": {}},
                    "downstream": [], "upstream": ["begin"]
                }
            },
            "history": [], "messages": [], "reference": [], "path": [], "answer": []
        }

        # 2. Create the workflow via API
        create_payload = {
            "name": "Simple API Test Flow",
            "description": "A basic Begin -> Answer flow for API run testing.",
            "dsl": simple_dsl
        }
        response_create = self.client.post("/workflows", json=create_payload)
        self.assertEqual(response_create.status_code, 201, "Failed to create workflow")
        created_workflow_data = response_create.json()
        self.assertIn("workflow_id", created_workflow_data)
        workflow_id = created_workflow_data["workflow_id"]
        self.assertIn("dsl", created_workflow_data)
        self.assertEqual(created_workflow_data["dsl"]["components"]["begin"]["obj"]["params"]["prologue"], "Test API: Hello!")

        # 3. Run the created workflow
        run_payload = {
            "initial_input": "User says hi to API flow"
            # stream: False is default
        }
        response_run = self.client.post(f"/workflows/{workflow_id}/run", json=run_payload)

        # print("Run response JSON:", response_run.json()) # For debugging if needed

        self.assertEqual(response_run.status_code, 200, f"Failed to run workflow. Response: {response_run.text}")
        run_response_data = response_run.json()

        self.assertIn("workflow_id", run_response_data)
        self.assertEqual(run_response_data["workflow_id"], workflow_id)

        self.assertIn("run_outputs", run_response_data)
        self.assertIsInstance(run_response_data["run_outputs"], list)

        # Check the content of run_outputs
        # For a Begin -> Answer flow with no user input processing by Answer node itself:
        # - First output from Begin (prologue)
        # - Then output from Answer (which would be the prologue again as it's passed through)
        # The canvas.run() yields status updates too. Let's find the final Answer output.

        # The `final_message_content` should capture the last non-status output's content
        self.assertIn("final_message_content", run_response_data)

        # In this simple Begin -> Answer flow, the Begin node's prologue is what the Answer node outputs.
        # The initial_input "User says hi..." is added to history but doesn't change the Answer output
        # in this minimal setup because there's no Generate node using it.
        # The last output from canvas.run() should be from the 'answer_out' node.
        # Its content will be what it received from 'begin'.
        expected_final_content = "Test API: Hello!"
        self.assertEqual(run_response_data["final_message_content"], expected_final_content, "final_message_content did not match expected prologue.")

        # Check the run_outputs list to see if the expected content appeared in any step_output
        found_prologue_in_any_output_step = False
        for item_wrapper in run_response_data["run_outputs"]:
            step_out = item_wrapper.get("step_output", {})
            # Check if the step_output itself is a dict with the content (e.g. status message)
            if isinstance(step_out, dict) and step_out.get("content") == expected_final_content and not step_out.get("running_status"):
                found_prologue_in_any_output_step = True
                break
            # Check if the step_output contains a dataframe_output (e.g. from Begin or Answer node)
            if isinstance(step_out, dict) and "dataframe_output" in step_out:
                df_records = step_out["dataframe_output"]
                if isinstance(df_records, list) and df_records: # Check if it's a list of records
                    # For a simple DataFrame output with one row, one content column
                    if df_records[0].get("content") == expected_final_content:
                        found_prologue_in_any_output_step = True
                        break

        self.assertTrue(found_prologue_in_any_output_step, "Expected prologue was not found as 'content' in any non-status dictionary or in the first record of a 'dataframe_output' within run_outputs.")


    def test_run_nonexistent_workflow(self):
        run_payload = {"initial_input": "test"}
        response_run = self.client.post("/workflows/nonexistent_id/run", json=run_payload)
        self.assertEqual(response_run.status_code, 404)
        self.assertIn("Workflow not found", response_run.json()["detail"])

    # TODO: Add a test for a more complex workflow like retrieval_and_generate
    # This would involve mocking external calls if they were real, but here mocks are already in place.

if __name__ == '__main__':
    # This allows running the tests directly using `python agent/test/test_api_server_endpoints.py`
    # after ensuring PYTHONPATH is set up correctly (e.g. from project root: `PYTHONPATH=. python agent/test/test_api_server_endpoints.py`)
    # However, it's better to use `python -m unittest agent.test.test_api_server_endpoints` from root.
    unittest.main()
