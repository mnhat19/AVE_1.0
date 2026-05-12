import type { DragEvent } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { UploadFileResult } from '../../services/api'
import { getErrorMessage, getSessionFiles, uploadSessionFiles } from '../../services/api'
import styles from '../panels.module.css'

type UploadPanelProps = {
  sessionId: string
  onQueueChange?: (count: number) => void
  onBack?: () => void
  onNext?: () => void
}

export function UploadPanel({
  sessionId,
  onQueueChange,
  onBack,
  onNext,
}: UploadPanelProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [bundleId, setBundleId] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [queuedFiles, setQueuedFiles] = useState<UploadFileResult[]>([])
  const [queueError, setQueueError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [lastValidation, setLastValidation] = useState<unknown | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const canUpload = sessionId && selectedFiles.length > 0 && !isUploading

  const dropZoneLabel = useMemo(() => {
    if (!sessionId) {
      return 'Create or load a session before uploading.'
    }

    return 'Drop files here or browse to select documents.'
  }, [sessionId])

  const handleFiles = (files: File[]) => {
    if (!files.length) {
      return
    }
    setUploadError(null)
    setSelectedFiles(files)
    if (!sessionId) {
      return
    }
    if (isUploading) {
      setUploadError('Upload in progress. Please wait before adding more files.')
      return
    }
    void uploadFiles(files)
  }

  const handleBrowse = () => {
    fileInputRef.current?.click()
  }

  const refreshQueue = useCallback(async (resetSelection = false) => {
    if (!sessionId) {
      setQueuedFiles([])
      setQueueError(null)
      setLastValidation(null)
      if (resetSelection) {
        setSelectedFiles([])
      }
      onQueueChange?.(0)
      return
    }
    if (resetSelection) {
      setSelectedFiles([])
    }
    setQueueError(null)
    try {
      const response = await getSessionFiles(sessionId)
      setQueuedFiles(response.files)
      onQueueChange?.(response.files.length)
    } catch (error) {
      setQueueError(getErrorMessage(error, 'Unable to load session files.'))
    }
  }, [onQueueChange, sessionId])

  useEffect(() => {
    let isActive = true

    const loadQueue = async () => {
      if (!isActive) {
        return
      }
      await refreshQueue(true)
    }

    void loadQueue()

    return () => {
      isActive = false
    }
  }, [refreshQueue])

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    handleFiles(Array.from(event.dataTransfer.files))
  }

  const uploadFiles = async (filesToUpload: File[]) => {
    if (!sessionId) {
      setUploadError('Session ID is required before uploading.')
      return
    }
    if (!filesToUpload.length) {
      setUploadError('Select at least one document to upload.')
      return
    }

    setIsUploading(true)
    setUploadError(null)

    try {
      const response = await uploadSessionFiles(
        sessionId,
        filesToUpload,
        bundleId.trim() || undefined
      )
      setLastValidation(response.validation ?? null)
      setSelectedFiles([])
      await refreshQueue()
    } catch (error) {
      setUploadError(getErrorMessage(error, 'Upload failed.'))
    } finally {
      setIsUploading(false)
    }
  }

  const handleUpload = async () => {
    await uploadFiles(selectedFiles)
  }

  const pendingRows = selectedFiles.map((file, index) => ({
    file_id: `pending-${index}`,
    filename: file.name,
    format: file.name.split('.').pop()?.toUpperCase() ?? 'FILE',
    stage: 'PENDING',
    status: isUploading ? 'UPLOADING' : 'QUEUED',
  }))
  const queueRows = [...pendingRows, ...queuedFiles]
  const hasUploadedFiles = queuedFiles.length > 0
  const hasPendingFiles = pendingRows.length > 0
  const showPendingHint = hasPendingFiles && !hasUploadedFiles && !isUploading

  return (
    <section className={styles.section}>
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Source Upload</h2>
        <p className={styles.panelMeta}>
          Drag and drop documents or browse from disk. Validation runs per bundle.
        </p>
        <div
          className={`${styles.dropZone} ${isDragging ? styles.dropZoneActive : ''}`}
          role="region"
          aria-label="File upload drop zone"
          onDragOver={(event) => {
            event.preventDefault()
            setIsDragging(true)
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <p className={styles.dropZoneText}>{dropZoneLabel}</p>
          <div className={styles.buttonRow}>
            <button
              className={styles.buttonPrimary}
              type="button"
              onClick={handleBrowse}
              disabled={!sessionId}
              aria-label="Browse files from your computer"
            >
              Browse Files
            </button>
            <button
              className={styles.buttonGhost}
              type="button"
              onClick={handleUpload}
              disabled={!canUpload}
              aria-label="Upload selected files bundle"
              aria-busy={isUploading}
            >
              {isUploading ? 'Uploading...' : 'Upload Bundle'}
            </button>
          </div>
          <input
            ref={fileInputRef}
            className={styles.hiddenInput}
            type="file"
            multiple
            onChange={(event) =>
              handleFiles(Array.from(event.target.files ?? []))
            }
          />
        </div>
        <div className={styles.inputRow}>
          <label className={styles.label} htmlFor="bundle-id">
            Bundle ID (optional)
          </label>
          <input
            id="bundle-id"
            className={styles.input}
            value={bundleId}
            onChange={(event) => setBundleId(event.target.value)}
            placeholder="Use to append to an existing bundle"
          />
        </div>
        {uploadError ? <p className={styles.errorText}>{uploadError}</p> : null}
      </div>
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Upload Queue</h2>
        {queueError ? <p className={styles.errorText}>{queueError}</p> : null}
        {showPendingHint ? (
          <p className={styles.panelMeta}>
            Files are selected but not uploaded yet. Click Upload Bundle to save them.
          </p>
        ) : null}
        {queueRows.length ? (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Format</th>
                <th>Stage</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {queueRows.map((file) => (
                <tr key={`${file.file_id}-${file.filename}`}>
                  <td>{file.filename}</td>
                  <td>{file.format}</td>
                  <td>{file.stage}</td>
                  <td>
                    <span className={styles.statusBadge}>{file.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className={styles.panelMeta}>No uploads yet.</p>
        )}
      </div>
      {lastValidation ? (
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Validation Report</h2>
          <pre className={styles.codeBlock}>
            {JSON.stringify(lastValidation, null, 2)}
          </pre>
        </div>
      ) : null}
      <div className={styles.panel}>
        <h2 className={styles.panelTitle}>Workflow Navigation</h2>
        <div className={styles.buttonRow}>
          <button
            className={styles.buttonGhost}
            type="button"
            onClick={onBack}
            disabled={!onBack}
            aria-label="Back to session step"
          >
            Back to Session
          </button>
          <button
            className={styles.buttonPrimary}
            type="button"
            onClick={onNext}
            disabled={!hasUploadedFiles || !onNext}
            aria-label="Continue to run step"
          >
            Continue to Run
          </button>
        </div>
      </div>
    </section>
  )
}
