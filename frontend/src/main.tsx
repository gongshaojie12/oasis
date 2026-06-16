// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './lib/i18n'
import './styles/tokens.css'
import { applyTheme, getInitialTheme } from '@/lib/theme'
import { App } from './App'

// Apply theme synchronously before the first render so the user never
// sees a flash of the wrong theme (FOUC) when reopening the app.
applyTheme(getInitialTheme())

const root = document.getElementById('root')
if (!root) throw new Error('#root not found in index.html')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
