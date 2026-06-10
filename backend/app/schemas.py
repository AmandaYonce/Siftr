from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ScanRequest(CamelModel):
    folder: str
    threshold: int = Field(default=9, ge=0, le=64)
    recursive: bool = True


class ScanResponse(CamelModel):
    photo_count: int
    cluster_count: int
    duration_ms: int


class PhotoOut(CamelModel):
    id: int
    filename: str
    thumbnail_url: str
    sharpness: float
    width: int
    height: int
    taken_at: str | None
    bytes: int


class ClusterOut(CamelModel):
    id: str
    suggested_keeper_id: int
    photos: list[PhotoOut]


class Summary(CamelModel):
    photos: int
    clusters: int
    duplicates: int
    reclaimable_bytes: int


class ClustersResponse(CamelModel):
    summary: Summary
    clusters: list[ClusterOut]
