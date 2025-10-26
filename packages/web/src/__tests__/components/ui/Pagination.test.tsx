/**
 * Pagination Component Tests
 * Story 3.5: User Trip List Dashboard
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Pagination } from '@/components/ui/Pagination';
import { IPaginationMeta } from '@/lib/types';

const mockPagination: IPaginationMeta = {
  page: 2,
  per_page: 20,
  total_items: 100,
  total_pages: 5,
  has_next: true,
  has_prev: true,
};

describe('Pagination', () => {
  it('renders pagination info correctly', () => {
    const onPageChange = vi.fn();
    render(<Pagination pagination={mockPagination} onPageChange={onPageChange} />);

    expect(screen.getByText(/Showing/)).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument(); // Start item
    expect(screen.getByText('40')).toBeInTheDocument(); // End item
    expect(screen.getByText('100')).toBeInTheDocument(); // Total items
  });

  it('displays current page as active', () => {
    const onPageChange = vi.fn();
    render(<Pagination pagination={mockPagination} onPageChange={onPageChange} />);

    const currentPageButton = screen.getByRole('button', { name: 'Page 2' });
    expect(currentPageButton).toHaveClass('bg-blue-600');
  });

  it('calls onPageChange when clicking page number', () => {
    const onPageChange = vi.fn();
    render(<Pagination pagination={mockPagination} onPageChange={onPageChange} />);

    const page3Button = screen.getByRole('button', { name: 'Page 3' });
    fireEvent.click(page3Button);

    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it('calls onPageChange when clicking next button', () => {
    const onPageChange = vi.fn();
    render(<Pagination pagination={mockPagination} onPageChange={onPageChange} />);

    const nextButton = screen.getByRole('button', { name: 'Next page' });
    fireEvent.click(nextButton);

    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it('calls onPageChange when clicking previous button', () => {
    const onPageChange = vi.fn();
    render(<Pagination pagination={mockPagination} onPageChange={onPageChange} />);

    const prevButton = screen.getByRole('button', { name: 'Previous page' });
    fireEvent.click(prevButton);

    expect(onPageChange).toHaveBeenCalledWith(1);
  });

  it('disables previous button on first page', () => {
    const onPageChange = vi.fn();
    const firstPagePagination = { ...mockPagination, page: 1, has_prev: false };
    render(<Pagination pagination={firstPagePagination} onPageChange={onPageChange} />);

    const prevButton = screen.getByRole('button', { name: 'Previous page' });
    expect(prevButton).toBeDisabled();
  });

  it('disables next button on last page', () => {
    const onPageChange = vi.fn();
    const lastPagePagination = { ...mockPagination, page: 5, has_next: false };
    render(<Pagination pagination={lastPagePagination} onPageChange={onPageChange} />);

    const nextButton = screen.getByRole('button', { name: 'Next page' });
    expect(nextButton).toBeDisabled();
  });

  it('displays ellipsis for large page ranges', () => {
    const onPageChange = vi.fn();
    const largePagination = { ...mockPagination, total_pages: 20, page: 10 };
    render(<Pagination pagination={largePagination} onPageChange={onPageChange} />);

    const ellipses = screen.getAllByText('...');
    expect(ellipses.length).toBeGreaterThan(0);
  });

  it('displays all pages when total is less than max', () => {
    const onPageChange = vi.fn();
    const smallPagination = { ...mockPagination, total_pages: 5 };
    render(<Pagination pagination={smallPagination} onPageChange={onPageChange} />);

    for (let i = 1; i <= 5; i++) {
      expect(screen.getByRole('button', { name: `Page ${i}` })).toBeInTheDocument();
    }
  });

  it('calculates correct item range for last page with partial results', () => {
    const onPageChange = vi.fn();
    const lastPagePagination = {
      page: 5,
      per_page: 20,
      total_items: 85,
      total_pages: 5,
      has_next: false,
      has_prev: true,
    };
    const { container } = render(<Pagination pagination={lastPagePagination} onPageChange={onPageChange} />);

    // Check that the pagination shows correct range (81-85 of 85)
    const paginationText = container.textContent;
    expect(paginationText).toContain('Showing');
    expect(paginationText).toContain('81');
    expect(paginationText).toContain('85');
    expect(paginationText).toContain('results');
  });
});
