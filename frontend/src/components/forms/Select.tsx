// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import type { ChangeEvent, ReactNode } from 'react'

interface Option {
  value: string
  label: ReactNode
}

interface Props {
  value: string
  options: Option[]
  onChange: (value: string) => void
  disabled?: boolean
  ariaLabel?: string
}

export function Select({ value, options, onChange, disabled, ariaLabel }: Props) {
  return (
    <select
      className="wx-input"
      value={value}
      disabled={disabled}
      aria-label={ariaLabel}
      onChange={(e: ChangeEvent<HTMLSelectElement>) =>
        onChange(e.target.value)
      }
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label as string}
        </option>
      ))}
    </select>
  )
}
