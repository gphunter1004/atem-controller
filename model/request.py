from pydantic import BaseModel, Field
from typing import Literal

class SourceInput(BaseModel):
    source: int = Field(..., ge=1, le=4, description="소스 번호 (1~4)")

class TransitionStyleInput(BaseModel):
    style: Literal["MIX", "DIP", "WIPE", "STING"]

class PiPConfig(BaseModel):
    source: int   = Field(1,     ge=1,    le=4)
    size:   float = Field(0.25,  ge=0.0,  le=1.0)
    pos_x:  float = Field(12.0,  ge=-16.0, le=16.0)
    pos_y:  float = Field(7.0,   ge=-9.0,  le=9.0)

class PiPMove(BaseModel):
    pos_x: float = Field(..., ge=-16.0, le=16.0)
    pos_y: float = Field(..., ge=-9.0,  le=9.0)