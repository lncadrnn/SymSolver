import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import WelcomeScreen from './components/WelcomeScreen'
import InputBar from './components/InputBar'

function App() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const chatAreaRef = useRef(null)

  const scrollToBottom = () => {
    if (chatAreaRef.current) {
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (equation) => {
    if (!equation.trim() || isLoading) return

    const userMessage = { role: 'user', content: equation.trim() }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    // Add a placeholder bot message with loading state
    const botMessage = {
      role: 'bot',
      content: null,
      loading: true,
      steps: [],
      finalAnswer: null,
      error: null,
    }
    setMessages((prev) => [...prev, botMessage])

    try {
      const response = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ equation: equation.trim() }),
      })

      const data = await response.json()

      if (!response.ok) {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'bot',
            loading: false,
            error: data.detail || data.error || 'Failed to solve the equation.',
            steps: [],
            finalAnswer: null,
          }
          return updated
        })
      } else {
        // Start typewriter animation for steps
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'bot',
            loading: false,
            steps: data.steps || [],
            finalAnswer: data.final_answer || null,
            verificationSteps: data.verification_steps || [],
            equation: data.equation || equation.trim(),
            error: null,
            animating: true,
          }
          return updated
        })
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'bot',
          loading: false,
          error: 'Could not connect to the solver. Make sure the backend is running.',
          steps: [],
          finalAnswer: null,
        }
        return updated
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleExampleClick = (equation) => {
    handleSend(equation)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: '#7c5cfc' }}>
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          <span className="header-title">SymSolver</span>
          <span className="header-subtitle">Linear Equation Solver</span>
        </div>
      </header>

      <div className="chat-area" ref={chatAreaRef}>
        {messages.length === 0 ? (
          <WelcomeScreen onExampleClick={handleExampleClick} />
        ) : (
          messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} onScrollNeeded={scrollToBottom} />
          ))
        )}
      </div>

      <InputBar onSend={handleSend} disabled={isLoading} />
    </div>
  )
}

export default App
