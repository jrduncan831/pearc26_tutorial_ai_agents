from pydantic import BaseModel, Field

class GenerateCode(BaseModel):
    thoughts: str = Field(..., description="Reasoning about how to solve the coding task")
    code: str = Field(..., description="Python code as a string that solves the task, must include uv install of dependencies")
