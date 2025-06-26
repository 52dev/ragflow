# agent/api_server.py
import uuid
from typing import Dict, Any, List, Optional
import logging # Added
import pandas as pd # Added

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field # BaseModel will be used for request/response models

# In-memory storage for workflows
# Key: workflow_id (str)
# Value: Workflow DSL (Dict[str, Any]) - storing the parsed JSON directly
WORKFLOWS_DB: Dict[str, Dict[str, Any]] = {}

# Initialize FastAPI app
app = FastAPI(
    title="Agent Workflow API",
    description="API for creating, managing, and exporting agent workflow DSLs.",
    version="0.1.0"
)

# --- Pydantic Models ---

class WorkflowDSL(BaseModel):
    """Represents the structure of a workflow DSL."""
    components: Dict[str, Any] = Field(..., description="Dictionary of components in the workflow.")
    history: Optional[List[Any]] = Field(default_factory=list)
    messages: Optional[List[Any]] = Field(default_factory=list)
    reference: Optional[List[Any]] = Field(default_factory=list) # Or Dict
    path: Optional[List[Any]] = Field(default_factory=list)
    answer: Optional[List[Any]] = Field(default_factory=list)
    # Add other top-level DSL fields if they exist, e.g., embed_id: Optional[str] = None

    class Config:
        # Allows for extra fields not explicitly defined, useful for flexible params
        extra = "allow"

class WorkflowCreateRequest(BaseModel):
    """Request model for creating a new workflow."""
    # For now, we expect the client to send the full DSL structure.
    # Alternatively, this could take parameters for the workflow_builder API.
    name: Optional[str] = Field(default="Untitled Workflow", description="A user-friendly name for the workflow.")
    description: Optional[str] = Field(default="", description="A brief description of the workflow.")
    dsl: WorkflowDSL = Field(..., description="The workflow DSL content.")


class WorkflowResponse(BaseModel):
    """Response model for a single workflow."""
    workflow_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    dsl: WorkflowDSL

    class Config:
        # For compatibility with ORM mode if we ever use a DB, though not for now.
        # from_attributes = True
        pass


class WorkflowListItem(BaseModel):
    """Response model for listing workflows."""
    workflow_id: str
    name: Optional[str] = None
    description: Optional[str] = None


class ComponentListItem(BaseModel):
    """Response model for listing available components."""
    name: str
    # Potentially add: params_schema: Optional[Dict[str, Any]] = None


class WorkflowRunRequest(BaseModel):
    """Request model for running a workflow."""
    initial_input: str = Field(..., description="The initial user input or question for the workflow.")
    stream: bool = Field(default=False, description="Whether to stream the output. Note: Streaming is not fully implemented in this version for the run endpoint.")
    # Future: Could add a dictionary for other ad-hoc parameters to pass to canvas.run(**kwargs)

class WorkflowOutputItem(BaseModel):
    """Represents a single item yielded by the workflow's run method (non-streaming)."""
    # The canvas.run() yields dicts, often {"content": "...", "running_status": True/False}
    # or just {"content": "...", "reference": ...}
    # Using Dict[str, Any] provides flexibility for what each yielded step contains.
    step_output: Dict[str, Any]

class WorkflowRunResponse(BaseModel):
    """Response model for a non-streaming workflow run."""
    # Returns a list of all items yielded by canvas.run() during its execution.
    # The client can then process this list (e.g., take the last item's 'content' if it's from an Answer node).
    run_outputs: List[WorkflowOutputItem] = Field(description="A list of all output dictionaries yielded by the workflow execution.")
    workflow_id: str
    final_message_content: Optional[str] = Field(None, description="The 'content' from the very last yielded output, if available and applicable (often from an Answer node).")

# --- End Pydantic Models ---

# --- In-memory storage for workflow metadata (name, description) ---
# WORKFLOWS_DB stores the DSL, this can store metadata.
WORKFLOW_METADATA: Dict[str, Dict[str, Optional[str]]] = {}


# --- API Endpoints ---

@app.post("/workflows", response_model=WorkflowResponse, status_code=201)
async def create_workflow_endpoint(workflow_req: WorkflowCreateRequest = Body(...)):
    """
    Creates a new workflow.
    The request body should contain the workflow name, description, and its DSL structure.
    """
    workflow_id = uuid.uuid4().hex
    if workflow_id in WORKFLOWS_DB:
        raise HTTPException(status_code=409, detail="Workflow ID conflict, please try again.")

    # Store the DSL and metadata
    WORKFLOWS_DB[workflow_id] = workflow_req.dsl.model_dump(exclude_unset=True) # Store as dict
    WORKFLOW_METADATA[workflow_id] = {
        "name": workflow_req.name,
        "description": workflow_req.description
    }

    return WorkflowResponse(
        workflow_id=workflow_id,
        name=workflow_req.name,
        description=workflow_req.description,
        dsl=WorkflowDSL(**WORKFLOWS_DB[workflow_id]) # Re-validate/cast for response
    )

@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_endpoint(workflow_id: str):
    """
    Retrieves a specific workflow by its ID.
    """
    if workflow_id not in WORKFLOWS_DB:
        raise HTTPException(status_code=404, detail="Workflow not found")

    metadata = WORKFLOW_METADATA.get(workflow_id, {})
    return WorkflowResponse(
        workflow_id=workflow_id,
        name=metadata.get("name"),
        description=metadata.get("description"),
        dsl=WorkflowDSL(**WORKFLOWS_DB[workflow_id]) # Re-validate/cast for response
    )

@app.put("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow_endpoint(workflow_id: str, workflow_req: WorkflowCreateRequest = Body(...)):
    """
    Updates an existing workflow.
    The request body should contain the new name, description, and DSL structure.
    """
    if workflow_id not in WORKFLOWS_DB:
        raise HTTPException(status_code=404, detail="Workflow not found")

    WORKFLOWS_DB[workflow_id] = workflow_req.dsl.model_dump(exclude_unset=True)
    WORKFLOW_METADATA[workflow_id] = {
        "name": workflow_req.name,
        "description": workflow_req.description
    }

    return WorkflowResponse(
        workflow_id=workflow_id,
        name=workflow_req.name,
        description=workflow_req.description,
        dsl=WorkflowDSL(**WORKFLOWS_DB[workflow_id])
    )

@app.delete("/workflows/{workflow_id}", status_code=204)
async def delete_workflow_endpoint(workflow_id: str):
    """
    Deletes a workflow by its ID.
    """
    if workflow_id not in WORKFLOWS_DB:
        raise HTTPException(status_code=404, detail="Workflow not found")

    del WORKFLOWS_DB[workflow_id]
    if workflow_id in WORKFLOW_METADATA:
        del WORKFLOW_METADATA[workflow_id]
    return # Returns 204 No Content

@app.get("/workflows", response_model=List[WorkflowListItem])
async def list_workflows_endpoint():
    """
    Lists all workflows currently stored in memory.
    """
    items = []
    for wf_id, dsl in WORKFLOWS_DB.items(): # dsl is not used here directly
        metadata = WORKFLOW_METADATA.get(wf_id, {})
        items.append(WorkflowListItem(
            workflow_id=wf_id,
            name=metadata.get("name"),
            description=metadata.get("description")
        ))
    return items

# Import from workflow_builder for /components endpoint
from .workflow_builder import list_available_components
from agent.canvas import Canvas # Added for the run endpoint
import json # For parsing DSL string if needed, though WORKFLOWS_DB stores dicts

@app.post("/workflows/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow_endpoint(workflow_id: str, run_request: WorkflowRunRequest = Body(...)):
    """
    Executes a specified workflow with the given initial input.
    Currently supports non-streaming responses.
    """
    if workflow_id not in WORKFLOWS_DB:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow_dsl_dict = WORKFLOWS_DB[workflow_id]

    # The Canvas expects a JSON string DSL, but we store it as a dict.
    # So, we need to dump it to string first.
    try:
        dsl_string = json.dumps(workflow_dsl_dict)
        canvas = Canvas(dsl=dsl_string) # Canvas expects a string DSL
    except Exception as e:
        # This could happen if the stored DSL dict is somehow invalid for Canvas init
        # or json.dumps fails, though unlikely if it came from WorkflowDSL model.
        logging.error(f"Error initializing Canvas for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize workflow canvas: {str(e)}")

    if run_request.initial_input:
        canvas.add_user_input(run_request.initial_input)

    run_outputs_raw = []
    final_content: Optional[str] = None

    try:
        # Non-streaming execution
        if run_request.stream:
            # For now, we'll treat stream=True as non-streaming and collect all outputs.
            # True streaming response would require StreamingResponse and different handling.
            logging.warning("Streaming requested but not fully implemented for this endpoint yet. Collecting all outputs.")

        for item in canvas.run(stream=False):
            final_yielded_item = item # Keep track of the very last item yielded
            if isinstance(item, dict):
                run_outputs_raw.append(WorkflowOutputItem(step_output=item))
                # Potentially update final_content if it's a non-status dict with content
                if "content" in item and not item.get("running_status"):
                    # This might be overwritten if a DataFrame is the actual last output
                    final_content = str(item["content"])
            elif isinstance(item, pd.DataFrame):
                # Convert DataFrame to a list of dicts for consistent output structure
                # This is likely the actual final output from an Answer node in non-streaming mode
                df_records = item.to_dict(orient='records')
                run_outputs_raw.append(WorkflowOutputItem(step_output={"dataframe_output": df_records}))
                if df_records and "content" in df_records[0]:
                    final_content = str(df_records[0]["content"]) # Assume first row of DF has the relevant content
            else:
                logging.warning(f"Workflow {workflow_id} yielded unexpected type: {type(item)}, value: {item}")
                run_outputs_raw.append(WorkflowOutputItem(step_output={"unknown_output": str(item)}))

    except Exception as e:
        logging.error(f"Error during workflow execution for {workflow_id}: {e}", exc_info=True)
        # Capture the error in the output as well
        error_output = {"error": "Workflow execution failed at canvas level.", "detail": str(e)}
        run_outputs_raw.append(WorkflowOutputItem(step_output=error_output))
        # final_content might remain from before the error, or be None.
        # Consider if we should raise HTTPException here or let the client see the error in run_outputs.
        # For now, returning outputs including the error.
        # raise HTTPException(status_code=500, detail=f"Workflow execution error: {str(e)}")

    # Refined final_content extraction from the very last yielded item
    if final_yielded_item is not None:
        if isinstance(final_yielded_item, pd.DataFrame):
            if not final_yielded_item.empty and "content" in final_yielded_item.columns:
                final_content = str(final_yielded_item["content"].iloc[0])
        elif isinstance(final_yielded_item, dict):
            if "content" in final_yielded_item and not final_yielded_item.get("running_status"):
                final_content = str(final_yielded_item["content"])
        # else final_content remains as it was (None or from a previous dict)

    return WorkflowRunResponse(
        workflow_id=workflow_id,
        run_outputs=run_outputs_raw, # This is List[WorkflowOutputItem]
        final_message_content=final_content
    )


@app.get("/components", response_model=List[ComponentListItem])
async def get_available_components_endpoint():
    """
    Lists all available components that can be used in workflows.
    """
    component_names = list_available_components()
    return [{"name": name} for name in component_names]


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Agent Workflow API. See /docs for available endpoints."}

# Example of how list_available_components might be integrated later:
# from .workflow_builder import list_available_components
# @app.get("/components", response_model=List[ComponentListItem])
# async def get_available_components():
#     components = list_available_components()
#     return [{"name": name} for name in components]

if __name__ == "__main__":
    import uvicorn
    # This is for local development/testing if you run this file directly
    # For production, you'd typically use: uvicorn agent.api_server:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
