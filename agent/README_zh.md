[English](./README.md) | 简体中文

# Graph Agent Workflow Engine (图代理工作流引擎)

## 简介 (Introduction)

图代理工作流引擎允许使用由节点（组件）和边组成的基于图的结构来创建和执行复杂的工作流。该系统通过在基于JSON的领域特定语言（DSL）中定义工作流，从而支持动态代理行为，包括循环过程。
*(Machine translation for: The Graph Agent Workflow Engine allows for the creation and execution of complex workflows using a graph-based structure composed of nodes (components) and edges. This system enables dynamic agent behaviors, including looped processes, by defining workflows in a JSON-based Domain Specific Language (DSL).)*

此目录包含核心代理引擎、组件定义以及一个测试客户端 (`./test/client.py`)，用于执行DSL文件（示例可在 `./test/dsl_examples/` 中找到）。
*(Machine translation for: This directory contains the core agent engine, component definitions, and a test client (`./test/client.py`) for executing DSL files (examples can be found in `./test/dsl_examples/`).)*

**关于旧版本的说明 (Note on Previous Versions):** 此系统的早期版本包含多租户功能（通过 `TENANT_ID`）和用于 `Retrieval` 组件的数据库支持的知识库。这些功能已被移除，以使引擎更加独立和简化。测试客户端不再需要 `TENANT_ID`。
*(Machine translation for: Earlier versions of this system included multi-tenancy (via `TENANT_ID`) and database-backed knowledge bases for the `Retrieval` component. These features have been removed to make the engine more standalone and streamlined. The test client no longer requires a `TENANT_ID`.)*

### 运行测试客户端 (Running the Test Client)
要运行测试客户端，请确保您的Python环境已配置好 `pyproject.toml` 中定义的依赖项（例如，通过使用 `poetry install`）。
*(Machine translation for: To run the test client, ensure your Python environment is set up with the dependencies defined in `pyproject.toml` (e.g., by using `poetry install`).)*

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
*注意：`client.py` 中的 `-t TENANT_ID` 参数现已废弃，因为租户功能已从核心 `Canvas` 中移除。*
*(Machine translation for: Note: The `-t TENANT_ID` argument in `client.py` is now vestigial as tenant functionality has been removed from the core `Canvas`.)*

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://github.com/infiniflow/ragflow/assets/12318111/05924730-c427-495b-8ee4-90b8b2250681" width="1000"/>
</div>

## 核心工作流组件 (Core Workflow Components)

本节描述了用于构建工作流的核心可用组件。
*(以下中文描述为英文内容的直接复制，需要人工翻译。JSON示例和参数名保留英文以保持与代码一致。)*
*(Machine translation for: This section describes the core components available for building workflows. The following Chinese descriptions are direct copies of the English content and require manual translation. JSON examples and parameter names are kept in English for consistency with the code.)*


### 1. `Begin`

*   **用途 (Purpose):** Marks the starting point of a workflow. It can provide an initial message or prologue.
*   **参数 (Parameters):**
    *   `prologue` (str): The initial message to be output when the workflow starts. Default: "Hi! I'm your smart assistant. What can I do for you?"
    *   `query` (list): A list of predefined parameters/values available globally from the Begin node (e.g., for system-wide settings or initial data). Each item is a dict like `{"key": "param_name", "name": "Parameter Name", "value": "param_value"}`.
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: None.
    *   Output: A DataFrame containing the `prologue` in a "content" column. The parameters in `query` can be accessed by other nodes if they are configured to query `begin@param_name`.

### 2. `Answer`

*   **用途 (Purpose):** Handles interaction points in the workflow.
    *   When upstream to a component that requires user input, it captures the user's message.
    *   When downstream of processing components (like `Generate`), it presents the final output to the user.
*   **参数 (Parameters):**
    *   `post_answers` (list[str]): A list of strings from which one will be randomly chosen and appended to the component's main output. Useful for adding variety or follow-up prompts. Default: `[]`.
*   **用法示例 (Usage Example):**
    ```json
    "user_input_node": {
        "obj": {
            "component_name": "Answer",
            "params": {}
        },
        "downstream": ["processing_node_id"],
        "upstream": ["begin_node_id"]
    },
    "bot_output_node": {
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
*   **输入/输出 (Input/Output):**
    *   Input (as a source for user query): Receives user's textual input from the dialog history.
    *   Input (as a display node): Receives a DataFrame from an upstream component (typically with a "content" column).
    *   Output: The content to be presented to the user (either the captured user input if it's an input node, or the processed content from upstream if it's an output node). If `post_answers` is used, a random choice from it is appended.

### 3. `Switch`

*   **用途 (Purpose):** Routes the workflow to different downstream components based on a set of conditions.
*   **参数 (Parameters):**
    *   `conditions` (list): A list of condition groups. Each group contains:
        *   `logical_operator` (str): `"and"` or `"or"` for combining items within this group.
        *   `items` (list): A list of individual conditions to evaluate. Each item is a dict:
            *   `cpn_id` (str): The ID of the component whose output is being checked. Can also reference `begin@param_key` for Begin node parameters.
            *   `operator` (str): The comparison operator. Supported: `contains`, `not contains`, `start with`, `end with`, `empty`, `not empty`, `=`, `≠`, `>`, `<`, `≥`, `≤`.
            *   `value` (str): The value to compare against.
        *   `to` (str): The component ID to branch to if this condition group evaluates to true.
    *   `end_cpn_id` (str): The default component ID to branch to if none of the `conditions` are met. Default: `"answer:0"` (typically the main answer output node, ensure such a node exists if relying on default).
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: Implicitly takes output from components specified in `cpn_id` within its conditions.
    *   Output: A DataFrame containing a single row with the component ID to branch to in its "content" column.

### 4. `Iteration` & `IterationItem`

*   **用途 (Purpose):**
    *   `Iteration`: Manages a loop over a list of items. The list of items is typically provided as output from an upstream component.
    *   `IterationItem`: Represents the starting point of the sub-workflow that is executed for each item in the list processed by the parent `Iteration` node.
*   **`Iteration` 参数 (Parameters):**
    *   *(No specific parameters beyond standard ones like `output_var_name`)*. The component iterates over the rows of the DataFrame received as input.
*   **`IterationItem` 参数 (Parameters):**
    *   *(No specific parameters beyond standard ones)*.
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   `Iteration` Input: Expects a DataFrame from an upstream component. It iterates row by row.
    *   `Iteration` Output: After all items are processed, it outputs a DataFrame containing the aggregated results (concatenated DataFrames) from each iteration's sub-workflow.
    *   `IterationItem` Input: For each loop, it receives a DataFrame containing a single row corresponding to the current item from the `Iteration` node.
    *   `IterationItem` Output: The output of the sub-workflow starting with `IterationItem` (specifically, the output of the component that links back to the parent `Iteration` node) is collected by `Iteration`.

### 5. `Retrieval`

*   **用途 (Purpose):** Fetches information based on a query. Currently supports (mocked) Tavily web search and a mocked Knowledge Graph (KG). Database-backed knowledge base retrieval has been removed.
*   **参数 (Parameters):**
    *   `tavily_api_key` (str): API key for Tavily. If provided, Tavily search will be attempted (currently mocked).
    *   `use_kg` (bool): If true, includes a mock result from a Knowledge Graph. Default: `false`.
    *   `empty_response` (str): Custom message if no results are found.
    *   `top_n` (int): Number of results for Tavily to fetch.
    *   *(Inactive Parameters: `kb_ids`, `kb_vars`, `similarity_threshold`, `keywords_similarity_weight`, `top_k`, `rerank_id` - these were for the removed DB KB functionality and are currently not used).*
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: Expects a query string, typically from an `Answer` node or another processing node.
    *   Output: A DataFrame with two columns:
        *   `content`: A string summarizing or listing the retrieved information (e.g., "Retrieved information:\n- Mocked Tavily content...").
        *   `chunks`: A JSON string representation of the individual retrieved pieces of information.

### 6. `Generate`

*   **用途 (Purpose):** Interacts with a Language Model (LLM) to generate text. It uses a prompt template that can be populated with inputs from other components or conversation history. (Currently uses a mocked LLM).
*   **参数 (Parameters):**
    *   `llm_id` (str): Identifier for the LLM to use (e.g., "mock_llm_id").
    *   `prompt` (str): The prompt template. Variables can be inserted using `{component_id}` or `{begin@param_key}`. A generic `{input}` placeholder can also be used.
    *   `max_tokens`, `temperature`, `top_p`, `presence_penalty`, `frequency_penalty`: Standard LLM generation parameters.
    *   `cite` (bool): If true and retrieval results (chunks) are available from an upstream `Retrieval` node, attempts to add mock citations to the LLM's answer. Default: `true`.
    *   `llm_enabled_tools` (list): (Currently Inactive) Was for specifying LLM tools/plugins; now logs a warning if used as the plugin system is removed.
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: Takes data from components specified in its prompt template placeholders. Also uses conversation history from the `Canvas`.
    *   Output: A DataFrame with a "content" column containing the LLM's generated text, and potentially a "reference" column if citations are enabled and successful.

### 7. `Relevant`

*   **用途 (Purpose):** Uses an LLM (mocked) to determine if a document (or text from an upstream component) is relevant to the user's query (or another piece of context). Outputs a predefined string ("yes" value or "no" value) which can be used by a `Switch` node.
*   **参数 (Parameters):**
    *   `llm_id` (str): Identifier for the LLM to use.
    *   `prompt` (str): (Optional) A custom prompt for the relevance check. If not provided, a default prompt is used. Can include placeholders like `{input_component_id}` for the document. The user's most recent question is automatically made available to the default prompt.
    *   `query` (list): Specifies inputs to populate the prompt, similar to `Generate`. Often used to explicitly pass the document to be checked if the prompt needs it as a named variable (e.g., `{"component_id": "retrieval_node", "name": "document_to_check"}`).
    *   `yes` (str): The string value to output if the content is deemed relevant. This value is used by `Switch` conditions.
    *   `no` (str): The string value to output if the content is deemed irrelevant.
*   **用法示例 (Usage Example):**
    ```json
    "relevant_check_node": {
        "obj": {
            "component_name": "Relevant",
            "params": {
                "llm_id": "mock_relevance_llm",
                "prompt": "User question: (implicitly included)\\nDocument: {retrieved_doc_node_id}\\nIs the document relevant? Answer yes or no.",
                "query": [{"component_id": "retrieved_doc_node_id", "name":"document_content"}],
                "yes": "proceed_with_document",
                "no": "discard_document"
            }
        },
        "downstream": ["switch_node_id"],
        "upstream": ["retrieved_doc_node_id"]
    }
    ```
*   **输入/输出 (Input/Output):**
    *   Input: Typically takes the document/text to be assessed from an upstream component (often specified via the `query` param or as `{input}` in the prompt if not explicitly named). It also implicitly uses the latest user query from the conversation history for its default prompt.
    *   Output: A DataFrame with a single "content" column containing either the `yes` string or the `no` string from its parameters.

### 8. `Concentrator`

*   **用途 (Purpose):** Gathers and consolidates outputs from multiple upstream branches into a single DataFrame. This is useful after a `Switch` or parallel processing paths converge, or at the end of an `Iteration` loop before further processing.
*   **参数 (Parameters):** (None specific to its core function beyond standard component params)
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: Receives DataFrames from all its direct upstream components.
    *   Output: A single DataFrame that concatenates the rows from all input DataFrames. Typically, these DataFrames should have compatible structures (e.g., a "content" column).

### 9. `Template`

*   **用途 (Purpose):** Formats a string template using inputs from other components or fixed values. Useful for constructing complex prompts, messages, or data structures.
*   **参数 (Parameters):**
    *   `template` (str): The string template with placeholders like `{variable_name}`.
    *   `variables` (list): A list of dictionaries defining how to fill the placeholders. Each dict:
        *   `name` (str): The name of the variable in the `template` (e.g., "variable_name").
        *   `component_id` (str, optional): ID of an upstream component to get the value from (its "content" output).
        *   `value` (str, optional): A fixed string value. (Use `component_id` or `value`, not both for the same variable).
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: Values from components specified in the `variables` list (specifically their "content" column).
    *   Output: A DataFrame with a single "content" column containing the formatted string.

### 10. `Message`

*   **用途 (Purpose):** A simple component to output one or more predefined messages. If multiple messages are provided, one is chosen randomly.
*   **参数 (Parameters):**
    *   `messages` (list[str]): A list of message strings.
*   **用法示例 (Usage Example):**
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
*   **输入/输出 (Input/Output):**
    *   Input: None required for its direct operation.
    *   Output: A DataFrame with a "content" column containing one randomly selected message from the `messages` list.

---

## 旧版信息 (现已过时) (Legacy Information - Now Outdated)

以下部分描述了早期版本中存在但已被移除或显著更改的功能：
*(Machine translation for: The following sections describe features that were present in earlier versions but have been removed or significantly changed:)*

### 租户ID (Tenant ID)
以前，系统使用 `TENANT_ID` 支持多租户。此功能已从 `Canvas` 和组件逻辑中移除，以简化引擎的独立使用。
*(Machine translation for: Previously, the system supported multi-tenancy using a `TENANT_ID`. This has been removed from the `Canvas` and component logic to simplify the engine for standalone use.)*

### Retrieval 组件 - 知识库ID (`kb_ids`) (Retrieval Component - Knowledge Base IDs)
`Retrieval` 组件以前允许指定 `kb_ids` 以从数据库支持的知识库中获取内容。此功能已被移除。`Retrieval` 组件现在主要依赖于（模拟的）Tavily网络搜索和（模拟的）知识图谱。`RetrievalParam` 中的 `kb_ids` 及相关参数不再有效。
*(Machine translation for: The `Retrieval` component previously allowed specifying `kb_ids` to fetch content from database-backed knowledge bases. This functionality has been removed. The `Retrieval` component now primarily relies on (mocked) Tavily web search and a (mocked) Knowledge Graph. The `kb_ids` and related parameters in `RetrievalParam` are no longer active.)*

---
*关于特定组件参数和高级用法的更多详细信息，可以通过检查 `agent/component/` 中组件的源代码及其对应的参数类（例如, `Generate` 的 `GenerateParam`）来找到。*
*(Machine translation for: Further details on specific component parameters and advanced usage can be found by examining the component's source code in `agent/component/` and its corresponding parameter class (e.g., `GenerateParam` for `Generate`).)*
