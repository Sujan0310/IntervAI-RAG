'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { interviewAPI } from '@/lib/api'

export default function InterviewSessionPage() {
  const router = useRouter()
  const params = useParams()
  const interviewId = parseInt(params.id as string)

  const [interview, setInterview] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentQuestion, setCurrentQuestion] = useState<any>(null)
  const [isEnding, setIsEnding] = useState(false)
  const [currentDifficulty, setCurrentDifficulty] = useState<string>('medium')
  const [isListening, setIsListening] = useState(false)
  const [antiCheatEnabled, setAntiCheatEnabled] = useState(false)
  const violationCountRef = useRef<Record<string, number>>({})
  const recognitionRef = useRef<any>(null)
  const isListeningRef = useRef<boolean>(false)   // ref mirror of isListening for use in callbacks
  const textBeforeMicRef = useRef<string>('')
  const cursorPosRef = useRef<number>(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { loadInterview() }, [])

  // Load anti-cheat status
  useEffect(() => {
    interviewAPI.getAntiCheatStatus().then(res => {
      setAntiCheatEnabled(res.data.anticheat_enabled)
    }).catch(() => {})
  }, [])

  // Anti-cheat event listeners
  useEffect(() => {
    if (!antiCheatEnabled || !interviewId) return

    const report = (type: string, details: string) => {
      const count = (violationCountRef.current[type] || 0) + 1
      violationCountRef.current[type] = count
      interviewAPI.reportViolation({
        interview_id: interviewId,
        violation_type: type,
        details: `${details} (occurrence #${count})`
      }).catch(() => {})
    }

    // Tab switch / window blur
    const onVisibilityChange = () => {
      if (document.hidden) report('tab_switch', 'User switched tab or minimized window')
    }
    const onBlur = () => report('window_blur', 'Browser window lost focus')

    // Copy / paste
    const onCopy = () => report('copy', 'User copied text from the page')
    const onPaste = () => report('paste', 'User pasted text into the page')

    // Right-click
    const onContextMenu = (e: MouseEvent) => {
      e.preventDefault()
      report('right_click', 'User right-clicked on the page')
    }

    // Multiple displays (Screen API)
    const checkDisplays = () => {
      if ((window.screen as any).isExtended) {
        report('multiple_displays', `Extended display detected (screen: ${window.screen.width}x${window.screen.height})`)
      }
    }
    checkDisplays()
    const displayInterval = setInterval(checkDisplays, 30000)

    // DevTools heuristic (window size difference)
    const checkDevTools = () => {
      const threshold = 160
      if (window.outerWidth - window.innerWidth > threshold || window.outerHeight - window.innerHeight > threshold) {
        report('devtools_open', `DevTools may be open (outer: ${window.outerWidth}x${window.outerHeight}, inner: ${window.innerWidth}x${window.innerHeight})`)
      }
    }
    const devToolsInterval = setInterval(checkDevTools, 10000)

    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('blur', onBlur)
    document.addEventListener('copy', onCopy)
    document.addEventListener('paste', onPaste)
    document.addEventListener('contextmenu', onContextMenu)

    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
      window.removeEventListener('blur', onBlur)
      document.removeEventListener('copy', onCopy)
      document.removeEventListener('paste', onPaste)
      document.removeEventListener('contextmenu', onContextMenu)
      clearInterval(displayInterval)
      clearInterval(devToolsInterval)
    }
  }, [antiCheatEnabled, interviewId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadInterview = async () => {
    try {
      const response = await interviewAPI.list()
      const found = response.data.find((i: any) => i.id === interviewId)
      if (!found) { setError('Interview not found'); return }
      setInterview(found)
      setCurrentDifficulty(found.difficulty)
    } catch {
      setError('Failed to load interview')
    } finally {
      setLoading(false)
    }
  }

  const toggleMic = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Try Chrome.')
      return
    }

    if (isListening) {
      recognitionRef.current?.stop()
      isListeningRef.current = false
      setIsListening(false)
      return
    }

    // Capture current text and cursor position before starting
    const currentText = input
    const cursorPos = textareaRef.current?.selectionStart ?? currentText.length
    textBeforeMicRef.current = currentText
    cursorPosRef.current = cursorPos

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: any) => {
      let newTranscript = ''
      for (let i = 0; i < event.results.length; i++) {
        newTranscript += event.results[i][0].transcript
      }
      const before = textBeforeMicRef.current.slice(0, cursorPosRef.current)
      const after = textBeforeMicRef.current.slice(cursorPosRef.current)
      const separator = before.length > 0 && !before.endsWith(' ') ? ' ' : ''
      setInput(before + separator + newTranscript + after)
    }

    recognition.onerror = (event: any) => {
      if (event.error === 'no-speech') return
      isListeningRef.current = false
      setIsListening(false)
    }

    recognition.onend = () => {
      // Restart automatically if user hasn't manually stopped
      if (isListeningRef.current) {
        try { recognition.start() } catch {}
      }
    }

    recognitionRef.current = recognition
    isListeningRef.current = true
    setIsListening(true)
    recognition.start()
  }

  const handleEndInterview = async () => {
    setIsEnding(true)
    try {
      await interviewAPI.endInterview(interviewId)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to end interview')
      setIsEnding(false)
    }
  }

  const handleGenerateQuestion = async (difficulty?: string) => {
    setIsGenerating(true)
    setError('')
    const useDifficulty = difficulty || currentDifficulty || interview?.difficulty || 'medium'

    try {
      const response = await interviewAPI.generateQuestion({
        interview_id: interviewId,
        domain: interview.domain,
        difficulty: useDifficulty
      })

      setCurrentQuestion(response.data)
      setMessages(prev => [...prev, {
        type: 'question',
        content: response.data.question_text,
        difficulty: response.data.difficulty,
        confidence: response.data.confidence_score,
        timestamp: new Date()
      }])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate question. Make sure documents are uploaded in Admin Panel.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !currentQuestion) return

    const userAnswer = input
    setInput('')
    setCurrentQuestion(null)

    // Stop mic if still recording
    if (isListening) {
      recognitionRef.current?.stop()
      isListeningRef.current = false
      setIsListening(false)
    }

    setMessages(prev => [...prev, {
      type: 'answer',
      content: userAnswer,
      timestamp: new Date()
    }])

    setIsGenerating(true)

    try {
      const response = await interviewAPI.submitAnswer({
        question_id: currentQuestion.id,
        answer: userAnswer
      })

      const adaptiveInfo = response.data.adaptive_difficulty
      const nextDifficulty = adaptiveInfo?.current_difficulty || currentDifficulty

      // Update tracked difficulty immediately
      setCurrentDifficulty(nextDifficulty)

      // Add feedback
      setMessages(prev => [...prev, {
        type: 'feedback',
        content: response.data.feedback,
        score: response.data.score,
        timestamp: new Date()
      }])

      // Show difficulty change or encouragement
      if (adaptiveInfo?.difficulty_changed) {
        setMessages(prev => [...prev, {
          type: 'system',
          content: `🎯 ${adaptiveInfo.adjustment_reason}\n${adaptiveInfo.encouragement}\n\nNext question: ${nextDifficulty.toUpperCase()} difficulty`,
          timestamp: new Date()
        }])
      } else if (adaptiveInfo?.encouragement) {
        setMessages(prev => [...prev, {
          type: 'system',
          content: `${adaptiveInfo.encouragement} (${nextDifficulty} difficulty)`,
          timestamp: new Date()
        }])
      }

      // Auto-fetch next question at the new adaptive difficulty after a short delay
      setTimeout(() => {
        handleGenerateQuestion(nextDifficulty)
      }, 1500)

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit answer')
      setIsGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-xl text-gray-800">Loading interview...</div>
      </div>
    )
  }

  if (error && !interview) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <div className="text-center">
          <p className="text-xl text-red-600 mb-4">{error}</p>
          <button onClick={() => router.push('/dashboard')} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      <nav className="bg-blue-600 shadow-lg">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">{interview.title}</h1>
            <p className="text-sm text-blue-100">
              {interview.domain} •{' '}
              <span className={`font-semibold ${
                currentDifficulty === 'hard' ? 'text-red-200' :
                currentDifficulty === 'easy' ? 'text-green-200' : 'text-yellow-200'
              }`}>
                {currentDifficulty.toUpperCase()}
              </span>
            </p>
          </div>
          <button
            onClick={handleEndInterview}
            disabled={isEnding}
            className="px-4 py-2 bg-white text-blue-600 rounded-lg hover:bg-blue-50 transition font-semibold disabled:opacity-50"
          >
            {isEnding ? 'Ending...' : 'End Interview'}
          </button>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {antiCheatEnabled && (
          <div className="mb-4 p-3 bg-red-50 border border-red-300 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <span className="text-lg">🛡️</span>
            <span><strong>Anti-Cheat Active</strong> — Tab switches, copy-paste, and suspicious activity are being monitored and reported.</span>
          </div>
        )}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <div className="space-y-4 mb-6">
          {messages.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`p-4 rounded-lg ${
                msg.type === 'question' ? 'bg-blue-100 border-l-4 border-blue-600' :
                msg.type === 'answer' ? 'bg-gray-100 border-l-4 border-gray-600 ml-8' :
                msg.type === 'system' ? 'bg-yellow-50 border-l-4 border-yellow-400' :
                'bg-green-100 border-l-4 border-green-600'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="text-2xl">
                  {msg.type === 'question' ? '❓' :
                   msg.type === 'answer' ? '💬' :
                   msg.type === 'system' ? '🎯' : '✅'}
                </div>
                <div className="flex-1">
                  {msg.type === 'question' && msg.difficulty && (
                    <span className={`text-xs font-bold px-2 py-0.5 rounded mb-2 inline-block ${
                      msg.difficulty === 'hard' ? 'bg-red-200 text-red-800' :
                      msg.difficulty === 'easy' ? 'bg-green-200 text-green-800' :
                      'bg-yellow-200 text-yellow-800'
                    }`}>
                      {msg.difficulty.toUpperCase()}
                    </span>
                  )}
                  <p className="text-gray-800 whitespace-pre-wrap font-medium">{msg.content}</p>
                  {msg.score !== undefined && (
                    <div className="mt-2 text-sm font-semibold text-gray-700">
                      Score: {msg.score.toFixed(1)}/100
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}

          {isGenerating && (
            <div className="flex justify-center">
              <div className="bg-gray-100 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce" />
                    <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '0.1s'}} />
                    <div className="w-3 h-3 bg-blue-600 rounded-full animate-bounce" style={{animationDelay: '0.2s'}} />
                  </div>
                  <span className="text-sm text-gray-600">
                    {currentQuestion ? 'Evaluating...' : `Loading ${currentDifficulty} question...`}
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          {messages.length === 0 && (
            <div className="text-center">
              <p className="text-gray-700 mb-4 font-medium">Ready to start your interview?</p>
              <button
                onClick={() => handleGenerateQuestion()}
                disabled={isGenerating}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
              >
                {isGenerating ? 'Generating...' : '🚀 Start Interview'}
              </button>
            </div>
          )}

          {currentQuestion && (
              <form onSubmit={handleSubmitAnswer} className="space-y-3">
                <div className="flex gap-2 items-start">
                  <button
                    type="button"
                    onClick={toggleMic}
                    disabled={isGenerating}
                    title={isListening ? 'Stop recording' : 'Start voice input'}
                    className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center transition-all font-bold text-xl shadow-md disabled:opacity-50 ${
                      isListening ? 'bg-red-500 text-white animate-pulse' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                    }`}
                  >
                    🎤
                  </button>
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={isListening ? 'Listening... speak now' : 'Type your answer or use the mic...'}
                    rows={4}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-800 font-medium"
                    disabled={isGenerating}
                  />
                </div>
                {isListening && (
                  <p className="text-xs text-red-500 font-medium flex items-center gap-1">
                    <span className="inline-block w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                    Recording — click the mic again to stop
                  </p>
                )}
                <div className="flex gap-3">
                  <button
                    type="submit"
                    disabled={isGenerating || !input.trim()}
                    className="flex-1 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    {isGenerating ? 'Submitting...' : '📤 Submit Answer'}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCurrentQuestion(null)
                      setInput('')
                      if (isListening) { recognitionRef.current?.stop(); isListeningRef.current = false; setIsListening(false) }
                      handleGenerateQuestion(currentDifficulty)
                    }}
                    disabled={isGenerating}
                    className="px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition"
                  >
                    Skip
                  </button>
                </div>
              </form>
          )}
        </div>
      </div>
    </div>
  )
}
