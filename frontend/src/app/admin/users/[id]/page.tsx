'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { adminAPI } from '@/lib/api'

export default function AdminUserHistoryPage() {
  const router = useRouter()
  const params = useParams()
  const userId = Number(params.id)

  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [expandedInterview, setExpandedInterview] = useState<number | null>(null)

  useEffect(() => {
    loadUserHistory()
  }, [userId])

  const loadUserHistory = async () => {
    try {
      const res = await adminAPI.getUserInterviews(userId)
      setData(res.data)
    } catch (err) {
      console.error('Failed to load user history')
    } finally {
      setLoading(false)
    }
  }

  const getDifficultyColor = (d: string) => {
    if (d === 'easy') return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    if (d === 'hard') return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600 dark:text-green-400'
    if (score >= 50) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getStatusBadge = (status: string) => {
    if (status === 'completed')
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-gray-600 dark:text-gray-300">Loading user history...</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-red-500">User not found</div>
      </div>
    )
  }

  const { user, interviews, total_interviews } = data

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4">
      <div className="container mx-auto max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Back button */}
          <button
            onClick={() => router.push('/admin?tab=users')}
            className="flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white transition"
          >
            <span>←</span>
            <span>Back to Users</span>
          </button>

          {/* User Info Card */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-14 h-14 rounded-full bg-purple-600 flex items-center justify-center text-white text-2xl font-bold">
                  {user.username[0].toUpperCase()}
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-800 dark:text-white">
                    {user.full_name || user.username}
                  </h1>
                  <p className="text-gray-500 dark:text-gray-400">{user.email}</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500">
                    Joined {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  user.is_active
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                }`}>
                  {user.is_active ? 'Active' : 'Disabled'}
                </span>
              </div>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <div className="text-center">
                <p className="text-3xl font-bold text-gray-800 dark:text-white">{total_interviews}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Total Interviews</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-600 dark:text-green-400">
                  {interviews.filter((i: any) => i.status === 'completed').length}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Completed</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">
                  {total_interviews > 0
                    ? (
                        interviews
                          .filter((i: any) => i.status === 'completed' && i.overall_score > 0)
                          .reduce((sum: number, i: any) => sum + i.overall_score, 0) /
                        (interviews.filter((i: any) => i.status === 'completed' && i.overall_score > 0).length || 1)
                      ).toFixed(1)
                    : '0'}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Avg Score</p>
              </div>
            </div>
          </div>

          {/* Interview History */}
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white">Interview History</h2>

          {interviews.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-12 text-center shadow-lg">
              <p className="text-gray-500 dark:text-gray-400 text-lg">No interviews taken yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {interviews.map((interview: any) => (
                <div
                  key={interview.id}
                  className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
                >
                  {/* Interview header — clickable to expand */}
                  <button
                    className="w-full text-left p-5 hover:bg-gray-50 dark:hover:bg-gray-750 transition"
                    onClick={() =>
                      setExpandedInterview(expandedInterview === interview.id ? null : interview.id)
                    }
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div>
                          <p className="font-semibold text-gray-800 dark:text-white">{interview.title}</p>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className="text-sm text-gray-500 dark:text-gray-400 capitalize">
                              {interview.domain.replace('-', ' ')}
                            </span>
                            <span className="text-gray-300 dark:text-gray-600">•</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getDifficultyColor(interview.difficulty)}`}>
                              {interview.difficulty}
                            </span>
                            <span className="text-gray-300 dark:text-gray-600">•</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getStatusBadge(interview.status)}`}>
                              {interview.status}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-6 text-right">
                        <div>
                          <p className={`text-2xl font-bold ${getScoreColor(interview.overall_score)}`}>
                            {interview.overall_score.toFixed(1)}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Score</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {interview.answered_questions}/{interview.total_questions} Qs
                          </p>
                          <p className="text-xs text-gray-400 dark:text-gray-500">
                            {interview.created_at ? new Date(interview.created_at).toLocaleDateString() : 'N/A'}
                          </p>
                        </div>
                        <span className="text-gray-400 dark:text-gray-500 text-lg">
                          {expandedInterview === interview.id ? '▲' : '▼'}
                        </span>
                      </div>
                    </div>
                  </button>

                  {/* Expanded questions */}
                  {expandedInterview === interview.id && (
                    <div className="border-t border-gray-200 dark:border-gray-700 divide-y divide-gray-100 dark:divide-gray-700">
                      {interview.questions.length === 0 ? (
                        <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No questions recorded.</p>
                      ) : (
                        interview.questions.map((q: any, idx: number) => (
                          <div key={q.id} className="p-5 space-y-2">
                            <div className="flex items-start justify-between">
                              <p className="font-medium text-gray-800 dark:text-white text-sm">
                                Q{idx + 1}. {q.question_text}
                              </p>
                              <div className="flex items-center space-x-2 ml-4 shrink-0">
                                <span className={`text-xs px-2 py-0.5 rounded-full ${getDifficultyColor(q.difficulty)}`}>
                                  {q.difficulty}
                                </span>
                                {q.user_answer && (
                                  <span className={`text-sm font-bold ${getScoreColor(q.score)}`}>
                                    {q.score.toFixed(0)}/100
                                  </span>
                                )}
                              </div>
                            </div>
                            {q.user_answer ? (
                              <>
                                <p className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                                  <span className="font-medium text-gray-700 dark:text-gray-300">Answer: </span>
                                  {q.user_answer}
                                </p>
                                {q.feedback && (
                                  <p className="text-xs text-gray-500 dark:text-gray-400 whitespace-pre-line">
                                    {q.feedback.split('\n')[0]}
                                  </p>
                                )}
                              </>
                            ) : (
                              <p className="text-sm text-gray-400 dark:text-gray-500 italic">Not answered</p>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
