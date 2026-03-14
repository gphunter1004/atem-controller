from pydantic import BaseModel, Field
from typing import Optional, Literal


class KeyerConfig(BaseModel):
    mode:   Literal["keyup", "pip", "off"]
    source: Optional[int]   = Field(None, ge=1, le=4)
    size:   Optional[float] = Field(0.25, ge=0.0, le=1.0)
    pos_x:  Optional[float] = Field(12.0, ge=-16.0, le=16.0)
    pos_y:  Optional[float] = Field(7.0,  ge=-9.0,  le=9.0)


class Preset(BaseModel):
    id:          int
    name:        str
    label:       str
    description: Optional[str] = None
    pgm:         int = Field(..., ge=1, le=4)
    pvw:         Optional[int] = Field(None, ge=1, le=4)
    keyer:       Optional[KeyerConfig] = None
    confirm:     bool = False  # True → 두 번 클릭해야 실행


class PresetCreate(BaseModel):
    name:        str
    label:       str = ""
    description: Optional[str] = None
    pgm:         int = Field(..., ge=1, le=4)
    pvw:         Optional[int] = Field(None, ge=1, le=4)
    keyer:       Optional[KeyerConfig] = None
    confirm:     bool = False
