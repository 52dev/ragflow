# agent/test/test_workflow_builder.py

from agent.workflow_builder import (
    create_workflow,
    add_node,
    connect_nodes,
    set_node_parameters,
    list_available_components
    # Workflow class might be needed if we manipulate workflow.nodes directly for advanced connections
)

def main():
    print("Demonstrating the Workflow Builder API\n")

    # 1. List available components (optional demonstration)
    print("Available components:")
    available_components = list_available_components()
    for component_name in available_components:
        print(f"- {component_name}")
    print("-" * 30)

    # 2. Create a new workflow
    wf = create_workflow(workflow_id="my_example_flow", description="A simple flow built via API")
    print(f"Created workflow: {wf.workflow_id} - {wf.description}")

    # 3. Add nodes
    begin_node = add_node(wf, node_id="begin", component_name="Begin")
    # print(f"Added node: {begin_node.node_id} ({begin_node.component_name})")

    user_answer_node = add_node(wf, node_id="user_input_ans", component_name="Answer")
    # print(f"Added node: {user_answer_node.node_id} ({user_answer_node.component_name})")

    generate_node = add_node(wf, node_id="generate_response", component_name="Generate")
    # print(f"Added node: {generate_node.node_id} ({generate_node.component_name})")

    bot_answer_node = add_node(wf, node_id="bot_output_ans", component_name="Answer")
    # print(f"Added node: {bot_answer_node.node_id} ({bot_answer_node.component_name})")

    print(f"\nTotal nodes in workflow: {len(wf.nodes)}")

    # 4. Set node parameters
    set_node_parameters(wf, "begin", {"prologue": "Welcome to the API-built flow!"})
    set_node_parameters(wf, "generate_response", {
        "llm_id": "mocked_llm_for_api_test",
        "prompt": "User said: {user_input_ans}. Please respond.",
        "temperature": 0.5
    })
    set_node_parameters(wf, "bot_output_ans", {"post_answers": ["Was this helpful?", "Anything else I can do?"]})
    print("\nSet parameters for 'begin', 'generate_response', and 'bot_output_ans' nodes.")

    # 5. Connect nodes
    connect_nodes(wf, "begin", "user_input_ans")
    connect_nodes(wf, "user_input_ans", "generate_response")
    connect_nodes(wf, "generate_response", "bot_output_ans")
    print("\nConnected nodes: begin -> user_input_ans -> generate_response -> bot_output_ans")

    # Verify connections (optional check)
    # print(f"Begin downstream: {wf.get_node('begin').downstream_node_ids}")
    # print(f"Generate upstream: {wf.get_node('generate_response').upstream_node_ids}")


    # 6. Generate the JSON DSL
    dsl_json_output = wf.to_dsl_json(indent=4)
    print("\nGenerated DSL JSON:")
    print(dsl_json_output)
    print("-" * 30)

    # Example of trying to add a non-existent component (should fail)
    print("\nAttempting to add a non-existent component (expecting ValueError):")
    try:
        add_node(wf, "error_node", "NonExistentComponent")
    except ValueError as e:
        print(f"Caught expected error: {e}")

    print("\nWorkflow Builder API demonstration complete.")


if __name__ == "__main__":
    main()
