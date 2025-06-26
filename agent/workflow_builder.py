# agent/workflow_builder.py
"""
Provides an API for programmatically creating and manipulating agent workflow DSLs.

This module allows users to define workflow structures (nodes, connections, parameters)
using Python objects and then export them to the JSON DSL format recognized by the
agent's Canvas execution engine.
"""
from typing import Optional, Dict, List, Any
import json
import logging # Added for logging in _load_available_components

class WorkflowNode:
    """
    Represents a single node (component instance) in the workflow graph.
    """
    def __init__(self,
                 node_id: str,
                 component_name: str,
                 params: Optional[Dict[str, Any]] = None,
                 parent_id: Optional[str] = None):
        """
        Initializes a WorkflowNode.

        Args:
            node_id: The unique identifier for this node.
            component_name: The name of the component this node represents (e.g., "Generate", "Retrieval").
            params: An optional dictionary of parameters for this component.
            parent_id: Optional ID of a parent node, used for components like IterationItem.

        Raises:
            ValueError: If node_id or component_name is empty or not a string.
        """
        if not node_id or not isinstance(node_id, str):
            raise ValueError("node_id must be a non-empty string.")
        if not component_name or not isinstance(component_name, str):
            raise ValueError("component_name must be a non-empty string.")

        self.node_id: str = node_id
        self.component_name: str = component_name
        self.params: Dict[str, Any] = params if params is not None else {}

        # These will be managed by the Workflow class when connections are made,
        # but are stored here for DSL generation.
        self.upstream_node_ids: List[str] = []
        self.downstream_node_ids: List[str] = []

        self.parent_id: Optional[str] = parent_id

    def to_dsl_dict(self) -> Dict[str, Any]:
        """
        Converts this node into the dictionary structure expected in the DSL's "components" section.
        """
        return {
            "obj": {
                "component_name": self.component_name,
                "params": self.params
            },
            "downstream": self.downstream_node_ids,
            "upstream": self.upstream_node_ids,
            "parent_id": self.parent_id or "" # DSL expects empty string if no parent
        }

    def __repr__(self) -> str:
        return f"WorkflowNode(node_id='{self.node_id}', component_name='{self.component_name}')"


class Workflow:
    """
    Represents the entire workflow graph and its associated metadata.
    """
    def __init__(self,
                 workflow_id: str = "default_workflow",
                 description: str = "A workflow created programmatically."):
        self.workflow_id: str = workflow_id
        self.description: str = description
        self.nodes: Dict[str, WorkflowNode] = {}

        # These attributes mirror the top-level keys in the DSL JSON.
        # besides "components". For now, they are kept minimal as the focus is on structure.
        self.history: List[Any] = []
        self.messages: List[Any] = []
        self.reference: List[Any] = [] # Or dict, depending on actual use
        self.path: List[Any] = []
        self.answer: List[Any] = [] # Queue for answer components

    def add_node_object(self, node: WorkflowNode):
        """Adds an already created WorkflowNode object."""
        if node.node_id in self.nodes:
            raise ValueError(f"Node with ID '{node.node_id}' already exists in the workflow.")
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        return self.nodes.get(node_id)

    def to_dsl_dict(self) -> Dict[str, Any]:
        """
        Converts the entire workflow into the DSL dictionary format.
        """
        dsl_components = {}
        for node_id, node_obj in self.nodes.items():
            dsl_components[node_id] = node_obj.to_dsl_dict()

        return {
            "components": dsl_components,
            "history": self.history,
            "messages": self.messages,
            "reference": self.reference,
            "path": self.path,
            "answer": self.answer
            # Potentially add other top-level DSL fields if needed, e.g., "embed_id"
        # For now, keeping them as per the current Canvas structure.
        }

    def to_dsl_json(self, indent: Optional[int] = 4) -> str:
        """
        Converts the workflow to its JSON DSL string representation.

        Args:
            indent: The indentation level for pretty-printing the JSON.

        Returns:
            A JSON string representing the workflow DSL.
        """
        return json.dumps(self.to_dsl_dict(), indent=indent, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"Workflow(id='{self.workflow_id}', nodes={len(self.nodes)})"

# Placeholder for available components - to be implemented in a later step
_AVAILABLE_COMPONENTS = {}

def _load_available_components():
    """
    (Helper function, to be fully implemented later)
    Dynamically loads available component names and their parameter classes
    from agent.component.__init__.py.
    """
    global _AVAILABLE_COMPONENTS
    if _AVAILABLE_COMPONENTS: # Already loaded
        return

    try:
        from agent.component import __all__ as component_names_and_params
        from agent.component import component_class

        # Filter out Param classes and component_class function itself
        component_names = [
            name for name in component_names_and_params
            if not name.endswith("Param") and name != "component_class"
        ]

        for name in component_names:
            try:
                # Check if it's a valid component by trying to get its Param class
                param_class_name = name + "Param"
                if param_class_name in component_names_and_params:
                     _AVAILABLE_COMPONENTS[name] = {} # Store it; more details later if needed
            except Exception as e:
                print(f"Warning: Could not fully inspect component '{name}': {e}")

        if not _AVAILABLE_COMPONENTS:
             print("Warning: No components loaded by _load_available_components.")

    except ImportError:
        print("Warning: Could not import from agent.component to load available components.")
        # Fallback or default list if dynamic import fails in some contexts
        _AVAILABLE_COMPONENTS = {
            "Begin": {}, "Answer": {}, "Generate": {}, "Retrieval": {},
            "Switch": {}, "Relevant": {}, "KeywordExtract": {}, "Message": {},
            "Concentrator": {}, "Template": {}, "Iteration": {}, "IterationItem": {}
            # Add other known retained components here as a fallback
        }
    # print(f"Loaded components: {_AVAILABLE_COMPONENTS.keys()}")


# Load components when module is loaded (called at the end of the file now)


# --- Utility Functions ---

def list_available_components() -> List[str]:
    """
    Returns a list of available component names.
    Ensures components are loaded before returning.
    """
    if not _AVAILABLE_COMPONENTS:
        _load_available_components()
    return list(_AVAILABLE_COMPONENTS.keys())


# --- Workflow Management Functions ---

def create_workflow(workflow_id: str = "new_workflow", description: str = "A new workflow") -> Workflow:
    """
    Creates and returns a new, empty Workflow object.
    """
    return Workflow(workflow_id=workflow_id, description=description)

def add_node(workflow: Workflow, node_id: str, component_name: str, params: Optional[Dict[str, Any]] = None) -> WorkflowNode:
    """
    Adds a new node to the workflow.
    Validates if the component_name is known (basic check for now).
    Returns the created WorkflowNode.
    """
    if component_name not in _AVAILABLE_COMPONENTS:
        # Attempt to reload components if the list is empty, in case it wasn't loaded properly at module init
        if not _AVAILABLE_COMPONENTS:
            _load_available_components()
            if component_name not in _AVAILABLE_COMPONENTS:
                 raise ValueError(f"Component '{component_name}' is not recognized. Available (or fallback): {list(_AVAILABLE_COMPONENTS.keys())}")
        else: # Component not found even after load attempt
            raise ValueError(f"Component '{component_name}' is not recognized. Available: {list(_AVAILABLE_COMPONENTS.keys())}")


    if workflow.get_node(node_id):
        raise ValueError(f"Node with ID '{node_id}' already exists.")

    node = WorkflowNode(node_id=node_id, component_name=component_name, params=params)
    workflow.add_node_object(node)
    return node

def remove_node(workflow: Workflow, node_id: str):
    """
    Removes a node from the workflow and cleans up its connections.
    """
    node_to_remove = workflow.get_node(node_id)
    if not node_to_remove:
        raise ValueError(f"Node with ID '{node_id}' not found in workflow.")

    # Remove connections from upstream nodes
    for upstream_id in list(node_to_remove.upstream_node_ids): # Iterate over a copy
        upstream_node = workflow.get_node(upstream_id)
        if upstream_node and node_id in upstream_node.downstream_node_ids:
            upstream_node.downstream_node_ids.remove(node_id)

    # Remove connections from downstream nodes
    for downstream_id in list(node_to_remove.downstream_node_ids): # Iterate over a copy
        downstream_node = workflow.get_node(downstream_id)
        if downstream_node and node_id in downstream_node.upstream_node_ids:
            downstream_node.upstream_node_ids.remove(node_id)

    # Remove parent relationship if this node was a child
    # (No explicit children list on parent, parent_id is on child)

    # Remove if this node was a parent to others
    for other_node_id, other_node in workflow.nodes.items():
        if other_node.parent_id == node_id:
            other_node.parent_id = None # Or handle as error/warning if parent removal invalidates child

    del workflow.nodes[node_id]

def connect_nodes(workflow: Workflow, upstream_node_id: str, downstream_node_id: str):
    """
    Connects an upstream node to a downstream node.
    Updates downstream_node_ids for the upstream node and upstream_node_ids for the downstream node.
    """
    upstream_node = workflow.get_node(upstream_node_id)
    downstream_node = workflow.get_node(downstream_node_id)

    if not upstream_node:
        raise ValueError(f"Upstream node '{upstream_node_id}' not found.")
    if not downstream_node:
        raise ValueError(f"Downstream node '{downstream_node_id}' not found.")

    if downstream_node_id not in upstream_node.downstream_node_ids:
        upstream_node.downstream_node_ids.append(downstream_node_id)
    if upstream_node_id not in downstream_node.upstream_node_ids:
        downstream_node.upstream_node_ids.append(upstream_node_id)

def disconnect_nodes(workflow: Workflow, upstream_node_id: str, downstream_node_id: str):
    """
    Disconnects an upstream node from a downstream node.
    """
    upstream_node = workflow.get_node(upstream_node_id)
    downstream_node = workflow.get_node(downstream_node_id)

    if upstream_node and downstream_node_id in upstream_node.downstream_node_ids:
        upstream_node.downstream_node_ids.remove(downstream_node_id)
    else:
        print(f"Warning: Downstream node '{downstream_node_id}' not found in upstream node '{upstream_node_id}' connections or upstream node missing.")

    if downstream_node and upstream_node_id in downstream_node.upstream_node_ids:
        downstream_node.upstream_node_ids.remove(upstream_node_id)
    else:
        print(f"Warning: Upstream node '{upstream_node_id}' not found in downstream node '{downstream_node_id}' connections or downstream node missing.")


def set_node_parameters(workflow: Workflow, node_id: str, params_dict: Dict[str, Any]):
    """
    Sets or updates the parameters for a given node.
    The provided params_dict will update existing params or add new ones.
    """
    node = workflow.get_node(node_id)
    if not node:
        raise ValueError(f"Node with ID '{node_id}' not found.")
    if not isinstance(params_dict, dict):
        raise TypeError("params_dict must be a dictionary.")

    node.params.update(params_dict) # Update existing params with new values

def set_node_parent(workflow: Workflow, node_id: str, parent_node_id: Optional[str]):
    """
    Sets the parent_id for a node (typically for IterationItem).
    If parent_node_id is None, it clears the parent.
    """
    node = workflow.get_node(node_id)
    if not node:
        raise ValueError(f"Node with ID '{node_id}' not found.")

    if parent_node_id is not None:
        parent_node = workflow.get_node(parent_node_id)
        if not parent_node:
            raise ValueError(f"Parent node with ID '{parent_node_id}' not found.")
        # Optional: Check if parent_node is an 'Iteration' component
        # if parent_node.component_name != "Iteration":
        #     raise ValueError(f"Node '{parent_node_id}' is not an Iteration component and cannot be a parent.")

    node.parent_id = parent_node_id
