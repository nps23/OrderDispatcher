import pydantic


class BasicResponse(pydantic.BaseModel):
    message: str
