/**
 * EmptyState Component
 * Displays a message when no items are available with optional CTA
 * Story 3.5: User Trip List Dashboard
 */

'use client';

import React from 'react';
import Link from 'next/link';
import { Plus } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message: string;
  ctaText?: string;
  ctaHref?: string;
  icon?: React.ReactNode;
}

export function EmptyState({
  title = 'No items found',
  message,
  ctaText,
  ctaHref,
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      {icon && <div className="mb-4 text-gray-400">{icon}</div>}
      <h3 className="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600 mb-6 max-w-md">{message}</p>
      {ctaText && ctaHref && (
        <Link
          href={ctaHref}
          className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          {ctaText}
        </Link>
      )}
    </div>
  );
}
