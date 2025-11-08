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

  it('does not show search input when searchable is false', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        searchable={false}
      />
    )

    expect(screen.queryByPlaceholderText('Search cuisines...')).not.toBeInTheDocument()
  })

  it('shows search input when searchable is true', () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        searchable={true}
      />
    )

    expect(screen.getByPlaceholderText('Search cuisines...')).toBeInTheDocument()
  })

  it('filters options based on search query', async () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        searchable={true}
      />
    )

    const searchInput = screen.getByPlaceholderText('Search cuisines...')
    await userEvent.type(searchInput, 'Option 1')

    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.queryByText('Option 2')).not.toBeInTheDocument()
    expect(screen.queryByText('Option 3')).not.toBeInTheDocument()
  })

  it('shows filtered count when searching', async () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        searchable={true}
      />
    )

    const searchInput = screen.getByPlaceholderText('Search cuisines...')
    await userEvent.type(searchInput, 'Option 1')

    expect(screen.getByText('Showing 1 of 3 options')).toBeInTheDocument()
  })

  it('filters are case-insensitive', async () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        searchable={true}
      />
    )

    const searchInput = screen.getByPlaceholderText('Search cuisines...')
    await userEvent.type(searchInput, 'option 1')

    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.queryByText('Option 2')).not.toBeInTheDocument()
  })

  it('clears filter when search is cleared', async () => {
    render(
      <MultiSelect
        label="Test Options"
        options={mockOptions}
        value={[]}
        onChange={vi.fn()}
        searchable={true}
      />
    )

    const searchInput = screen.getByPlaceholderText('Search cuisines...')
    await userEvent.type(searchInput, 'Option 1')
    await userEvent.clear(searchInput)

    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.getByText('Option 2')).toBeInTheDocument()
    expect(screen.getByText('Option 3')).toBeInTheDocument()
  })
})
