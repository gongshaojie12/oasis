import { nanoid } from 'nanoid'

export function generateId(size = 21): string {
  return nanoid(size)
}

export function generateSmsCode(): string {
  return Math.floor(100000 + Math.random() * 900000).toString()
}
