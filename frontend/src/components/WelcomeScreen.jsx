const EXAMPLES = [
  '2x + 3 = 7',
  '5x - 2 = 3x + 8',
  '3(x + 4) = 2x - 1',
  '4x + 7 = 2(x + 5)',
]

function WelcomeScreen({ onExampleClick }) {
  return (
    <div className="welcome">
      <div className="welcome-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
      </div>
      <h2>Solve Linear Equations Step by Step</h2>
      <p>
        Enter any linear equation and watch as DualSolver breaks down the
        solution into clear, detailed steps — just like a tutor would.
      </p>
      <div className="examples">
        {EXAMPLES.map((eq) => (
          <button key={eq} className="example-btn" onClick={() => onExampleClick(eq)}>
            {eq}
          </button>
        ))}
      </div>
    </div>
  )
}

export default WelcomeScreen
