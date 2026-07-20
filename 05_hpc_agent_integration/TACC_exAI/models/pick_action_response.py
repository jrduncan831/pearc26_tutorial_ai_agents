# models/pick_action_response.py
from pydantic import BaseModel, Field
from enum import Enum

class PickedActionEnum(str, Enum):
    save_session = "SaveSessionAction"
    summarize_and_reply = "SummarizeAndReplyAction"
    switch_mode = "SwitchModeAction"

class PickActionResponse(BaseModel):
    thoughts: str = Field(
        ..., 
        min_length=20, 
        max_length=1000, 
        description="Reasoning behind selecting the action."
    )
    picked_action: PickedActionEnum = Field(
        ..., 
        description="The chosen action to execute."
    )
