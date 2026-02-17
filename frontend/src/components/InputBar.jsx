import { useState } from 'react'

function InputBar({ onSend, disabled }) {
  const [value, setValue] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (value.trim() && !disabled) {
      onSend(value)
      setValue('')
    }
  }

  return (
    <div className="input-area">
      <form className="input-container" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Enter a linear equation, e.g. 2x + 3 = 7"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          autoFocus
        />
        <button type="submit" className="send-btn" disabled={disabled || !value.trim()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </form>
      <div className="input-hint">
        Supports equations like: 2x + 3 = 7 &nbsp;|&nbsp; 3(x - 1) = 2x + 5 &nbsp;|&nbsp; x/2 + 1 = 4
      </div>
    </div>
  )
}

export default InputBar
