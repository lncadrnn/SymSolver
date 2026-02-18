import { useState, useEffect, useRef, useCallback } from 'react'

/* ── Utility: fires onDone immediately (for steps with no expression) ── */
function HiddenDone({ onDone }) {
  useEffect(() => { onDone() }, [])
  return null
}

/* ── Typewriter: types out text character by character ── */
function TypewriterText({ text, speed = 20, onDone }) {
  const [displayed, setDisplayed] = useState('')
  const indexRef = useRef(0)

  useEffect(() => {
    if (!text) {
      if (onDone) onDone()
      return
    }
    setDisplayed('')
    indexRef.current = 0

    const interval = setInterval(() => {
      indexRef.current++
      if (indexRef.current <= text.length) {
        setDisplayed(text.slice(0, indexRef.current))
      } else {
        clearInterval(interval)
        if (onDone) onDone()
      }
    }, speed)

    return () => clearInterval(interval)
  }, [text, speed])

  return (
    <span>
      {displayed}
      {text && displayed.length < text.length && <span className="typewriter-cursor" />}
    </span>
  )
}

/* ── Explanation Panel (toggleable) ── */
function ExplanationPanel({ explanation, visible }) {
  if (!visible || !explanation) return null
  return (
    <div className="explanation-panel">
      <div className="explanation-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </div>
      <p>{explanation}</p>
    </div>
  )
}

/* ── Single Step Card ── */
function StepCard({ step, index, animate, onDone, onScrollNeeded }) {
  const [phase, setPhase] = useState(animate ? 'typing-desc' : 'done')
  // phases: typing-desc -> typing-expr -> done
  const [showExplanation, setShowExplanation] = useState(true)
  const cardRef = useRef(null)

  const scroll = useCallback(() => {
    if (onScrollNeeded) {
      setTimeout(onScrollNeeded, 30)
    }
  }, [onScrollNeeded])

  useEffect(() => { scroll() }, [phase])

  const lines = step.expression
    ? step.expression.split('\n').filter((l) => l.trim())
    : []

  const handleDescDone = () => {
    if (lines.length > 0) {
      setPhase('typing-expr')
    } else {
      setPhase('done')
      if (onDone) onDone()
    }
  }

  const handleExprDone = () => {
    setPhase('done')
    if (onDone) onDone()
  }

  const descReady = phase !== 'typing-desc' || !animate
  const exprReady = phase === 'done' || !animate

  return (
    <div className="step-card" ref={cardRef}>
      {/* Step description row */}
      <div className="step-header">
        <div className="step-number">{index + 1}</div>
        <div className="step-description">
          {animate && phase === 'typing-desc' ? (
            <TypewriterText text={step.description} speed={12} onDone={handleDescDone} />
          ) : (
            step.description
          )}
        </div>
      </div>

      {/* Equation display */}
      {(descReady) && lines.length > 0 && (
        <div className="step-equation">
          {lines.map((line, i) => (
            <div className="equation-line" key={i}>
              {animate && phase === 'typing-expr' ? (
                <TypewriterText
                  text={line}
                  speed={16}
                  onDone={i === lines.length - 1 ? handleExprDone : undefined}
                />
              ) : exprReady ? (
                line
              ) : null}
            </div>
          ))}
        </div>
      )}

      {/* Explanation shown by default, with toggle to hide */}
      {(exprReady) && step.explanation && (
        <div className="step-footer">
          <button
            className={`explain-btn ${showExplanation ? 'active' : ''}`}
            onClick={() => setShowExplanation((v) => !v)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            {showExplanation ? 'Hide Explanation' : 'Show Explanation'}
          </button>
          <ExplanationPanel explanation={step.explanation} visible={showExplanation} />
        </div>
      )}

      {descReady && lines.length === 0 && animate && phase !== 'done' && (
        <HiddenDone onDone={() => { setPhase('done'); if (onDone) onDone() }} />
      )}
    </div>
  )
}

/* ── Final Answer Card ── */
function FinalAnswer({ answer, animate, onScrollNeeded }) {
  useEffect(() => {
    if (onScrollNeeded) setTimeout(onScrollNeeded, 30)
  }, [])

  return (
    <div className="final-answer">
      <div className="final-answer-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <div>
        <div className="final-answer-label">Solution</div>
        <div className="final-answer-text">
          {animate ? <TypewriterText text={answer} speed={22} /> : answer}
        </div>
      </div>
    </div>
  )
}

/* ── Verification Section ── */
function VerificationSection({ verificationSteps, onScrollNeeded }) {
  const [expanded, setExpanded] = useState(false)
  const [verifyStep, setVerifyStep] = useState(0)
  const [verifyAllDone, setVerifyAllDone] = useState(false)
  const verifyStepRef = useRef(0)
  const verifyCount = verificationSteps?.length || 0

  const handleVerifyStepDone = useCallback(() => {
    if (verifyStepRef.current < verifyCount - 1) {
      setTimeout(() => {
        verifyStepRef.current++
        setVerifyStep(verifyStepRef.current)
      }, 300)
    } else {
      setTimeout(() => {
        setVerifyAllDone(true)
      }, 300)
    }
  }, [verifyCount])

  // Reset animation when toggling open
  const handleToggle = () => {
    if (!expanded) {
      verifyStepRef.current = 0
      setVerifyStep(0)
      setVerifyAllDone(false)
    }
    setExpanded((v) => !v)
  }

  if (!verificationSteps || verificationSteps.length === 0) return null

  return (
    <div className="verification-section">
      <button
        className={`verify-btn ${expanded ? 'active' : ''}`}
        onClick={handleToggle}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <path d="M9 12l2 2 4-4" />
          <circle cx="12" cy="12" r="10" />
        </svg>
        {expanded ? 'Hide Verification' : 'Check / Verify Your Answer'}
        <svg className={`verify-chevron ${expanded ? 'open' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {expanded && (
        <div className="verification-steps">
          {verificationSteps.map((step, i) => {
            if (!verifyAllDone && i > verifyStep) return null
            return (
              <StepCard
                key={`verify-${i}`}
                step={step}
                index={i}
                animate={!verifyAllDone && i === verifyStep}
                onDone={handleVerifyStepDone}
                onScrollNeeded={onScrollNeeded}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

/* ── Main ChatMessage Component ── */
function ChatMessage({ message, onScrollNeeded }) {
  const { role, content, loading, steps, finalAnswer, verificationSteps, error, animating } = message
  const [currentStep, setCurrentStep] = useState(0)
  const [showAnswer, setShowAnswer] = useState(!animating)
  const [allDone, setAllDone] = useState(!animating)
  const currentStepRef = useRef(0)
  const stepsCount = steps?.length || 0

  // Safety fallback: if animation gets stuck, force show answer after a generous timeout
  useEffect(() => {
    if (animating && stepsCount > 0 && !allDone) {
      const timeout = setTimeout(() => {
        setShowAnswer(true)
        setAllDone(true)
      }, stepsCount * 5000) // 5 seconds per step max
      return () => clearTimeout(timeout)
    }
  }, [animating, stepsCount, allDone])

  const handleStepDone = useCallback(() => {
    if (currentStepRef.current < stepsCount - 1) {
      setTimeout(() => {
        currentStepRef.current++
        setCurrentStep(currentStepRef.current)
      }, 300)
    } else {
      setTimeout(() => {
        setShowAnswer(true)
        setAllDone(true)
      }, 300)
    }
  }, [stepsCount])

  if (role === 'user') {
    return (
      <div className="message user">
        <div className="message-avatar">U</div>
        <div className="message-content">{content}</div>
      </div>
    )
  }

  return (
    <div className="message bot">
      <div className="message-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <div className="message-content">
        {loading && (
          <div className="solving-indicator">
            <div className="solving-spinner" />
            Solving equation...
          </div>
        )}

        {error && <div className="error-msg">{error}</div>}

        {!loading && !error && steps && steps.length > 0 && (
          <div className="solver-response">
            {steps.map((step, i) => {
              if (animating && !allDone && i > currentStep) return null
              return (
                <StepCard
                  key={i}
                  step={step}
                  index={i}
                  animate={animating && !allDone && i === currentStep}
                  onDone={handleStepDone}
                  onScrollNeeded={onScrollNeeded}
                />
              )
            })}
            {(showAnswer || (!animating && finalAnswer)) && finalAnswer && (
              <>
              <FinalAnswer
                answer={finalAnswer}
                animate={animating && showAnswer}
                onScrollNeeded={onScrollNeeded}
              />
              <VerificationSection
                verificationSteps={verificationSteps}
                onScrollNeeded={onScrollNeeded}
              />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ChatMessage
