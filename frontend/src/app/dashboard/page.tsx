'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { authAPI, interviewAPI } from '@/lib/api'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [interviews, setInterviews] = useState<any[]>([])
  const [resumes, setResumes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [userRes, interviewsRes] = await Promise.all([
        authAPI.getCurrentUser(),
        interviewAPI.list(),
      ])
      setUser(userRes.data)
      setInterviews(interviewsRes.data)

      // Load resumes only for regular users
      if (!userRes.data.is_admin) {
        const resumesRes = await interviewAPI.listResumes()
        setResumes(resumesRes.data)
      }
    } catch (error) {
      router.push('/auth/login')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteResume = async (resumeId: number) => {
    if (!confirm('Delete this resume?')) return
    try {
      await interviewAPI.deleteResume(resumeId)
      setResumes((prev) => prev.filter((r) => r.id !== resumeId))
    } catch (err) {
      console.error('Failed to delete resume')
    }
  }

  const handleDeleteInterview = async (interviewId: number) => {
    if (!confirm('Delete this interview and all its questions?')) return
    try {
      await interviewAPI.deleteInterview(interviewId)
      setInterviews((prev) => prev.filter((i) => i.id !== interviewId))
    } catch (err) {
      console.error('Failed to delete interview')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <nav className="navbar-premium sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold gradient-text">
            🎯 Interview RAG System
          </h1>
          <div className="flex items-center gap-4">
            <span className="badge-premium">
              {user?.full_name || user?.username}
            </span>
            <button
              onClick={handleLogout}
              className="px-6 py-2 bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-full font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h2 className="text-5xl font-bold gradient-text mb-4">
            Welcome to Your Interview Hub
          </h2>
          <p className="text-xl text-gray-700 font-medium">
            Prepare, Practice, and Perfect Your Interview Skills
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 mb-12"
        >
          {user?.is_admin ? (
            // Admin Dashboard Cards
            <>
              <div className="glass-card premium-card p-8 rounded-2xl float-animation">
                <div className="text-6xl mb-4">📊</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  System Statistics
                </h2>
                <p className="text-gray-600 mb-6 font-medium">
                  View system analytics, user activity, and interview metrics
                </p>
                <a
                  href="/admin?tab=stats"
                  className="block w-full py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center"
                  style={{ textDecoration: 'none' }}
                >
                  View Statistics
                </a>
              </div>

              <div className="glass-card premium-card p-8 rounded-2xl float-animation" style={{animationDelay: '0.2s'}}>
                <div className="text-6xl mb-4">📝</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  Question Management
                </h2>
                <p className="text-gray-600 mb-6 font-medium">
                  Add, edit, and delete questions across all domains
                </p>
                <a
                  href="/admin?tab=questions"
                  className="block w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center"
                  style={{ textDecoration: 'none' }}
                >
                  Manage Questions
                </a>
              </div>

              <div className="glass-card premium-card p-8 rounded-2xl float-animation" style={{animationDelay: '0.4s'}}>
                <div className="text-6xl mb-4">👥</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  User Management
                </h2>
                <p className="text-gray-600 mb-6 font-medium">
                  View and manage all registered users in the system
                </p>
                <a
                  href="/admin?tab=users"
                  className="block w-full py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center"
                  style={{ textDecoration: 'none' }}
                >
                  View Users
                </a>
              </div>

              <div className="glass-card premium-card p-8 rounded-2xl float-animation" style={{animationDelay: '0.6s'}}>
                <div className="text-6xl mb-4">📚</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  Document Upload
                </h2>
                <p className="text-gray-600 mb-6 font-medium">
                  Upload and index knowledge base documents
                </p>
                <a
                  href="/admin?tab=upload"
                  className="block w-full py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center"
                  style={{ textDecoration: 'none' }}
                >
                  Upload Documents
                </a>
              </div>

              <div className="glass-card premium-card p-8 rounded-2xl float-animation" style={{animationDelay: '0.8s'}}>
                <div className="text-6xl mb-4">🛡️</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  Anti-Cheat
                </h2>
                <p className="text-gray-600 mb-6 font-medium">
                  Monitor violations, manage anti-cheat settings and view flagged users
                </p>
                <a
                  href="/admin?tab=anticheat"
                  className="block w-full py-3 bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center"
                  style={{ textDecoration: 'none' }}
                >
                  View Violations
                </a>
              </div>
            </>
          ) : (
            // Regular User Dashboard Cards
            <>
              <div className="glass-card premium-card p-8 rounded-2xl float-animation">
                <div className="text-6xl mb-4">🚀</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  Start New Interview
                </h2>
                <p className="text-gray-600 mb-6 font-medium">
                  Begin your AI-powered interview session with personalized questions
                </p>
                <a
                  href="/interview/new"
                  className="btn-premium w-full block text-center"
                  style={{ textDecoration: 'none' }}
                >
                  Create Interview
                </a>
              </div>

              <div className="glass-card premium-card p-8 rounded-2xl float-animation" style={{animationDelay: '0.2s'}}>
                <div className="text-6xl mb-4">📄</div>
                <h2 className="text-2xl font-bold mb-4 text-gray-800">
                  Upload Resume
                </h2>
                <p className="text-gray-600 mb-4 font-medium">
                  Get personalized questions based on your skills and experience
                </p>
                <a
                  href="/resume/upload"
                  className="block w-full py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center mb-2"
                  style={{ textDecoration: 'none' }}
                >
                  Upload Resume
                </a>
                <a
                  href="/resume/manual"
                  className="block w-full py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105 text-center"
                  style={{ textDecoration: 'none' }}
                >
                  🛠️ Build Profile Manually
                </a>
              </div>
            </>
          )}
        </motion.div>

        {!user?.is_admin && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <h2 className="text-3xl font-bold mb-6 gradient-text">
              📚 Your Interviews
            </h2>
            {interviews.length === 0 ? (
              <div className="glass-card p-12 rounded-2xl text-center">
                <div className="text-6xl mb-4">🎯</div>
                <p className="text-xl text-gray-700 font-semibold">
                  No interviews yet. Create your first interview to get started!
                </p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {interviews.map((interview, index) => (
                  <motion.div
                    key={interview.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 }}
                    className="glass-card premium-card p-6 rounded-2xl"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <h3 className="font-bold text-xl text-gray-800">
                        {interview.title}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        interview.status === 'completed' 
                          ? 'bg-green-500 text-white' 
                          : 'bg-yellow-500 text-white'
                      }`}>
                        {interview.status === 'completed' ? '✓ Completed' : '⏳ In Progress'}
                      </span>
                    </div>
                    <div className="space-y-2 mb-4">
                      <p className="text-sm text-gray-600 font-medium flex items-center gap-2">
                        <span className="text-lg">🎯</span>
                        Domain: {interview.domain}
                      </p>
                      <p className="text-sm text-gray-600 font-medium flex items-center gap-2">
                        <span className="text-lg">📊</span>
                        Difficulty: {interview.difficulty}
                      </p>
                      <p className="text-sm text-gray-600 font-medium flex items-center gap-2">
                        <span className="text-lg">⭐</span>
                        Score: {interview.overall_score ? interview.overall_score.toFixed(1) : 0}%
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/interview/${interview.id}`)
                        }}
                        className="flex-1 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105"
                      >
                        {interview.status === 'completed' ? 'Review' : 'Continue'}
                      </button>
                      {interview.status === 'completed' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            router.push(`/interview/history/${interview.id}`)
                          }}
                          className="flex-1 py-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-105"
                        >
                          📜 History
                        </button>
                      )}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteInterview(interview.id)
                        }}
                        className="px-3 py-2 bg-red-100 text-red-600 hover:bg-red-200 rounded-xl font-semibold transition"
                        title="Delete interview"
                      >
                        🗑
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* Resumes Section */}
        {!user?.is_admin && resumes.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-12"
          >
            <h2 className="text-3xl font-bold mb-6 gradient-text">
              📄 Your Resumes
            </h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {resumes.map((resume) => (
                <div key={resume.id} className="glass-card premium-card p-6 rounded-2xl">
                  <div className="flex items-start justify-between mb-3">
                    <div className="text-4xl">📄</div>
                    <button
                      onClick={() => handleDeleteResume(resume.id)}
                      className="px-3 py-1 bg-red-100 text-red-600 hover:bg-red-200 rounded-lg text-sm font-semibold transition"
                    >
                      🗑 Remove
                    </button>
                  </div>
                  <p className="font-semibold text-gray-800 truncate mb-2">{resume.filename}</p>
                  <div className="space-y-1 text-sm text-gray-600">
                    {resume.experience_years > 0 && (
                      <p>Experience: {resume.experience_years} yr{resume.experience_years !== 1 ? 's' : ''}</p>
                    )}
                    {resume.skills && resume.skills.length > 0 && (
                      <p className="truncate">Skills: {resume.skills.slice(0, 4).join(', ')}{resume.skills.length > 4 ? '...' : ''}</p>
                    )}
                    <p className="text-xs text-gray-400">
                      Uploaded: {resume.uploaded_at ? new Date(resume.uploaded_at).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
