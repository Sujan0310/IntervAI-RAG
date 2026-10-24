'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h1 className="text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Interview RAG System
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-3xl mx-auto">
            Next-Generation Intelligent Interview Preparation using Advanced Retrieval-Augmented Generation
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/auth/login">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold shadow-lg hover:bg-blue-700 transition"
              >
                Get Started
              </motion.button>
            </Link>
            <Link href="/auth/register">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-3 bg-white text-blue-600 rounded-lg font-semibold shadow-lg hover:bg-gray-50 transition border-2 border-blue-600"
              >
                Sign Up
              </motion.button>
            </Link>
          </div>
        </motion.div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="glass-dark p-6 rounded-xl hover:shadow-2xl transition"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-xl font-bold mb-2 text-gray-800 dark:text-white">
                {feature.title}
              </h3>
              <p className="text-gray-600 dark:text-gray-300">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>


      </div>
    </main>
  )
}

const features = [
  {
    icon: '🎯',
    title: 'Strict RAG Architecture',
    description: 'Zero hallucination with mandatory source attribution. Every answer grounded in retrieved context.',
  },
  {
    icon: '🔍',
    title: 'Hybrid Retrieval',
    description: 'Combines dense (FAISS) and sparse (BM25) retrieval with cross-encoder re-ranking.',
  },
  {
    icon: '🧠',
    title: 'Adaptive Interviewing',
    description: 'Resume-based personalized questions with dynamic difficulty adjustment.',
  },
  {
    icon: '📊',
    title: 'Real-Time Evaluation',
    description: 'Semantic scoring with AI-powered feedback and performance analytics.',
  },
  {
    icon: '🎨',
    title: 'Premium UI',
    description: 'Modern glassmorphism design with streaming responses and smooth animations.',
  },
  {
    icon: '🔒',
    title: 'Local-First',
    description: 'All retrieval components run locally for privacy and control.',
  },
]


