'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { interviewAPI } from '@/lib/api'

interface Question {
  id: number
  question_text: string
  question_type: string
  difficulty: string
  user_answer: string | null
  score: number
  feedback: string | null
  confidence_score: number
  created_at: string
  answered_at: string | null
}

interface InterviewData {
  id: number
  title: string
  domain: string
  difficulty: string
  status: string
  overall_score: number
  created_at: string
  completed_at: string | null
}

interface HistoryData {
  interview: InterviewData
  questions: Question[]
  total_questions: number
  answered_questions: number
}

export default function InterviewHistoryPage() {
  const router = useRouter()
  const params = useParams()
  const interviewId = params.id as string
  
  const [historyData, setHistoryData] = useState<HistoryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadHistory()
  }, [interviewId])

  const loadHistory = async () => {
    try {
      setLoading(true)
      const response = await interviewAPI.getHistory(parseInt(interviewId))
      setHistoryData(response.data)
    } catch (err: any) {
      console.error('Error loading history:', err)
      setError(err.response?.data?.detail || 'Failed to load interview history')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreEmoji = (score: number) => {
    if (score >= 90) return '🌟'
    if (score >= 80) return '✅'
    if (score >= 70) return '👍'
    if (score >= 60) return '👌'
    return '📝'
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⏳</div>
          <div className="text-xl font-semibold">Loading interview history...</div>
        </div>
      </div>
    )
  }

  if (error || !historyData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card p-8 rounded-2xl text-center max-w-md">
          <div className="text-6xl mb-4">❌</div>
          <h2 className="text-2xl font-bold mb-4 text-gray-800">Error</h2>
          <p className="text-gray-600 mb-6">{error || 'Interview not found'}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="btn-premium"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const { interview, questions } = historyData

  return (
    <div className="min-h-screen pb-12">
      {/* Navigation Bar */}
      <nav className="navbar-premium sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold gradient-text">
            🎯 Interview History
          </h1>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-full font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105"
          >
            ← Back to Dashboard
          </button>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        {/* Interview Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card premium-card p-8 rounded-2xl mb-8"
        >
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-4xl font-bold gradient-text mb-2">
                {interview.title}
              </h2>
              <p className="text-gray-600 font-medium">
                {formatDate(interview.created_at)}
              </p>
            </div>
            <span className={`px-4 py-2 rounded-full text-sm font-bold ${
              interview.status === 'completed' 
                ? 'bg-green-500 text-white' 
                : 'bg-yellow-500 text-white'
            }`}>
              {interview.status === 'completed' ? '✓ Completed' : '⏳ In Progress'}
            </span>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl">
              <div className="text-3xl mb-2">🎯</div>
              <div className="text-sm text-gray-600 font-medium">Domain</div>
              <div className="text-lg font-bold text-gray-800">{interview.domain}</div>
            </div>
            
            <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl">
              <div className="text-3xl mb-2">📊</div>
              <div className="text-sm text-gray-600 font-medium">Difficulty</div>
              <div className="text-lg font-bold text-gray-800 capitalize">{interview.difficulty}</div>
            </div>
            
            <div className="text-center p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl">
              <div className="text-3xl mb-2">⭐</div>
              <div className="text-sm text-gray-600 font-medium">Overall Score</div>
              <div className={`text-2xl font-bold ${getScoreColor(interview.overall_score)}`}>
                {interview.overall_score.toFixed(1)}%
              </div>
            </div>
            
            <div className="text-center p-4 bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl">
              <div className="text-3xl mb-2">📝</div>
              <div className="text-sm text-gray-600 font-medium">Questions</div>
              <div className="text-lg font-bold text-gray-800">
                {historyData.answered_questions} / {historyData.total_questions}
              </div>
            </div>
          </div>

          {interview.completed_at && (
            <div className="mt-6 text-center text-gray-600 font-medium">
              Completed on {formatDate(interview.completed_at)}
            </div>
          )}
        </motion.div>

        {/* Questions Timeline */}
        <div className="space-y-6">
          <h3 className="text-3xl font-bold gradient-text mb-6">
            📚 Questions & Answers
          </h3>

          {questions.length === 0 ? (
            <div className="glass-card p-12 rounded-2xl text-center">
              <div className="text-6xl mb-4">📭</div>
              <p className="text-xl text-gray-700 font-semibold">
                No questions yet. Start the interview to see questions here!
              </p>
            </div>
          ) : (
            questions.map((question, index) => (
              <motion.div
                key={question.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass-card premium-card p-6 rounded-2xl"
              >
                {/* Question Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="text-3xl">{index + 1}.</div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
                          {question.difficulty}
                        </span>
                        <span className="text-sm text-gray-500 font-medium">
                          {formatDate(question.created_at)}
                        </span>
                      </div>
                      <h4 className="text-xl font-bold text-gray-800 mb-3">
                        {question.question_text}
                      </h4>
                    </div>
                  </div>
                  {question.user_answer && (
                    <div className="text-center ml-4">
                      <div className="text-3xl mb-1">{getScoreEmoji(question.score)}</div>
                      <div className={`text-2xl font-bold ${getScoreColor(question.score)}`}>
                        {question.score.toFixed(0)}%
                      </div>
                    </div>
                  )}
                </div>

                {/* User Answer */}
                {question.user_answer ? (
                  <div className="space-y-4">
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-4 rounded-xl">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xl">💬</span>
                        <span className="font-bold text-gray-700">Your Answer:</span>
                      </div>
                      <p className="text-gray-700 whitespace-pre-wrap">{question.user_answer}</p>
                      {question.answered_at && (
                        <p className="text-sm text-gray-500 mt-2 font-medium">
                          Answered: {formatDate(question.answered_at)}
                        </p>
                      )}
                    </div>

                    {/* Feedback */}
                    {question.feedback && (
                      <div className="bg-gradient-to-br from-purple-50 to-pink-50 p-4 rounded-xl">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xl">🤖</span>
                          <span className="font-bold text-gray-700">AI Feedback:</span>
                        </div>
                        <div className="text-gray-700 whitespace-pre-wrap">
                          {question.feedback}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-gray-50 p-4 rounded-xl text-center">
                    <span className="text-gray-500 font-medium">
                      ⏳ Not answered yet
                    </span>
                  </div>
                )}
              </motion.div>
            ))
          )}
        </div>

        {/* Back Button */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-12 text-center"
        >
          <button
            onClick={() => router.push('/dashboard')}
            className="btn-premium px-12 py-4 text-lg"
          >
            ← Back to Dashboard
          </button>
        </motion.div>
      </div>
    </div>
  )
}
