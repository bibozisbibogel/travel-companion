import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { RouteLayer } from '../RouteLayer';
import type { RoutePolyline } from '@/lib/geoapifyRouting';

// Mock the Polyline component from @react-google-maps/api
vi.mock('@react-google-maps/api', () => ({
  Polyline: ({ path, options }: any) => (
    <div data-testid="polyline" data-path={JSON.stringify(path)} data-options={JSON.stringify(options)} />
  )
}));

describe('RouteLayer', () => {
  const mockRoute: RoutePolyline = {
    coordinates: [
      { lat: 40.7128, lng: -74.0060 },
      { lat: 40.7589, lng: -73.9851 }
    ],
    distance: 1000,
    duration: 720,
    legs: [{
      distance: 1000,
      duration: 720
    }]
  };

  it('should render nothing when routes array is empty', () => {
    const { container } = render(<RouteLayer routes={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('should render polyline for single route', () => {
    const { getAllByTestId } = render(<RouteLayer routes={[mockRoute]} />);
    const polylines = getAllByTestId('polyline');
    expect(polylines).toHaveLength(1);
  });

  it('should render multiple polylines for multiple routes', () => {
    const { getAllByTestId } = render(<RouteLayer routes={[mockRoute, mockRoute]} />);
    const polylines = getAllByTestId('polyline');
    expect(polylines).toHaveLength(2);
  });

  it('should pass correct coordinates to Polyline', () => {
    const { getByTestId } = render(<RouteLayer routes={[mockRoute]} />);
    const polyline = getByTestId('polyline');
    const path = JSON.parse(polyline.getAttribute('data-path') || '[]');
    expect(path).toHaveLength(2);
    expect(path[0]).toEqual({ lat: 40.7128, lng: -74.0060 });
  });

  it('should apply custom color', () => {
    const { getByTestId } = render(
      <RouteLayer routes={[mockRoute]} color="#FF0000" />
    );
    const polyline = getByTestId('polyline');
    const options = JSON.parse(polyline.getAttribute('data-options') || '{}');
    expect(options.strokeColor).toBe('#FF0000');
  });

  it('should apply custom opacity', () => {
    const { getByTestId } = render(
      <RouteLayer routes={[mockRoute]} opacity={0.5} />
    );
    const polyline = getByTestId('polyline');
    const options = JSON.parse(polyline.getAttribute('data-options') || '{}');
    expect(options.strokeOpacity).toBe(0.5);
  });

  it('should apply custom weight', () => {
    const { getByTestId } = render(
      <RouteLayer routes={[mockRoute]} weight={6} />
    );
    const polyline = getByTestId('polyline');
    const options = JSON.parse(polyline.getAttribute('data-options') || '{}');
    expect(options.strokeWeight).toBe(6);
  });

  it('should set geodesic to true', () => {
    const { getByTestId } = render(<RouteLayer routes={[mockRoute]} />);
    const polyline = getByTestId('polyline');
    const options = JSON.parse(polyline.getAttribute('data-options') || '{}');
    expect(options.geodesic).toBe(true);
  });

  it('should set clickable to false', () => {
    const { getByTestId } = render(<RouteLayer routes={[mockRoute]} />);
    const polyline = getByTestId('polyline');
    const options = JSON.parse(polyline.getAttribute('data-options') || '{}');
    expect(options.clickable).toBe(false);
  });
});
