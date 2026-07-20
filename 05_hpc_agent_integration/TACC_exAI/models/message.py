from pydantic import BaseModel, Field

class Message(BaseModel):
    thoughts: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Your thoughts as you think through what your message to the user should be."
    )
    contents: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Your message to the user or the content they asked you to create."
    )
