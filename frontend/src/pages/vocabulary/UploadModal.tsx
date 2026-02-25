import { useState, useRef } from 'react'
import Papa from 'papaparse'
import api from '../../lib/api'

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onUploadSuccess: () => void
  onUploadWarning: (message: string) => void
}

const UploadModal = ({ isOpen, onClose, onUploadSuccess, onUploadWarning }: UploadModalProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [sourceName, setSourceName] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  if (!isOpen) return null

  const handleClose = () => {
    setSelectedFile(null)
    setSourceName('')
    setUploadError(null)
    onClose()
  }

  const handleFileSelect = (file: File) => {
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
      alert('Only .csv files are accepted')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('Maximum file size is 10 MB')
      return
    }
    setSelectedFile(file)
    setUploadError(null)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile || !sourceName.trim()) {
      setUploadError('Please select a file and enter a source name')
      return
    }

    setUploading(true)
    setUploadError(null)
    try {
      const parseResult = await new Promise<Papa.ParseResult<Record<string, string>>>((resolve, reject) => {
        Papa.parse<Record<string, string>>(selectedFile, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => resolve(results),
          error: (error: Error) => reject(error),
        })
      })

      const headers = parseResult.meta.fields?.map(f => f.trim().toLowerCase()) || []
      const requiredColumns = ['word', 'pinyin', 'meaning']
      const missingColumns = requiredColumns.filter(col => !headers.includes(col))

      if (missingColumns.length > 0) {
        setUploadError(`CSV is missing required columns: ${missingColumns.join(', ')}. Your CSV must have columns named "word", "pinyin", and "meaning".`)
        return
      }

      if (parseResult.data.length === 0) {
        setUploadError('CSV file contains no data rows. Please check that your file has data below the header row.')
        return
      }

      const fieldMap: Record<string, string> = {}
      parseResult.meta.fields?.forEach(f => {
        fieldMap[f.trim().toLowerCase()] = f
      })

      const allRows = parseResult.data.map(row => ({
        word: row[fieldMap['word']],
        pinyin: row[fieldMap['pinyin']],
        meaning: row[fieldMap['meaning']],
        source_name: sourceName.trim(),
      }))

      const validRows = allRows.filter(w => w.word && w.pinyin && w.meaning)
      const skippedCount = allRows.length - validRows.length

      if (validRows.length === 0) {
        setUploadError('All rows have empty required fields (word, pinyin, or meaning). Please check your CSV.')
        return
      }

      await api.post('/api/words', validRows)

      if (skippedCount > 0) {
        onUploadWarning(`${skippedCount} row(s) were excluded due to missing data (word, pinyin, or meaning).`)
      }
      setSelectedFile(null)
      setSourceName('')
      setUploadError(null)
      onUploadSuccess()
    } catch (error: unknown) {
      console.error('Error uploading file:', error)
      const axiosError = error as { response?: { status?: number; data?: { error?: string; message?: string } } }
      if (axiosError.response?.status === 401) {
        setUploadError('Import failed: You must be logged in to import vocabulary.')
      } else {
        const message = axiosError.response?.data?.error || axiosError.response?.data?.message || 'Failed to upload file. Please try again.'
        setUploadError(`Import failed: ${message}`)
      }
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
        {/* Modal Header */}
        <div className="p-6 pb-4">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-xl font-semibold text-gray-900">Upload file</h2>
            <button
              onClick={handleClose}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="text-sm text-gray-500">Only .csv files are accepted. Required columns: word, pinyin, meaning</p>
        </div>

        {/* Upload Area */}
        <div className="px-6">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragging
                ? 'border-purple-500 bg-purple-50'
                : selectedFile
                ? 'border-purple-500 bg-purple-50'
                : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileInputChange}
              className="hidden"
            />
            {selectedFile ? (
              <>
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-purple-100 flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <p className="text-purple-600 font-medium">{selectedFile.name}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </>
            ) : (
              <>
                <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-purple-100 flex items-center justify-center">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                </div>
                <p>
                  <span className="text-purple-600 font-medium">Click to Upload</span>
                  <span className="text-gray-600"> or drag and drop</span>
                </p>
                <p className="text-sm text-gray-400 mt-1">Maximum file size 10 MB</p>
              </>
            )}
          </div>
        </div>

        {/* Source Name Input */}
        <div className="px-6 py-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Name your source file
          </label>
          <p className="text-xs text-gray-500 mb-2">
            Words from this file will be tagged with the following name for easy identification
          </p>
          <input
            type="text"
            placeholder="e.g., Kitchen Vocabulary"
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>

        {/* Error Message */}
        {uploadError && (
          <div className="px-6 pb-2">
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{uploadError}</p>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="px-6 pb-6 flex items-center justify-end gap-3">
          <button
            onClick={handleClose}
            className="px-5 py-2.5 text-gray-700 font-medium border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || !sourceName.trim() || uploading}
            className="flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white font-medium rounded-full transition-colors"
          >
            {uploading && (
              <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {uploading ? 'Processing...' : 'Attach File'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default UploadModal
