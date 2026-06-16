// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './lib/i18n'
import './styles/tokens.css'
import { App } from './App'

const root = document.getElementById('root')
if (!root) throw new Error('#root not found in index.html')

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
