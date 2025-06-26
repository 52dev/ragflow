English | [简体中文](./README_zh.md)

# Graph Agent Workflow Engine

## Introduction

The Graph Agent Workflow Engine allows for the creation and execution of complex workflows using a graph-based structure composed of nodes (components) and edges. This system enables dynamic agent behaviors, including looped processes, by defining workflows in a JSON-based Domain Specific Language (DSL).

This directory contains the core agent engine, component definitions, and a test client (`./test/client.py`) for executing DSL files (examples can be found in `./test/dsl_examples/`).

**Note on Previous Versions:** Earlier versions of this system included multi-tenancy (via `TENANT_ID`) and database-backed knowledge bases for the `Retrieval` component. These features have been removed to make the engine more standalone and streamlined. The test client no longer requires a `TENANT_ID`.

### Running the Test Client
To run the test client, ensure your Python environment is set up with the dependencies defined in `pyproject.toml` (e.g., by using `poetry install`).

```bash
python -m agent.test.client -h
usage: client.py [-h] [-s DSL] [-t TENANT_ID] [-m] [-q QUESTION]

options:
  -h, --help            show this help message and exit
  -s DSL, --dsl DSL     input dsl (default: agent/test/dsl_examples/retrieval_and_generate.json)
  -t TENANT_ID, --tenant_id TENANT_ID
                        Tenant ID (default: test_tenant)
  -m, --stream          Stream output (default: False)
  -q QUESTION, --question QUESTION
                        Initial question for non-interactive run (default: Hello)
```
*Note: The `-t TENANT_ID` argument in `client.py` is now vestigial as tenant functionality has been removed from the core `Canvas`.*

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://github.com/infiniflow/ragflow/assets/12318111/79179c5e-d4d6-464a-b6c4-5721cb329899" width="1000"/>
</div>

## Core Workflow Components

This section describes the core components available for building workflows.

### 1. `Begin`

*   **Purpose:** Marks the starting point of a workflow. It can provide an initial message or prologue.
*   **Parameters:**
    *   `prologue` (str): The initial message to be output when the workflow starts. Default: "Hi! I'm your smart assistant. What can I do for you?"
    *   `query` (list): A list of predefined parameters/values available globally from the Begin node (e.g., for system-wide settings or initial data). Each item is a dict like `{"key": "param_name", "name": "Parameter Name", "value": "param_value"}`.
*   **Usage Example:**
    ```json
    "begin_node_id": {
        "obj": {
            "component_name": "Begin",
            "params": {
                "prologue": "Welcome! How can I assist you today?",
                "query": [
                    {"key": "default_language", "name": "Default Language", "value": "en"}
                ]
            }
        },
        "downstream": ["next_node_id"],
        "upstream": []
    }
    ```
*   **Input/Output:**
    *   Input: None.
    *   Output: A DataFrame containing the `prologue` in a "content" column. The parameters in `query` can be accessed by other nodes if they are configured to query `begin@param_name`.

### 2. `Answer`

*   **Purpose:** Handles interaction points in the workflow.
    *   When upstream to a component that requires user input, it captures the user's message.
    *   When downstream of processing components (like `Generate`), it presents the final output to the user.
*   **Parameters:**
    *   `post_answers` (list[str]): A list of strings from which one will be randomly chosen and appended to the component's main output. Useful for adding variety or follow-up prompts. Default: `[]`.
*   **Usage Example:**
    ```json
    "user_input_node": { // Capturing user input
        "obj": {
            "component_name": "Answer",
            "params": {}
        },
        "downstream": ["processing_node_id"],
        "upstream": ["begin_node_id"]
    },
    "bot_output_node": { // Presenting bot's response
        "obj": {
            "component_name": "Answer",
            "params": {
                "post_answers": ["Anything else?", "Can I help with another question?"]
            }
        },
        "downstream": [],
        "upstream": ["generate_node_id"]
    }
    ```
*   **Input/Output:**
    *   Input (as a source for user query): Receives user's textual input from the dialog history.
    *   Input (as a display node): Receives a DataFrame from an upstream component (typically with a "content" column).
    *   Output: The content to be presented to the user (either the captured user input if it's an input node, or the processed content from upstream if it's an output node). If `post_answers` is used, a random choice from it is appended.

### 3. `Switch`

*   **Purpose:** Routes the workflow to different downstream components based on a set of conditions.
*   **Parameters:**
    *   `conditions` (list): A list of condition groups. Each group contains:
        *   `logical_operator` (str): `"and"` or `"or"` for combining items within this group.
        *   `items` (list): A list of individual conditions to evaluate. Each item is a dict:
            *   `cpn_id` (str): The ID of the component whose output is being checked. Can also reference `begin@param_key` for Begin node parameters.
            *   `operator` (str): The comparison operator. Supported: `contains`, `not contains`, `start with`, `end with`, `empty`, `not empty`, `=`, `≠`, `>`, `<`, `≥`, `≤`.
            *   `value` (str): The value to compare against.
        *   `to` (str): The component ID to branch to if this condition group evaluates to true.
    *   `end_cpn_id` (str): The default component ID to branch to if none of the `conditions` are met. Default: `"answer:0"` (typically the main answer output node, ensure such a node exists if relying on default).
*   **Usage Example:**
    ```json
    "switch_node_id": {
        "obj": {
            "component_name": "Switch",
            "params": {
                "conditions": [
                    {
                        "logical_operator": "and",
                        "items": [
                            {"cpn_id": "relevant_node_id", "operator": "=", "value": "is_relevant"}
                        ],
                        "to": "process_relevant_path_node_id"
                    },
                    {
                        "logical_operator": "or",
                        "items": [
                            {"cpn_id": "check1_node_id", "operator": "contains", "value": "error"},
                            {"cpn_id": "check2_node_id", "operator": "=", "value": "failed"}
                        ],
                        "to": "handle_error_node_id"
                    }
                ],
                "end_cpn_id": "default_path_node_id"
            }
        },
        "downstream": ["process_relevant_path_node_id", "handle_error_node_id", "default_path_node_id"],
        "upstream": ["relevant_node_id", "check1_node_id", "check2_node_id"]
    }
    ```
*   **Input/Output:**
    *   Input: Implicitly takes output from components specified in `cpn_id` within its conditions.
    *   Output: A DataFrame containing a single row with the component ID to branch to in its "content" column.

### 4. `Iteration` & `IterationItem`

*   **Purpose:**
    *   `Iteration`: Manages a loop over a list of items. The list of items is typically provided as output from an upstream component.
    *   `IterationItem`: Represents the starting point of the sub-workflow that is executed for each item in the list processed by the parent `Iteration` node.
*   **`Iteration` Parameters:**
    *   *(No specific parameters beyond standard ones like `output_var_name`)*. The component iterates over the rows of the DataFrame received as input.
*   **`IterationItem` Parameters:**
    *   *(No specific parameters beyond standard ones)*.
*   **Usage Example:**
    ```json
    "source_for_iteration": {
        "obj": {"component_name": "Retrieval", "params": {"tavily_api_key":"mock_key", "query": "list of items"}},
        "downstream": ["loop_manager"], "upstream": ["user_input"]
    },
    "loop_manager": {
        "obj": {
            "component_name": "Iteration",
            "params": {}
        },
        "downstream": ["process_each_item_start", "collect_results"],
        "upstream": ["source_for_iteration"]
    },
    "process_each_item_start": {
        "obj": {
            "component_name": "IterationItem",
            "params": {}
        },
        "downstream": ["generate_for_item"],
        "upstream": ["loop_manager"],
        "parent_id": "loop_manager"
    },
    "generate_for_item": {
        "obj": {
            "component_name": "Generate",
            "params": {"llm_id": "mock_llm", "prompt": "Processing item: {process_each_item_start}"}
        },
        "downstream": ["loop_manager"],
        "upstream": ["process_each_item_start"],
        "parent_id": "loop_manager"
    },
    "collect_results": {
        "obj": {
            "component_name": "Concentrator",
            "params": {}
        },
        "downstream": ["final_answer"],
        "upstream": ["loop_manager"]
    }
    ```
*   **Input/Output:**
    *   `Iteration` Input: Expects a DataFrame from an upstream component. It iterates row by row.
    *   `Iteration` Output: After all items are processed, it outputs a DataFrame containing the aggregated results (concatenated DataFrames) from each iteration's sub-workflow.
    *   `IterationItem` Input: For each loop, it receives a DataFrame containing a single row corresponding to the current item from the `Iteration` node.
    *   `IterationItem` Output: The output of the sub-workflow starting with `IterationItem` (specifically, the output of the component that links back to the parent `Iteration` node) is collected by `Iteration`.

### 5. `Retrieval`

*   **Purpose:** Fetches information based on a query. Currently supports (mocked) Tavily web search and a mocked Knowledge Graph (KG). Database-backed knowledge base retrieval has been removed.
*   **Parameters:**
    *   `tavily_api_key` (str): API key for Tavily. If provided, Tavily search will be attempted (currently mocked).
    *   `use_kg` (bool): If true, includes a mock result from a Knowledge Graph. Default: `false`.
    *   `empty_response` (str): Custom message if no results are found.
    *   `top_n` (int): Number of results for Tavily to fetch.
    *   *(Inactive Parameters: `kb_ids`, `kb_vars`, `similarity_threshold`, `keywords_similarity_weight`, `top_k`, `rerank_id` - these were for the removed DB KB functionality and are currently not used).*
*   **Usage Example:**
    ```json
    "retrieval_node_id": {
        "obj": {
            "component_name": "Retrieval",
            "params": {
                "tavily_api_key": "your_tavily_api_key_or_mock",
                "use_kg": true,
                "top_n": 3,
                "empty_response": "Sorry, I couldn't find specific information on that."
            }
        },
        "downstream": ["generate_node_id"],
        "upstream": ["user_input_node"]
    }
    ```
*   **Input/Output:**
    *   Input: Expects a query string, typically from an `Answer` node or another processing node.
    *   Output: A DataFrame with two columns:
        *   `content`: A string summarizing or listing the retrieved information (e.g., "Retrieved information:\n- Mocked Tavily content...").
        *   `chunks`: A JSON string representation of the individual retrieved pieces of information.

### 6. `Generate`

*   **Purpose:** Interacts with a Language Model (LLM) to generate text. It uses a prompt template that can be populated with inputs from other components or conversation history. (Currently uses a mocked LLM).
*   **Parameters:**
    *   `llm_id` (str): Identifier for the LLM to use (e.g., "mock_llm_id").
    *   `prompt` (str): The prompt template. Variables can be inserted using `{component_id}` or `{begin@param_key}`. A generic `{input}` placeholder can also be used.
    *   `max_tokens`, `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`: Standard LLM generation parameters.
    *   `cite` (bool): If true and retrieval results (chunks) are available from an upstream `Retrieval` node, attempts to add mock citations to the LLM's answer. Default: `true`.
    *   `llm_enabled_tools` (list): (Currently Inactive) Was for specifying LLM tools/plugins; now logs a warning if used as the plugin system is removed.
*   **Usage Example:**
    ```json
    "generate_node_id": {
        "obj": {
            "component_name": "Generate",
            "params": {
                "llm_id": "default_mock_llm",
                "prompt": "User asked: {user_input_node_id}\\nBased on this context: {retrieval_node_id}\\nPlease answer the user's question.",
                "temperature": 0.7,
                "cite": true
            }
        },
        "downstream": ["bot_output_node_id"],
        "upstream": ["user_input_node_id", "retrieval_node_id"]
    }
    ```
*   **Input/Output:**
    *   Input: Takes data from components specified in its prompt template placeholders. Also uses conversation history from the `Canvas`.
    *   Output: A DataFrame with a "content" column containing the LLM's generated text, and potentially a "reference" column if citations are enabled and successful.

### 7. `Relevant`

*   **Purpose:** Uses an LLM (mocked) to determine if a document (or text from an upstream component) is relevant to the user's query (or another piece of context). Outputs a predefined string ("yes" value or "no" value) which can be used by a `Switch` node.
*   **Parameters:**
    *   `llm_id` (str): Identifier for the LLM to use.
    *   `prompt` (str): (Optional) A custom prompt for the relevance check. If not provided, a default prompt is used. Can include placeholders like `{input_component_id}` for the document. The user's most recent question is automatically made available to the default prompt.
    *   `query` (list): Specifies inputs to populate the prompt, similar to `Generate`. Often used to explicitly pass the document to be checked if the prompt needs it as a named variable (e.g., `{"component_id": "retrieval_node", "name": "document_to_check"}`).
    *   `yes` (str): The string value to output if the content is deemed relevant. This value is used by `Switch` conditions.
    *   `no` (str): The string value to output if the content is deemed irrelevant.
*   **Usage Example:**
    ```json
    "relevant_check_node": {
        "obj": {
            "component_name": "Relevant",
            "params": {
                "llm_id": "mock_relevance_llm",
                "prompt": "User question: (implicitly included)\\nDocument: {retrieved_doc_node_id}\\nIs the document relevant? Answer yes or no.",
                "query": [{"component_id": "retrieved_doc_node_id", "name":"document_content"}], // Example if prompt uses {document_content}
                "yes": "proceed_with_document",
                "no": "discard_document"
            }
        },
        "downstream": ["switch_node_id"],
        "upstream": ["retrieved_doc_node_id"]
    }
    ```
*   **Input/Output:**
    *   Input: Typically takes the document/text to be assessed from an upstream component (often specified via the `query` param or as `{input}` in the prompt if not explicitly named). It also implicitly uses the latest user query from the conversation history for its default prompt.
    *   Output: A DataFrame with a single "content" column containing either the `yes` string or the `no` string from its parameters.

### 8. `Concentrator`

*   **Purpose:** Gathers and consolidates outputs from multiple upstream branches into a single DataFrame. This is useful after a `Switch` or parallel processing paths converge, or at the end of an `Iteration` loop before further processing.
*   **Parameters:** (None specific to its core function beyond standard component params)
*   **Usage Example:**
    ```json
    "concentrator_node": {
        "obj": {
            "component_name": "Concentrator",
            "params": {}
        },
        "downstream": ["final_processing_node_id"],
        "upstream": ["path_A_output_node", "path_B_output_node", "iteration_loop_output_node"]
    }
    ```
*   **Input/Output:**
    *   Input: Receives DataFrames from all its direct upstream components.
    *   Output: A single DataFrame that concatenates the rows from all input DataFrames. Typically, these DataFrames should have compatible structures (e.g., a "content" column).

### 9. `Template`

*   **Purpose:** Formats a string template using inputs from other components or fixed values. Useful for constructing complex prompts, messages, or data structures.
*   **Parameters:**
    *   `template` (str): The string template with placeholders like `{variable_name}`.
    *   `variables` (list): A list of dictionaries defining how to fill the placeholders. Each dict:
        *   `name` (str): The name of the variable in the `template` (e.g., "variable_name").
        *   `component_id` (str, optional): ID of an upstream component to get the value from (its "content" output).
        *   `value` (str, optional): A fixed string value. (Use `component_id` or `value`, not both for the same variable).
*   **Usage Example:**
    ```json
    "format_message_node": {
        "obj": {
            "component_name": "Template",
            "params": {
                "template": "User: {user_query_content}\\nSummary: {summary_from_generate}\\nCategory: {fixed_category}",
                "variables": [
                    {"name": "user_query_content", "component_id": "actual_user_query_node_id"},
                    {"name": "summary_from_generate", "component_id": "actual_summary_node_id"},
                    {"name": "fixed_category", "value": "General Inquiry"}
                ]
            }
        },
        "downstream": ["generate_node_id"],
        "upstream": ["actual_user_query_node_id", "actual_summary_node_id"]
    }
    ```
*   **Input/Output:**
    *   Input: Values from components specified in the `variables` list (specifically their "content" column).
    *   Output: A DataFrame with a single "content" column containing the formatted string.

### 10. `Message`

*   **Purpose:** A simple component to output one or more predefined messages. If multiple messages are provided, one is chosen randomly.
*   **Parameters:**
    *   `messages` (list[str]): A list of message strings.
*   **Usage Example:**
    ```json
    "static_reply_node": {
        "obj": {
            "component_name": "Message",
            "params": {
                "messages": ["Okay, I understand.", "Got it!", "Acknowledged."]
            }
        },
        "downstream": ["next_node_id"],
        "upstream": ["previous_node_id"]
    }
    ```
*   **Input/Output:**
    *   Input: None required for its direct operation.
    *   Output: A DataFrame with a "content" column containing one randomly selected message from the `messages` list.

---

## Legacy Information (Now Outdated)

The following sections describe features that were present in earlier versions but have been removed or significantly changed:

### Tenant ID
Previously, the system supported multi-tenancy using a `TENANT_ID`. This has been removed from the `Canvas` and component logic to simplify the engine for standalone use.

### Retrieval Component - Knowledge Base IDs (`kb_ids`)
The `Retrieval` component previously allowed specifying `kb_ids` to fetch content from database-backed knowledge bases. This functionality has been removed. The `Retrieval` component now primarily relies on (mocked) Tavily web search and a (mocked) Knowledge Graph. The `kb_ids` and related parameters in `RetrievalParam` are no longer active.

---
*Further details on specific component parameters and advanced usage can be found by examining the component's source code in `agent/component/` and its corresponding parameter class (e.g., `GenerateParam` for `Generate`).*

## Programmatic Workflow Creation (Workflow Builder API)

For advanced users or automation, a Python API is available to programmatically construct and export workflow DSLs. This can be found in `agent/workflow_builder.py`.

### Key Features:
*   **Object-Oriented Design:** Define workflows using `Workflow` and `WorkflowNode` Python objects.
*   **Helper Functions:** Easily add nodes, set parameters, and connect nodes.
*   **DSL Export:** Convert your Python workflow definition into the executable JSON DSL format.
*   **Component Listing:** List available components for use in your workflows.

### Basic Usage Example:

```python
# From agent.test.test_workflow_builder import (example)
from agent.workflow_builder import (
    create_workflow,
    add_node,
    connect_nodes,
    set_node_parameters,
    list_available_components
)

# List components
print(list_available_components())

# Create a workflow
wf = create_workflow(workflow_id="my_api_flow", description="Flow built via Python API")

# Add nodes
add_node(wf, "begin", "Begin", params={"prologue": "API Flow Started!"})
add_node(wf, "user_in", "Answer")
add_node(wf, "gen_response", "Generate", params={
    "llm_id": "mock_llm",
    "prompt": "User said: {user_in}. Respond."
})
add_node(wf, "bot_out", "Answer")

# Connect nodes
connect_nodes(wf, "begin", "user_in")
connect_nodes(wf, "user_in", "gen_response")
connect_nodes(wf, "gen_response", "bot_out")

# Export to JSON DSL
dsl_json = wf.to_dsl_json()
print(dsl_json)
```
This API provides a more structured way to generate complex DSLs, especially useful for dynamic workflow generation or integration into other Python applications.
