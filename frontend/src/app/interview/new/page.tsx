'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { interviewAPI } from '@/lib/api'

const ALL_DOMAINS = [
  'Machine Learning', 'Data Structures & Algorithms', 'Web Development',
  'System Design', 'Python Programming', 'Databases & SQL',
  'Cloud & DevOps', 'General Interview',
]

type DomainMode = 'all' | 'resume' | 'coding'

export default function NewInterviewPage() {
  const router = useRouter()
  const [title, setTitle] = useState('')
  const [domain, setDomain] = useState('Machine Learning')
  const [difficulty, setDifficulty] = useState('medium')
  const [evalMode, setEvalMode] = useState<'semantic' | 'llm'>('semantic')
  const [resumeId, setResumeId] = useState<number | null>(null)
  const [resumes, setResumes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingResumes, setLoadingResumes] = useState(true)
  const [error, setError] = useState('')

  const [domainMode, setDomainMode] = useState<DomainMode | null>(null)
  const [resumeDomains, setResumeDomains] = useState<string[]>([])
  const [resumeSkills, setResumeSkills] = useState<string[]>([])
  const [loadingDomains, setLoadingDomains] = useState(false)

  const isCodingMode = domainMode === 'coding'
  const needsResume = domainMode === 'all' || domainMode === 'resume'

  useEffect(() => { loadResumes() }, [])

  useEffect(() => {
    if (resumeId) {
      setResumeDomains([])
      fetchResumeDomains(resumeId)
    }
  }, [resumeId])

  useEffect(() => {
    if (domainMode === 'coding') setDomain('Coding Round')
    else if (domainMode === 'resume' && resumeDomains.length > 0)
      setDomain(resumeDomains.find(d => d !== 'Coding Round') || resumeDomains[0])
    else if (domainMode === 'all') setDomain('Machine Learning')
  }, [domainMode, resumeDomains])

  const loadResumes = async () => {
    try {
      const res = await interviewAPI.listResumes()
      setResumes(res.data)
      if (res.data.length > 0) setResumeId(res.data[0].id)
    } catch { } finally { setLoadingResumes(false) }
  }

  const fetchResumeDomains = async (id: number) => {
    setLoadingDomains(true)
    try {
      const res = await interviewAPI.getResumeDomains(id)
      setResumeDomains(res.data.matched_domains)
      setResumeSkills(res.data.resume_skills || [])
    } catch { setResumeDomains([]) } finally { setLoadingDomains(false) }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!domainMode) { setError('Please choose an interview type'); return }

    // Resume required for all/resume modes
    if (needsResume && resumes.length === 0) {
      setError('Please upload your resume first to use this interview type')
      return
    }
    if (needsResume && !resumeId) {
      setError('Please select a resume')
      return
    }

    setError('')
    setLoading(true)
    try {
      const res = await interviewAPI.create({
        title,
        domain,
        difficulty,
        resume_id: isCodingMode ? undefined : (resumeId ?? undefined),
        eval_mode: evalMode
      })
      router.push(`/interview/${res.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create interview')
      setLoading(false)
    }
  }

  const availableDomains =
    domainMode === 'resume' ? resumeDomains.filter(d => d !== 'Coding Round') : ALL_DOMAINS

  const canSubmit = !loading && domainMode && (isCodingMode || resumes.length > 0)

  if (loadingResumes) return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="text-xl text-gray-800">Loading...</div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-4">
      <div className="container mx-auto max-w-2xl">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-8 shadow-2xl">
          <h1 className="text-3xl font-bold mb-6 text-gray-800">Start New Interview</h1>

          {error && <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-6">

            {/* Interview Type — always visible */}
            <div>
              <label className="block text-sm font-medium mb-3 text-gray-700">Choose Interview Type *</label>
              <div className="grid grid-cols-1 gap-3">

                <button type="button" onClick={() => setDomainMode('all')}
                  className={`p-4 rounded-xl border-2 text-left transition ${domainMode === 'all' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300'}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🌐</span>
                    <div>
                      <p className="font-semibold text-gray-800">All Domains</p>
                      <p className="text-xs text-gray-500">ML, DSA, Web Dev, System Design, and more — requires resume</p>
                    </div>
                  </div>
                </button>

                <button type="button" onClick={() => setDomainMode('resume')}
                  className={`p-4 rounded-xl border-2 text-left transition ${domainMode === 'resume' ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">📄</span>
                    <div>
                      <p className="font-semibold text-gray-800">Based on My Resume</p>
                      <p className="text-xs text-gray-500">Questions tailored to your skills — requires resume</p>
                    </div>
                  </div>
                </button>

                <button type="button" onClick={() => setDomainMode('coding')}
                  className={`p-4 rounded-xl border-2 text-left transition ${domainMode === 'coding' ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-green-300'}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">💻</span>
                    <div>
                      <p className="font-semibold text-gray-800">Coding Round</p>
                      <p className="text-xs text-gray-500">Algorithm & data structure problems — no resume needed</p>
                      <span className="text-xs text-green-600 font-semibold">✓ No resume required</span>
                    </div>
                  </div>
                </button>

              </div>
            </div>

            {/* Resume section — only shown for all/resume modes */}
            <AnimatePresence>
              {needsResume && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  {resumes.length === 0 ? (
                    <div className="p-4 bg-yellow-100 border border-yellow-400 text-yellow-800 rounded-lg">
                      <p className="font-semibold mb-2">⚠️ Resume Required</p>
                      <p className="text-sm mb-3">This interview type needs your resume. Upload one to continue.</p>
                      <div className="flex gap-2">
                        <button type="button" onClick={() => router.push('/resume/upload')}
                          className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 font-semibold text-sm">
                          Upload Resume
                        </button>
                        <button type="button" onClick={() => router.push('/resume/manual')}
                          className="px-4 py-2 bg-yellow-100 border border-yellow-600 text-yellow-800 rounded-lg hover:bg-yellow-200 font-semibold text-sm">
                          Build Profile Manually
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <label className="block text-sm font-medium mb-2 text-gray-700">Select Resume *</label>
                      <select value={resumeId || ''} onChange={e => setResumeId(parseInt(e.target.value))}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800">
                        <option value="">Choose a resume...</option>
                        {resumes.map(r => (
                          <option key={r.id} value={r.id}>{r.filename} — {r.experience_years}y — {r.skills?.length || 0} skills</option>
                        ))}
                      </select>
                      <div className="mt-2 flex gap-3">
                        <button type="button" onClick={() => router.push('/resume/upload')}
                          className="text-sm text-blue-600 hover:text-blue-700 font-medium">+ Upload New Resume</button>
                        <button type="button" onClick={() => router.push('/resume/manual')}
                          className="text-sm text-purple-600 hover:text-purple-700 font-medium">🛠️ Build Manually</button>
                      </div>
                      {/* Resume-based domain info */}
                      {domainMode === 'resume' && resumeId && (
                        <div className="mt-3 p-3 bg-purple-50 rounded-lg text-xs text-purple-700">
                          {loadingDomains ? 'Analysing resume...' : (
                            resumeDomains.filter(d => d !== 'Coding Round').length > 0
                              ? <>Matched domains: <strong>{resumeDomains.filter(d => d !== 'Coding Round').join(', ')}</strong>
                                {resumeSkills.length > 0 && <> · Skills: {resumeSkills.slice(0, 5).join(', ')}{resumeSkills.length > 5 ? '...' : ''}</>}</>
                              : 'No specific domains detected — will use General Interview'
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Domain selector */}
            <AnimatePresence>
              {domainMode && domainMode !== 'coding' && (needsResume ? resumes.length > 0 : true) && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <label className="block text-sm font-medium mb-2 text-gray-700">Domain *</label>
                  <select value={domain} onChange={e => setDomain(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800">
                    {availableDomains.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Title */}
            <AnimatePresence>
              {domainMode && (isCodingMode || resumes.length > 0) && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <label className="block text-sm font-medium mb-2 text-gray-700">Interview Title *</label>
                  <input type="text" value={title} onChange={e => setTitle(e.target.value)}
                    placeholder={isCodingMode ? 'e.g., Coding Round Practice' : 'e.g., Python Developer Interview'}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
                    required />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Difficulty */}
            <AnimatePresence>
              {domainMode && (isCodingMode || resumes.length > 0) && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <label className="block text-sm font-medium mb-2 text-gray-700">Difficulty *</label>
                  <div className="grid grid-cols-3 gap-3">
                    {['easy', 'medium', 'hard'].map(level => (
                      <button key={level} type="button" onClick={() => setDifficulty(level)}
                        className={`py-3 rounded-lg font-semibold transition ${difficulty === level ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Eval mode — only for non-coding */}
            <AnimatePresence>
              {domainMode && domainMode !== 'coding' && resumes.length > 0 && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <label className="block text-sm font-medium mb-3 text-gray-700">Answer Evaluation Mode</label>
                  <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
                    <div className="flex-1">
                      <p className={`font-semibold text-sm ${evalMode === 'semantic' ? 'text-blue-700' : 'text-gray-400'}`}>Semantic Similarity</p>
                      <p className="text-xs text-gray-500">Fast, offline — keyword & meaning match</p>
                    </div>
                    <button type="button" onClick={() => setEvalMode(evalMode === 'semantic' ? 'llm' : 'semantic')}
                      className={`relative w-14 h-7 rounded-full transition-colors duration-300 ${evalMode === 'llm' ? 'bg-purple-600' : 'bg-blue-500'}`}>
                      <span className={`absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform duration-300 ${evalMode === 'llm' ? 'translate-x-7' : 'translate-x-0'}`} />
                    </button>
                    <div className="flex-1 text-right">
                      <p className={`font-semibold text-sm ${evalMode === 'llm' ? 'text-purple-700' : 'text-gray-400'}`}>LLM Evaluation</p>
                      <p className="text-xs text-gray-500">Deeper AI feedback</p>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <div className="flex gap-4">
              <button type="button" onClick={() => router.push('/dashboard')}
                className="flex-1 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition">
                Cancel
              </button>
              <button type="submit" disabled={!canSubmit}
                className="flex-1 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? 'Creating...' : 'Start Interview'}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  )
}
