from pydantic import BaseModel, Field

class Summary(BaseModel):
    thoughts: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Your thoughts as you think through how best to summarize the input."
    )
    summary: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Your summary of the input."
    )
