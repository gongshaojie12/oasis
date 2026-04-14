import { describe, it, expect } from 'vitest'
import { encrypt, decrypt } from '../../server/utils/crypto'
import { randomBytes } from 'crypto'

describe('crypto', () => {
  const testKey = randomBytes(32).toString('hex')

  it('encrypts and decrypts a string', () => {
    const original = 'sk-test-api-key-12345'
    const encrypted = encrypt(original, testKey)
    expect(encrypted).not.toBe(original)
    expect(encrypted).toContain(':')
    const decrypted = decrypt(encrypted, testKey)
    expect(decrypted).toBe(original)
  })

  it('produces different ciphertext each time (random IV)', () => {
    const original = 'same-key'
    const a = encrypt(original, testKey)
    const b = encrypt(original, testKey)
    expect(a).not.toBe(b)
    expect(decrypt(a, testKey)).toBe(original)
    expect(decrypt(b, testKey)).toBe(original)
  })
})
