'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { adminAPI, authAPI } from '@/lib/api'

type Tab = 'questions' | 'upload' | 'users' | 'stats' | 'anticheat'

export default function AdminPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const tabParam = searchParams.get('tab') as Tab
  const [activeTab, setActiveTab] = useState<Tab>(tabParam || 'questions')
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Question Management State
  const [domains, setDomains] = useState<any[]>([])
  const [selectedDomain, setSelectedDomain] = useState('')
  const [questions, setQuestions] = useState<any[]>([])
  const [editingQuestion, setEditingQuestion] = useState<any>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newQuestion, setNewQuestion] = useState({ question: '', answer: '' })

  // Upload State
  const [files, setFiles] = useState<File[]>([])
  const [uploadDomain, setUploadDomain] = useState('general')

  // Users State
  const [users, setUsers] = useState<any[]>([])

  // Stats State
  const [stats, setStats] = useState<any>(null)

  // Anti-cheat state
  const [antiCheatEnabled, setAntiCheatEnabled] = useState(false)
  const [violations, setViolations] = useState<any[]>([])
  const [expandedUserId, setExpandedUserId] = useState<number | null>(null)

  useEffect(() => {
    loadInitialData()
  }, [])

  useEffect(() => {
    // Update tab from URL parameter
    if (tabParam && ['questions', 'upload', 'users', 'stats'].includes(tabParam)) {
      setActiveTab(tabParam)
    }
  }, [tabParam])

  useEffect(() => {
    if (selectedDomain && activeTab === 'questions') {
      loadQuestions()
    }
  }, [selectedDomain])

  const loadInitialData = async () => {
    try {
      const userRes = await authAPI.getCurrentUser()
      setUser(userRes.data)
      
      if (!userRes.data.is_admin) {
        router.push('/dashboard')
        return
      }

      // Load domains
      const domainsRes = await adminAPI.getDomains()
      setDomains(domainsRes.data.domains)
      if (domainsRes.data.domains.length > 0) {
        setSelectedDomain(domainsRes.data.domains[0].name)
      }

      // Load stats
      loadStats()
      // Load anti-cheat settings
      adminAPI.getAntiCheatSettings().then(res => setAntiCheatEnabled(res.data.anticheat_enabled)).catch(() => {})
    } catch (error) {
      router.push('/auth/login')
    }
  }

  const loadQuestions = async () => {
    if (!selectedDomain) return
    
    setLoading(true)
    try {
      const res = await adminAPI.getQuestions(selectedDomain)
      setQuestions(res.data.questions)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load questions')
    } finally {
      setLoading(false)
    }
  }

  const loadUsers = async () => {
    setLoading(true)
    try {
      const res = await adminAPI.getUsers()
      setUsers(res.data.users)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleUser = async (userId: number) => {
    try {
      const res = await adminAPI.toggleUserActive(userId)
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: res.data.is_active } : u))
      )
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update user status')
    }
  }

  const loadStats = async () => {
    try {
      const res = await adminAPI.getInterviewStats()
      setStats(res.data)
    } catch (err) {
      console.error('Failed to load stats')
    }
  }

  const handleToggleAntiCheat = async () => {
    try {
      const newVal = !antiCheatEnabled
      await adminAPI.updateAntiCheatSettings(newVal)
      setAntiCheatEnabled(newVal)
      setSuccess(`Anti-cheat ${newVal ? 'enabled' : 'disabled'}`)
      setTimeout(() => setSuccess(''), 3000)
    } catch {
      setError('Failed to update anti-cheat setting')
    }
  }

  const loadViolations = async () => {
    setLoading(true)
    try {
      const res = await adminAPI.getAntiCheatViolations()
      setViolations(res.data.violations)
    } catch {
      setError('Failed to load violations')
    } finally {
      setLoading(false)
    }
  }

  const handleAddQuestion = async () => {
    if (!newQuestion.question.trim()) {
      setError('Question is required')
      return
    }

    setLoading(true)
    setError('')
    try {
      await adminAPI.addQuestion(selectedDomain, newQuestion)
      setSuccess('Question added successfully!')
      setShowAddModal(false)
      setNewQuestion({ question: '', answer: '' })
      loadQuestions()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add question')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateQuestion = async () => {
    if (!editingQuestion) return

    setLoading(true)
    setError('')
    try {
      await adminAPI.updateQuestion(selectedDomain, editingQuestion.id, {
        question: editingQuestion.question,
        answer: editingQuestion.answer
      })
      setSuccess('Question updated successfully!')
      setEditingQuestion(null)
      loadQuestions()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update question')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteQuestion = async (questionId: string) => {
    if (!confirm('Are you sure you want to delete this question?')) return

    setLoading(true)
    setError('')
    try {
      await adminAPI.deleteQuestion(selectedDomain, questionId)
      setSuccess('Question deleted successfully!')
      loadQuestions()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete question')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (files.length === 0) {
      setError('Please select at least one file')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await adminAPI.uploadDocuments(files, uploadDomain)
      setSuccess(`Successfully uploaded ${files.length} file(s)!`)
      setFiles([])
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload documents')
    } finally {
      setLoading(false)
    }
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4">
      <div className="container mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-dark rounded-2xl p-8 shadow-2xl"
        >
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
              Admin Panel
            </h1>
            <button
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
            >
              Back to Dashboard
            </button>
          </div>

          {/* Alerts */}
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
              {success}
            </div>
          )}

          {/* Tabs */}
          <div className="flex space-x-2 mb-6 border-b border-gray-300 dark:border-gray-600">
            {[
              { id: 'questions', label: 'Question Management' },
              { id: 'upload', label: 'Upload Documents' },
              { id: 'users', label: 'Users' },
              { id: 'stats', label: 'Statistics' },
              { id: 'anticheat', label: '🛡️ Anti-Cheat' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id as Tab)
                  setError('')
                  setSuccess('')
                  if (tab.id === 'users') loadUsers()
                  if (tab.id === 'stats') loadStats()
                  if (tab.id === 'anticheat') loadViolations()
                }}
                className={`px-6 py-3 font-medium transition ${
                  activeTab === tab.id
                    ? 'border-b-2 border-purple-600 text-purple-600 dark:text-purple-400'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Question Management Tab */}
          {activeTab === 'questions' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-4">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Domain:
                  </label>
                  <select
                    value={selectedDomain}
                    onChange={(e) => setSelectedDomain(e.target.value)}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-800 dark:text-white"
                  >
                    {domains.map((domain) => (
                      <option key={domain.name} value={domain.name}>
                        {domain.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
                >
                  + Add Question
                </button>
              </div>

              {/* Questions List */}
              <div className="space-y-4 max-h-[600px] overflow-y-auto">
                {loading ? (
                  <div className="text-center py-8">Loading questions...</div>
                ) : questions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No questions found in this domain
                  </div>
                ) : (
                  questions.map((q) => (
                    <div
                      key={q.id}
                      className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                    >
                      {editingQuestion?.id === q.id ? (
                        <div className="space-y-3">
                          <input
                            type="text"
                            value={editingQuestion.question}
                            onChange={(e) =>
                              setEditingQuestion({
                                ...editingQuestion,
                                question: e.target.value
                              })
                            }
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:text-white"
                          />
                          <textarea
                            value={editingQuestion.answer}
                            onChange={(e) =>
                              setEditingQuestion({
                                ...editingQuestion,
                                answer: e.target.value
                              })
                            }
                            rows={4}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:text-white"
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={handleUpdateQuestion}
                              disabled={loading}
                              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingQuestion(null)}
                              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex-1">
                              <p className="font-semibold text-gray-800 dark:text-white">
                                {q.number}. {q.question}
                              </p>
                              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                                {q.answer}
                              </p>
                            </div>
                            <div className="flex space-x-2 ml-4">
                              <button
                                onClick={() => setEditingQuestion(q)}
                                className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteQuestion(q.id)}
                                className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">
                            File: {q.file}
                          </p>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Upload Documents Tab */}
          {activeTab === 'upload' && (
            <form onSubmit={handleFileUpload} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Upload Interview Documents
                </label>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => {
                    if (e.target.files) {
                      setFiles(Array.from(e.target.files))
                      setError('')
                    }
                  }}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-800 dark:text-white"
                />
                {files.length > 0 && (
                  <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                    <p>Selected {files.length} file(s):</p>
                    <ul className="list-disc list-inside">
                      {files.map((file, idx) => (
                        <li key={idx}>{file.name}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Domain
                </label>
                <select
                  value={uploadDomain}
                  onChange={(e) => setUploadDomain(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-800 dark:text-white"
                >
                  {domains.map((domain) => (
                    <option key={domain.name} value={domain.name}>
                      {domain.display_name}
                    </option>
                  ))}
                </select>
              </div>

              <button
                type="submit"
                disabled={loading || files.length === 0}
                className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition disabled:opacity-50"
              >
                {loading ? 'Uploading...' : 'Upload & Index Documents'}
              </button>
            </form>
          )}

          {/* Users Tab */}
          {activeTab === 'users' && (
            <div className="space-y-4">
              <div className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                Total Users: {users.length}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-100 dark:bg-gray-800">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">
                        Username
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">
                        Email
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">
                        Full Name
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">
                        Status
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">
                        Created
                      </th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-700 dark:text-gray-300">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-750 transition">
                        <td className="px-4 py-3 text-sm">
                          <button
                            onClick={() => router.push(`/admin/users/${u.id}`)}
                            className="text-purple-600 dark:text-purple-400 hover:underline font-medium"
                          >
                            {u.username}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-800 dark:text-gray-200">
                          {u.email}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-800 dark:text-gray-200">
                          {u.full_name || '—'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            u.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <button
                            onClick={() => handleToggleUser(u.id)}
                            className={`px-3 py-1 rounded text-xs font-medium transition ${
                              u.is_active
                                ? 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300 dark:hover:bg-red-800'
                                : 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300 dark:hover:bg-green-800'
                            }`}
                          >
                            {u.is_active ? 'Disable' : 'Enable'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Statistics Tab */}
          {activeTab === 'stats' && stats && (
            <div className="space-y-6">
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-blue-100 dark:bg-blue-900 p-6 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Total Interviews</p>
                  <p className="text-3xl font-bold text-gray-800 dark:text-white">
                    {stats.total_interviews}
                  </p>
                </div>
                <div className="bg-green-100 dark:bg-green-900 p-6 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Completed</p>
                  <p className="text-3xl font-bold text-gray-800 dark:text-white">
                    {stats.completed_interviews}
                  </p>
                </div>
                <div className="bg-purple-100 dark:bg-purple-900 p-6 rounded-lg">
                  <p className="text-sm text-gray-600 dark:text-gray-400">Active</p>
                  <p className="text-3xl font-bold text-gray-800 dark:text-white">
                    {stats.active_interviews}
                  </p>
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-white mb-4">
                  Domain Distribution
                </h3>
                <div className="space-y-2">
                  {Object.entries(stats.domain_distribution || {}).map(([domain, count]) => (
                    <div key={domain} className="flex justify-between items-center">
                      <span className="text-gray-700 dark:text-gray-300 capitalize">
                        {domain.replace('-', ' ')}
                      </span>
                      <span className="font-semibold text-gray-800 dark:text-white">
                        {count as number}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Anti-Cheat Tab */}
          {activeTab === 'anticheat' && (() => {
            // Group violations by user
            const byUser: Record<string, { username: string; user_id: number; violations: any[] }> = {}
            violations.forEach(v => {
              if (!byUser[v.user_id]) byUser[v.user_id] = { username: v.username, user_id: v.user_id, violations: [] }
              byUser[v.user_id].violations.push(v)
            })
            const userList = Object.values(byUser).sort((a, b) => b.violations.length - a.violations.length)

            const VIOLATION_STYLE: Record<string, string> = {
              tab_switch: 'bg-orange-100 text-orange-800',
              window_blur: 'bg-yellow-100 text-yellow-800',
              copy: 'bg-blue-100 text-blue-800',
              paste: 'bg-purple-100 text-purple-800',
              right_click: 'bg-gray-100 text-gray-800',
              multiple_displays: 'bg-red-100 text-red-800',
              devtools_open: 'bg-pink-100 text-pink-800',
            }
            const VIOLATION_ICON: Record<string, string> = {
              tab_switch: '🔀', window_blur: '👁️', copy: '📋', paste: '📌',
              right_click: '🖱️', multiple_displays: '🖥️', devtools_open: '🔧',
            }

            return (
              <div className="space-y-6">

                {/* Toggle row */}
                <div className="flex items-center justify-between p-5 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                  <div>
                    <p className="font-bold text-gray-800 dark:text-white text-lg flex items-center gap-2">
                      🛡️ Anti-Cheat Monitoring
                      <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${antiCheatEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {antiCheatEnabled ? 'ENABLED' : 'DISABLED'}
                      </span>
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                      Detects tab switches, copy-paste, multiple displays, DevTools, and right-clicks during interviews.
                    </p>
                  </div>
                  <button
                    onClick={handleToggleAntiCheat}
                    className={`relative w-16 h-8 rounded-full transition-colors duration-300 focus:outline-none ${antiCheatEnabled ? 'bg-green-500' : 'bg-gray-300'}`}
                  >
                    <span className={`absolute top-1 left-1 w-6 h-6 bg-white rounded-full shadow transition-transform duration-300 ${antiCheatEnabled ? 'translate-x-8' : 'translate-x-0'}`} />
                  </button>
                </div>

                {/* Summary cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Total Violations', value: violations.length, color: 'bg-red-50 text-red-700 border-red-200' },
                    { label: 'Users Flagged', value: userList.length, color: 'bg-orange-50 text-orange-700 border-orange-200' },
                    { label: 'Tab Switches', value: violations.filter(v => v.violation_type === 'tab_switch').length, color: 'bg-yellow-50 text-yellow-700 border-yellow-200' },
                    { label: 'Multi-Display', value: violations.filter(v => v.violation_type === 'multiple_displays').length, color: 'bg-purple-50 text-purple-700 border-purple-200' },
                  ].map(card => (
                    <div key={card.label} className={`p-4 rounded-xl border ${card.color}`}>
                      <p className="text-2xl font-bold">{card.value}</p>
                      <p className="text-xs font-medium mt-1">{card.label}</p>
                    </div>
                  ))}
                </div>

                {/* Users with violations */}
                <div className="flex justify-between items-center">
                  <h3 className="font-bold text-gray-800 dark:text-white">Flagged Users</h3>
                  <button onClick={loadViolations} className="text-sm text-blue-600 hover:underline">↻ Refresh</button>
                </div>

                {loading ? (
                  <p className="text-center py-6 text-gray-500">Loading...</p>
                ) : userList.length === 0 ? (
                  <p className="text-center py-8 text-gray-500">No violations recorded yet.</p>
                ) : (
                  <div className="space-y-3">
                    {userList.map(u => {
                      const typeCounts: Record<string, number> = {}
                      u.violations.forEach(v => { typeCounts[v.violation_type] = (typeCounts[v.violation_type] || 0) + 1 })
                      const isExpanded = (expandedUserId as any) === u.user_id

                      return (
                        <div key={u.user_id} className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
                          {/* User row — clickable */}
                          <button
                            type="button"
                            onClick={() => setExpandedUserId(isExpanded ? null : u.user_id)}
                            className="w-full flex items-center justify-between px-5 py-4 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 transition text-left"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-full bg-red-100 text-red-700 flex items-center justify-center font-bold text-sm">
                                {u.username[0].toUpperCase()}
                              </div>
                              <div>
                                <p className="font-semibold text-gray-800 dark:text-white">{u.username}</p>
                                <p className="text-xs text-gray-500">{u.violations.length} violation{u.violations.length !== 1 ? 's' : ''}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              {Object.entries(typeCounts).map(([type, count]) => (
                                <span key={type} className={`px-2 py-0.5 rounded-full text-xs font-bold ${VIOLATION_STYLE[type] || 'bg-gray-100 text-gray-700'}`}>
                                  {VIOLATION_ICON[type] || '⚠️'} {count}
                                </span>
                              ))}
                              <span className="text-gray-400 ml-2">{isExpanded ? '▲' : '▼'}</span>
                            </div>
                          </button>

                          {/* Expanded violation list */}
                          {isExpanded && (
                            <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="bg-gray-100 dark:bg-gray-800">
                                    <th className="px-4 py-2 text-left text-xs text-gray-600 dark:text-gray-400">Interview</th>
                                    <th className="px-4 py-2 text-left text-xs text-gray-600 dark:text-gray-400">Violation</th>
                                    <th className="px-4 py-2 text-left text-xs text-gray-600 dark:text-gray-400">Details</th>
                                    <th className="px-4 py-2 text-left text-xs text-gray-600 dark:text-gray-400">Time</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                                  {u.violations.map(v => (
                                    <tr key={v.id} className="hover:bg-white dark:hover:bg-gray-800">
                                      <td className="px-4 py-2 text-gray-600 dark:text-gray-400 text-xs">
                                        <span className="font-medium text-gray-800 dark:text-gray-200">{v.interview_title || `#${v.interview_id}`}</span>
                                        {v.interview_domain && <span className="ml-1 text-gray-400">({v.interview_domain})</span>}
                                      </td>
                                      <td className="px-4 py-2">
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${VIOLATION_STYLE[v.violation_type] || 'bg-gray-100 text-gray-700'}`}>
                                          {VIOLATION_ICON[v.violation_type] || '⚠️'} {v.violation_type.replace(/_/g, ' ')}
                                        </span>
                                      </td>
                                      <td className="px-4 py-2 text-gray-500 text-xs max-w-xs">{v.details}</td>
                                      <td className="px-4 py-2 text-gray-400 text-xs whitespace-nowrap">
                                        {v.occurred_at ? new Date(v.occurred_at.endsWith('Z') ? v.occurred_at : v.occurred_at + 'Z').toLocaleString() : 'N/A'}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })()}

      {/* Add Question Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4"
          >
            <h2 className="text-2xl font-bold text-gray-800 dark:text-white mb-4">
              Add New Question
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Question
                </label>
                <input
                  type="text"
                  value={newQuestion.question}
                  onChange={(e) =>
                    setNewQuestion({ ...newQuestion, question: e.target.value })
                  }
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:text-white"
                  placeholder="Enter the question..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
                  Answer
                </label>
                <textarea
                  value={newQuestion.answer}
                  onChange={(e) =>
                    setNewQuestion({ ...newQuestion, answer: e.target.value })
                  }
                  rows={6}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:text-white"
                  placeholder="Enter the answer..."
                />
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={handleAddQuestion}
                  disabled={loading}
                  className="flex-1 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
                >
                  {loading ? 'Adding...' : 'Add Question'}
                </button>
                <button
                  onClick={() => {
                    setShowAddModal(false)
                    setNewQuestion({ question: '', answer: '' })
                    setError('')
                  }}
                  className="flex-1 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                >
                  Cancel
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
