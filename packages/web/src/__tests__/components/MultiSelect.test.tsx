import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect } from 'vitest'
import MultiSelect from '../../components/ui/MultiSelect'

const mockOptions = [
  { id: 'option1', label: 'Option 1', icon: '🌟' },
  { id: 'option2', label: 'Option 2', icon: '⭐' },
  { id: 'option3', label: 'Option 3', icon: '✨' },
]

describe('MultiSelect', () => {
  it('renders all options', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
      />
    )

    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.getByText('Option 2')).toBeInTheDocument()
    expect(screen.getByText('Option 3')).toBeInTheDocument()
  })

  it('displays selected count', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={['option1', 'option2']}
        onChange={vi.fn()}
      />
    )

    expect(screen.getByText('2 selected')).toBeInTheDocument()
  })

  it('calls onChange when option is clicked', async () => {
    const handleChange = vi.fn()

    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={handleChange}
      />
    )

    const option1Button = screen.getByRole('button', { name: /option 1/i })
    await userEvent.click(option1Button)

    expect(handleChange).toHaveBeenCalledWith(['option1'])
  })

  it('toggles selection correctly', async () => {
    const handleChange = vi.fn()

    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={['option1']}
        onChange={handleChange}
      />
    )

    const option1Button = screen.getByRole('button', { name: /option 1/i })
    await userEvent.click(option1Button)

    expect(handleChange).toHaveBeenCalledWith([])
  })

  it('adds multiple selections', async () => {
    let selectedValues: string[] = []
    const handleChange = vi.fn((values) => {
      selectedValues = values
    })

    const { rerender } = render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={selectedValues}
        onChange={handleChange}
      />
    )

    const option1Button = screen.getByRole('button', { name: /option 1/i })
    await userEvent.click(option1Button)

    rerender(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={['option1']}
        onChange={handleChange}
      />
    )

    const option2Button = screen.getByRole('button', { name: /option 2/i })
    await userEvent.click(option2Button)

    expect(handleChange).toHaveBeenLastCalledWith(['option1', 'option2'])
  })

  it('displays error message when provided', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        error="This field is required"
      />
    )

    expect(screen.getByRole('alert')).toHaveTextContent('This field is required')
  })

  it('renders option icons', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
      />
    )

    expect(screen.getByText('🌟')).toBeInTheDocument()
    expect(screen.getByText('⭐')).toBeInTheDocument()
    expect(screen.getByText('✨')).toBeInTheDocument()
  })

  it('shows selection indicator on selected options', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={['option1']}
        onChange={vi.fn()}
      />
    )

    const option1Button = screen.getByRole('button', { name: /option 1/i })
    expect(option1Button).toHaveAttribute('aria-pressed', 'true')
  })

  it('renders with custom description', () => {
    render(
      <MultiSelect
        label="Test Options"
        description="Select your preferences"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
      />
    )

    expect(screen.getByText('Select your preferences')).toBeInTheDocument()
  })
})
