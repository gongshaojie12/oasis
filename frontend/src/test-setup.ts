// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import '@testing-library/jest-dom/vitest'

// Reset localStorage between tests so token/lang state never leaks across cases.
beforeEach(() => {
  localStorage.clear()
})
