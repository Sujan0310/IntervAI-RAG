'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { authAPI } from '@/lib/api'
import Link from 'next/link'

export default function LoginPage() {
  const router = useRouter()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await authAPI.login(username, password)
      localStorage.setItem('token', response.data.access_token)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="glass-card rounded-3xl p-10 shadow-premium">
          <div className="text-center mb-8">
            <div className="text-6xl mb-4 float-animation">🎯</div>
            <h1 className="text-4xl font-bold gradient-text mb-2">
              Welcome Back
            </h1>
            <p className="text-gray-600 font-medium">
              Sign in to continue your interview journey
            </p>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-6 p-4 bg-red-100 border-2 border-red-400 text-red-700 rounded-xl font-semibold error-glow"
            >
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-bold mb-2 text-gray-700">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Enter your username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-bold mb-2 text-gray-700">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="Enter your password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-premium w-full py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="spinner"></div>
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-gray-600 font-medium">
              Don't have an account?{' '}
              <Link href="/auth/register" className="text-purple-600 hover:text-purple-700 font-bold hover:underline">
                Sign up
              </Link>
            </p>
          </div>

          <div className="mt-6 p-4 glass rounded-xl">
            <p className="text-sm text-gray-700 font-bold mb-2">🎁 Demo Accounts:</p>
            <div className="space-y-1 text-xs text-gray-600 font-medium">
              <p>👤 Admin: <span className="font-bold">admin</span> / <span className="font-bold">admin123</span></p>
              <p>👤 User: <span className="font-bold">demo</span> / <span className="font-bold">demo123</span></p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
