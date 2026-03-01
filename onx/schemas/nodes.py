from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from onx.schemas.common import ONXBaseModel


class NodeRoleValue(StrEnum):
    GATEWAY = "gateway"
    RELAY = "relay"
    EGRESS = "egress"
    MIXED = "mixed"


class NodeAuthTypeValue(StrEnum):
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"


class NodeStatusValue(StrEnum):
    UNKNOWN = "unknown"
    REACHABLE = "reachable"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    role: NodeRoleValue = NodeRoleValue.MIXED
    management_address: str = Field(min_length=1, max_length=255)
    ssh_host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(min_length=1, max_length=64)
    auth_type: NodeAuthTypeValue


class NodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    role: NodeRoleValue | None = None
    management_address: str | None = Field(default=None, min_length=1, max_length=255)
    ssh_host: str | None = Field(default=None, min_length=1, max_length=255)
    ssh_port: int | None = Field(default=None, ge=1, le=65535)
    ssh_user: str | None = Field(default=None, min_length=1, max_length=64)
    auth_type: NodeAuthTypeValue | None = None
    status: NodeStatusValue | None = None


class NodeRead(ONXBaseModel):
    id: str
    name: str
    role: NodeRoleValue
    management_address: str
    ssh_host: str
    ssh_port: int
    ssh_user: str
    auth_type: NodeAuthTypeValue
    status: NodeStatusValue
    os_family: str | None
    os_version: str | None
    kernel_version: str | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
