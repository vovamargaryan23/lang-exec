from pydantic import BaseModel


class CodeExecRequestData(BaseModel):
    language: str
    execution_params: str
    code: str
    
    
class CodeExecResponseData(BaseModel):
    stdout: str
    stderr: str
    return_code: int