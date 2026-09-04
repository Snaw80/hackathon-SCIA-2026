from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Actor = Literal["developer", "client", "sales", "security"]


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    expected_version: int = Field(ge=0, le=6)
    actions: list[str] = Field(default_factory=list, max_length=2)

    @field_validator("actions")
    @classmethod
    def unique_actions(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("A decision cannot be selected twice.")
        return value


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    expected_version: int = Field(ge=0, le=6)
    command: str = Field(min_length=1, max_length=1000)

    @field_validator("command")
    @classmethod
    def command_is_not_whitespace(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tell the team what you want to do.")
        return value


class CommandInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=300)
    actions: list[str] = Field(default_factory=list, max_length=2)
    confidence: Literal["clear", "ambiguous"]
    reason: str | None = Field(default=None, max_length=300)

    @field_validator("actions")
    @classmethod
    def unique_actions(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("An action cannot be interpreted twice.")
        return value


class AgentIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=40)
    message: str = Field(default="", max_length=500)
    recipient: Literal["player", "developer", "client", "sales", "security"] = "player"
    fact_ids: list[str] = Field(default_factory=list, max_length=4)
