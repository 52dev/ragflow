# agent/api_server.py
import uuid
from typing import Dict, Any, List, Optional

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
