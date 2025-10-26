/**
 * CategoryBreakdown Component
 * Displays budget breakdown by category with visual donut chart
 * Story 3.4 - Task 2: Category Breakdown Visualization
 */

'use client';

import React, { useState } from 'react';
import {
  Plane,
  Hotel,
  Compass,
  Utensils,
  Car,
  MoreHorizontal,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { formatCurrency } from '@/lib/currencyUtils';

export type BudgetCategory =
  | 'flights'
  | 'accommodation'
  | 'activities'
  | 'dining'
  | 'transportation'
  | 'misc';

export interface CategoryCost {
  category: BudgetCategory;
  amount: number;
  percentage: number;
  items?: Array<{
    name: string;
    cost: number;
  }>;
}

export interface CategoryBreakdownProps {
  categories: CategoryCost[];
  currency?: string;
  totalCost: number;
}

const CATEGORY_CONFIG: Record<
  BudgetCategory,
  {
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    bgLight: string;
  }
> = {
  flights: {
    label: 'Flights',
    icon: Plane,
    color: '#3B82F6',
    bgLight: 'bg-blue-50',
  },
  accommodation: {
    label: 'Accommodation',
    icon: Hotel,
    color: '#8B5CF6',
    bgLight: 'bg-purple-50',
  },
  activities: {
    label: 'Activities',
    icon: Compass,
    color: '#10B981',
    bgLight: 'bg-green-50',
  },
  dining: {
    label: 'Meals & Dining',
    icon: Utensils,
    color: '#F59E0B',
    bgLight: 'bg-orange-50',
  },
  transportation: {
    label: 'Transportation',
    icon: Car,
    color: '#6B7280',
    bgLight: 'bg-gray-50',
  },
  misc: {
    label: 'Miscellaneous',
    icon: MoreHorizontal,
    color: '#EC4899',
    bgLight: 'bg-pink-50',
  },
};

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({
  categories,
  currency = 'EUR',
  totalCost,
}) => {
  const [expandedCategory, setExpandedCategory] = useState<BudgetCategory | null>(null);
  const [hoveredCategory, setHoveredCategory] = useState<BudgetCategory | null>(null);

  /**
   * Generate SVG path for donut chart segment
   */
  const generateDonutPath = (
    startAngle: number,
    endAngle: number,
    innerRadius: number,
    outerRadius: number
  ): string => {
    const startAngleRad = (startAngle - 90) * (Math.PI / 180);
    const endAngleRad = (endAngle - 90) * (Math.PI / 180);

    const x1 = 100 + outerRadius * Math.cos(startAngleRad);
    const y1 = 100 + outerRadius * Math.sin(startAngleRad);
    const x2 = 100 + outerRadius * Math.cos(endAngleRad);
    const y2 = 100 + outerRadius * Math.sin(endAngleRad);
    const x3 = 100 + innerRadius * Math.cos(endAngleRad);
    const y3 = 100 + innerRadius * Math.sin(endAngleRad);
    const x4 = 100 + innerRadius * Math.cos(startAngleRad);
    const y4 = 100 + innerRadius * Math.sin(startAngleRad);

    const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0;

    return `M ${x1} ${y1} A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${x2} ${y2} L ${x3} ${y3} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${x4} ${y4} Z`;
  };

  const toggleCategory = (category: BudgetCategory) => {
    setExpandedCategory(expandedCategory === category ? null : category);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <h3 className="text-lg font-bold text-gray-900 mb-6">Category Breakdown</h3>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Donut Chart */}
        <div className="flex items-center justify-center">
          <div className="relative">
            <svg width="200" height="200" viewBox="0 0 200 200">
              {categories.map((cat, index) => {
                const previousTotal = categories
                  .slice(0, index)
                  .reduce((sum, c) => sum + c.percentage, 0);
                const startAngle = (previousTotal / 100) * 360;
                const endAngle = startAngle + (cat.percentage / 100) * 360;
                const config = CATEGORY_CONFIG[cat.category];
                const isHovered = hoveredCategory === cat.category;

                return (
                  <path
                    key={cat.category}
                    d={generateDonutPath(
                      startAngle,
                      endAngle,
                      isHovered ? 55 : 60,
                      isHovered ? 95 : 90
                    )}
                    fill={config.color}
                    className="transition-all duration-200 cursor-pointer"
                    onMouseEnter={() => setHoveredCategory(cat.category)}
                    onMouseLeave={() => setHoveredCategory(null)}
                    onClick={() => toggleCategory(cat.category)}
                  >
                    <title>
                      {config.label}: {formatCurrency(cat.amount.toString(), currency)} (
                      {cat.percentage.toFixed(1)}%)
                    </title>
                  </path>
                );
              })}
              {/* Center circle */}
              <circle cx="100" cy="100" r="60" fill="white" />
              <text
                x="100"
                y="95"
                textAnchor="middle"
                className="text-sm font-medium fill-gray-600"
              >
                Total
              </text>
              <text
                x="100"
                y="110"
                textAnchor="middle"
                className="text-lg font-bold fill-gray-900"
              >
                {formatCurrency(totalCost.toString(), currency)}
              </text>
            </svg>
          </div>
        </div>

        {/* Category List */}
        <div className="space-y-2">
          {categories.map((cat) => {
            const config = CATEGORY_CONFIG[cat.category];
            const Icon = config.icon;
            const isExpanded = expandedCategory === cat.category;
            const hasItems = cat.items && cat.items.length > 0;

            return (
              <div key={cat.category} className="border border-gray-200 rounded-lg">
                <button
                  className="w-full p-3 flex items-center justify-between hover:bg-gray-50 transition-colors rounded-lg"
                  onClick={() => hasItems && toggleCategory(cat.category)}
                  onMouseEnter={() => setHoveredCategory(cat.category)}
                  onMouseLeave={() => setHoveredCategory(null)}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`p-2 rounded ${config.bgLight}`}
                      style={{ backgroundColor: `${config.color}20` }}
                    >
                      <Icon className="w-4 h-4" style={{ color: config.color }} />
                    </div>
                    <div className="text-left">
                      <div className="text-sm font-medium text-gray-900">
                        {config.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {cat.percentage.toFixed(1)}% of total
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-gray-900">
                      {formatCurrency(cat.amount.toString(), currency)}
                    </span>
                    {hasItems &&
                      (isExpanded ? (
                        <ChevronUp className="w-4 h-4 text-gray-500" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-500" />
                      ))}
                  </div>
                </button>

                {/* Expanded Items */}
                {isExpanded && hasItems && (
                  <div className="px-3 pb-3 space-y-1">
                    {cat.items?.map((item, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded text-sm"
                      >
                        <span className="text-gray-700">{item.name}</span>
                        <span className="text-gray-900 font-medium">
                          {formatCurrency(item.cost.toString(), currency)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CategoryBreakdown;
