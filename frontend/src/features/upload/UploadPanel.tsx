import type { DragEvent } from 'react'
import { useMemo, useRef, useState } from 'react'

import type { UploadFileResult } from '../../services/api'
import { getErrorMessage, uploadSessionFiles } from '../../services/api'
import styles from '../panels.module.css'

type UploadPanelProps = {
  sessionId: string
}

export function UploadPanel({ sessionId }: UploadPanelProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [bundleId, setBundleId] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadResult, setUploadResult] = useState<{
    files: UploadFileResult[]
    validation?: unknown
  } | null>(null)
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
  }

  const handleBrowse = () => {
    fileInputRef.current?.click()
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    handleFiles(Array.from(event.dataTransfer.files))
  }

  const handleUpload = async () => {
    if (!sessionId) {
      setUploadError('Session ID is required before uploading.')
      return
    }
    if (!selectedFiles.length) {
      setUploadError('Select at least one document to upload.')
      return
    }

    setIsUploading(true)
    setUploadError(null)

    try {
      const response = await uploadSessionFiles(
        sessionId,
        selectedFiles,
        bundleId.trim() || undefined
      )
      setUploadResult({ files: response.files, validation: response.validation })
      setSelectedFiles([])
    } catch (error) {
      setUploadError(getErrorMessage(error, 'Upload failed.'))
    } finally {
      setIsUploading(false)
    }
  }

  const queueRows = uploadResult?.files.length
    ? uploadResult.files
    : selectedFiles.map((file) => ({
        file_id: 'pending',
        filename: file.name,
        format: file.name.split('.').pop()?.toUpperCase() ?? 'FILE',
        stage: 'PENDING',
        status: 'QUEUED',
      }))

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
      {uploadResult?.validation ? (
        <div className={styles.panel}>
          <h2 className={styles.panelTitle}>Validation Report</h2>
          <pre className={styles.codeBlock}>
            {JSON.stringify(uploadResult.validation, null, 2)}
          </pre>
        </div>
      ) : null}
    </section>
  )
}
