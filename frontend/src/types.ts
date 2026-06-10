export interface ScanResponse {
  photoCount: number
  clusterCount: number
  durationMs: number
}

export interface Photo {
  id: number
  filename: string
  thumbnailUrl: string
  sharpness: number
  width: number
  height: number
  takenAt: string | null
  bytes: number
}

export interface Cluster {
  id: string
  suggestedKeeperId: number
  photos: Photo[]
}

export interface Summary {
  photos: number
  clusters: number
  duplicates: number
  reclaimableBytes: number
}

export interface ClustersResponse {
  summary: Summary
  clusters: Cluster[]
}

export interface ApplyResponse {
  moved: number
  reclaimedBytes: number
}

export interface UndoResponse {
  restored: number
}
