'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { interviewAPI } from '@/lib/api'

export default function ResumeUploadPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState<any>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      const ext = selectedFile.name.split('.').pop()?.toLowerCase()
      
      // Validate file type
      if (ext !== 'pdf' && ext !== 'docx' && ext !== 'doc') {
        setError('Only PDF, DOC, and DOCX files are supported')
        setFile(null)
        return
      }
      
      // Validate file size (1KB - 10MB)
      const minSize = 1 * 1024 // 1KB
      const maxSize = 10 * 1024 * 1024 // 10MB
      
      if (selectedFile.size < minSize) {
        setError(`File too small. Minimum size is 1KB.`)
        setFile(null)
        return
      }
      
      if (selectedFile.size > maxSize) {
        setError(`File too large. Maximum size is 10MB.`)
        setFile(null)
        return
      }
      
      // Validate filename (basic sanitization check)
      const invalidChars = /[<>:"|?*]/
      if (invalidChars.test(selectedFile.name)) {
        setError('Filename contains invalid characters')
        setFile(null)
        return
      }
      
      setFile(selectedFile)
      setError('')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a file')
      return
    }

    setError('')
    setLoading(true)

    try {
      const response = await interviewAPI.uploadResume(file)
      setSuccess(response.data)
    } catch (err: any) {
      // Handle detailed validation errors
      const errorDetail = err.response?.data?.detail
      
      if (typeof errorDetail === 'object' && errorDetail.error) {
        // Structured error response
        let errorMessage = errorDetail.error
        if (errorDetail.details && errorDetail.details.length > 0) {
          errorMessage += '\n\nDetails:\n' + errorDetail.details.join('\n')
        }
        setError(errorMessage)
      } else if (typeof errorDetail === 'string') {
        setError(errorDetail)
      } else {
        setError('Failed to upload resume. Please ensure your file is a valid resume.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4">
      <div className="container mx-auto max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-dark rounded-2xl p-8 shadow-2xl"
        >
          <h1 className="text-3xl font-bold mb-2 text-gray-800 dark:text-white">
            Upload Resume
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
            Upload your resume or{' '}
            <button
              onClick={() => router.push('/resume/manual')}
              className="text-blue-600 hover:text-blue-700 font-semibold underline"
            >
              build your profile manually
            </button>
          </p>

          {error && (
            <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
              <p className="font-semibold mb-2">❌ Validation Error</p>
              <div className="text-sm whitespace-pre-line">{error}</div>
            </div>
          )}

          {success && (
            <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
              <p className="font-semibold mb-3">✅ Resume uploaded successfully!</p>
              <div className="space-y-2 text-sm">
                <p><strong>Filename:</strong> {success.filename}</p>
                <p><strong>Experience:</strong> {success.experience_years} years</p>
                <p><strong>Skills:</strong> {success.extracted_skills.join(', ')}</p>
                {success.validation && (
                  <>
                    <p><strong>Quality Score:</strong> {success.validation.quality_score.toFixed(1)}/100</p>
                    <p><strong>Word Count:</strong> {success.validation.word_count}</p>
                    <p><strong>Detected Sections:</strong> {success.validation.detected_sections.join(', ')}</p>
                  </>
                )}
              </div>
              <button
                onClick={() => router.push('/dashboard')}
                className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                Back to Dashboard
              </button>
            </div>
          )}

          {!success && (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Select Resume (PDF, DOC, or DOCX)
                </label>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={handleFileChange}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                  required
                />
                {file && (
                  <p className="mt-2 text-sm text-green-600 dark:text-green-400">
                    ✓ Selected: {file.name} ({(file.size / 1024).toFixed(2)} KB)
                  </p>
                )}
              </div>

              <div className="bg-blue-50 dark:bg-blue-900 p-4 rounded-lg space-y-2">
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                  Resume Requirements:
                </p>
                <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 list-disc list-inside">
                  <li>File size: up to 10MB</li>
                  <li>Format: PDF, DOC, or DOCX only</li>
                  <li>Minimum 100 meaningful words</li>
                  <li>Must contain at least 2 sections (Education, Experience, Skills, etc.)</li>
                  <li>No placeholder text or spam content</li>
                </ul>
              </div>

              <div className="flex gap-4">
                <button
                  type="button"
                  onClick={() => router.back()}
                  className="flex-1 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !file}
                  className="flex-1 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition disabled:opacity-50"
                >
                  {loading ? 'Uploading...' : 'Upload Resume'}
                </button>
              </div>
            </form>
          )}
        </motion.div>
      </div>
    </div>
  )
}
