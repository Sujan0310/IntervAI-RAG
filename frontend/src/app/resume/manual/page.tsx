'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { interviewAPI } from '@/lib/api'

const SKILL_CATEGORIES = {
  'Programming Languages': ['Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'PHP', 'Ruby', 'Swift', 'Kotlin'],
  'Web Development': ['React', 'Next.js', 'Vue.js', 'Angular', 'Node.js', 'Express', 'FastAPI', 'Django', 'Flask', 'HTML/CSS', 'Tailwind CSS'],
  'Databases': ['SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite', 'Elasticsearch', 'Cassandra'],
  'Cloud & DevOps': ['AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'CI/CD', 'Terraform', 'Linux', 'Nginx'],
  'Data & ML': ['Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Pandas', 'NumPy', 'Data Science', 'NLP', 'Computer Vision'],
  'CS Fundamentals': ['Data Structures', 'Algorithms', 'System Design', 'OOP', 'REST APIs', 'GraphQL', 'Microservices'],
  'Tools': ['Git', 'GitHub', 'Jira', 'Agile/Scrum', 'VS Code', 'Postman'],
}

const ROLES = [
  'Software Engineer', 'Frontend Developer', 'Backend Developer', 'Full Stack Developer',
  'Data Scientist', 'ML Engineer', 'DevOps Engineer', 'Cloud Architect',
  'Mobile Developer', 'QA Engineer', 'Data Engineer', 'Security Engineer',
]

export default function ManualProfilePage() {
  const router = useRouter()
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [role, setRole] = useState('Software Engineer')
  const [experienceYears, setExperienceYears] = useState(1)
  const [customSkill, setCustomSkill] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const toggleSkill = (skill: string) => {
    setSelectedSkills(prev =>
      prev.includes(skill) ? prev.filter(s => s !== skill) : [...prev, skill]
    )
  }

  const addCustomSkill = () => {
    const s = customSkill.trim()
    if (s && !selectedSkills.includes(s)) {
      setSelectedSkills(prev => [...prev, s])
    }
    setCustomSkill('')
  }

  const handleSubmit = async () => {
    if (selectedSkills.length === 0) {
      setError('Please select at least one skill')
      return
    }
    setError('')
    setLoading(true)
    try {
      await interviewAPI.createManualProfile({
        skills: selectedSkills,
        experience_years: experienceYears,
        role,
      })
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create profile')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-4">
      <div className="container mx-auto max-w-3xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-8 shadow-2xl"
        >
          <div className="flex items-center gap-3 mb-6">
            <span className="text-4xl">🛠️</span>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Build Your Profile Manually</h1>
              <p className="text-sm text-gray-500">Select your skills and we'll tailor the interview to you</p>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg text-sm">{error}</div>
          )}

          {/* Role */}
          <div className="mb-6">
            <label className="block text-sm font-semibold mb-2 text-gray-700">Your Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800"
            >
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          {/* Experience */}
          <div className="mb-6">
            <label className="block text-sm font-semibold mb-2 text-gray-700">
              Years of Experience: <span className="text-blue-600 font-bold">{experienceYears}</span>
            </label>
            <input
              type="range" min={0} max={20} value={experienceYears}
              onChange={e => setExperienceYears(parseInt(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0 (Fresher)</span><span>5</span><span>10</span><span>15</span><span>20+</span>
            </div>
          </div>

          {/* Skills by category */}
          <div className="mb-6">
            <label className="block text-sm font-semibold mb-3 text-gray-700">
              Select Your Skills
              {selectedSkills.length > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-bold">
                  {selectedSkills.length} selected
                </span>
              )}
            </label>

            <div className="space-y-4">
              {Object.entries(SKILL_CATEGORIES).map(([category, skills]) => (
                <div key={category}>
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">{category}</p>
                  <div className="flex flex-wrap gap-2">
                    {skills.map(skill => (
                      <button
                        key={skill}
                        type="button"
                        onClick={() => toggleSkill(skill)}
                        className={`px-3 py-1.5 rounded-full text-sm font-medium border transition ${
                          selectedSkills.includes(skill)
                            ? 'bg-blue-600 text-white border-blue-600'
                            : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                        }`}
                      >
                        {selectedSkills.includes(skill) ? '✓ ' : ''}{skill}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Custom skill input */}
          <div className="mb-6">
            <label className="block text-sm font-semibold mb-2 text-gray-700">Add Custom Skill</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={customSkill}
                onChange={e => setCustomSkill(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addCustomSkill()}
                placeholder="e.g. Solidity, Rust, Figma..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800 text-sm"
              />
              <button
                type="button"
                onClick={addCustomSkill}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold text-sm"
              >
                + Add
              </button>
            </div>
          </div>

          {/* Selected skills preview */}
          <AnimatePresence>
            {selectedSkills.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-6 p-4 bg-blue-50 rounded-xl border border-blue-200"
              >
                <p className="text-sm font-semibold text-blue-700 mb-2">Selected Skills:</p>
                <div className="flex flex-wrap gap-2">
                  {selectedSkills.map(skill => (
                    <span key={skill}
                      className="px-3 py-1 bg-blue-600 text-white rounded-full text-xs font-medium flex items-center gap-1">
                      {skill}
                      <button onClick={() => toggleSkill(skill)} className="ml-1 hover:text-red-200">×</button>
                    </span>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Buttons */}
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => router.push('/resume/upload')}
              className="flex-1 py-3 bg-gray-100 text-gray-700 rounded-lg font-semibold hover:bg-gray-200 transition"
            >
              ← Upload Resume Instead
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading || selectedSkills.length === 0}
              className="flex-1 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating Profile...' : '🚀 Create Profile & Continue'}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
