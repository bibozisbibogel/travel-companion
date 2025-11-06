/**
 * Geoapify Routing API Client
 * https://apidocs.geoapify.com/docs/routing/
 */

export interface GeoapifyWaypoint {
  lat: number;
  lon: number;
}

export interface GeoapifyRouteResponse {
  type: string;
  features: Array<{
    type: string;
    geometry: {
      type: string;
      coordinates: number[][];
    };
    properties: {
      mode: string;
      waypoints: Array<{
        location: number[];
        original_index: number;
      }>;
      units: string;
      distance: number;
      distance_units: string;
      time: number;
      legs: Array<{
        distance: number;
        time: number;
        steps: Array<{
          distance: {
            value: number;
            text: string;
          };
          duration: {
            value: number;
            text: string;
          };
          instruction: {
            text: string;
          };
          type: number;
          from_index: number;
          to_index: number;
        }>;
      }>;
    };
  }>;
}

export interface RoutePolyline {
  coordinates: Array<{ lat: number; lng: number }>;
  distance: number;
  duration: number;
  legs: Array<{
    distance: number;
    duration: number;
  }>;
}

/**
 * Fetch route from Geoapify Routing API
 * @param waypoints - Array of waypoints with lat/lon coordinates
 * @param mode - Travel mode (drive, walk, truck, bicycle, approximated_transit)
 * @returns Route polyline with distance and duration information
 */
export async function fetchGeoapifyRoute(
  waypoints: GeoapifyWaypoint[],
  mode: 'drive' | 'walk' | 'truck' | 'bicycle' | 'approximated_transit' = 'walk'
): Promise<RoutePolyline | null> {
  const apiKey = process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY;

  if (!apiKey) {
    console.error('⚠️ Geoapify API key not found. Please add NEXT_PUBLIC_GEOAPIFY_API_KEY to your .env file');
    console.error('Get your API key from: https://www.geoapify.com/');
    return null;
  }

  if (waypoints.length < 2) {
    console.error('At least 2 waypoints are required for routing');
    return null;
  }

  try {
    // Build waypoints parameter for API
    const waypointsParam = waypoints.map(wp => `${wp.lat},${wp.lon}`).join('|');

    // API documentation: https://apidocs.geoapify.com/docs/routing/#routing
    const url = `https://api.geoapify.com/v1/routing?waypoints=${waypointsParam}&mode=${mode}&apiKey=${apiKey}`;

    console.log(`🌐 Geoapify API call with ${waypoints.length} waypoints:`);
    waypoints.forEach((wp, idx) => {
      console.log(`  ${idx}: [${wp.lat}, ${wp.lon}]`);
    });
    console.log(`🌐 Full URL: ${url.replace(apiKey, 'REDACTED')}`);

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Geoapify API error: ${response.status} ${response.statusText}`);
    }

    const data: GeoapifyRouteResponse = await response.json();

    if (!data.features || data.features.length === 0) {
      console.error('No route found');
      return null;
    }

    const feature = data.features[0];
    const properties = feature.properties;
    const geometry = feature.geometry;

    console.log('✅ Raw Geoapify response:');
    console.log('  - Geometry type:', geometry.type);
    console.log('  - Coordinate segments:', geometry.coordinates.length);
    console.log('  - Legs (waypoint-to-waypoint):', properties.legs.length);
    console.log('  - Waypoints returned:', properties.waypoints.length);
    console.log('  - Total distance:', properties.distance, 'meters');

    // Log each leg
    properties.legs.forEach((leg, idx) => {
      console.log(`  📏 Leg ${idx}: ${leg.distance}m, ${leg.time}s`);
    });

    // Flatten coordinates if needed (handle both LineString and MultiLineString)
    let flatCoordinates: number[][] = [];

    // Check if this is a MultiLineString (array of LineStrings)
    if (Array.isArray(geometry.coordinates[0]) && Array.isArray(geometry.coordinates[0][0])) {
      console.log('  ℹ️ MultiLineString detected with', geometry.coordinates.length, 'segments');
      // Concatenate all segments into one array
      geometry.coordinates.forEach((segment: number[][], idx: number) => {
        console.log(`    Segment ${idx}: ${segment.length} coordinates`);
        flatCoordinates.push(...segment);
      });
      console.log(`  ✅ Flattened to ${flatCoordinates.length} total coordinates`);
    } else {
      // It's already a simple LineString
      flatCoordinates = geometry.coordinates as number[][];
    }

    // Convert coordinates from [lon, lat] to {lat, lng} format for Google Maps
    const coordinates = flatCoordinates
      .map(coord => {
        if (!Array.isArray(coord) || coord.length < 2) {
          console.warn('Invalid coordinate format:', coord);
          return null;
        }

        const lat = Number(coord[1]);
        const lng = Number(coord[0]);

        if (!isFinite(lat) || !isFinite(lng)) {
          console.warn('Non-finite coordinates:', { lat, lng, original: coord });
          return null;
        }

        return { lat, lng };
      })
      .filter((coord): coord is { lat: number; lng: number } => coord !== null);

    console.log(`  ✅ Converted ${coordinates.length} coordinates for Google Maps`);
    console.log(`  🎯 Route ready: ${properties.legs.length} legs covering ${(properties.distance / 1000).toFixed(1)}km`);

    if (coordinates.length === 0) {
      console.error('No valid coordinates after conversion');
      return null;
    }

    return {
      coordinates,
      distance: properties.distance,
      duration: properties.time,
      legs: properties.legs.map(leg => ({
        distance: leg.distance,
        duration: leg.time
      }))
    };
  } catch (error) {
    console.error('Error fetching Geoapify route:', error);
    return null;
  }
}

/**
 * Fetch routes for a day's activities
 * @param locations - Array of locations (activities + accommodation)
 * @param mode - Travel mode
 * @returns Route polyline or null if routing fails
 */
export async function fetchDayRoute(
  locations: Array<{ latitude: number; longitude: number }>,
  mode: 'drive' | 'walk' | 'truck' | 'bicycle' | 'approximated_transit' = 'walk'
): Promise<RoutePolyline | null> {
  if (locations.length < 2) {
    return null;
  }

  const waypoints: GeoapifyWaypoint[] = locations.map(loc => ({
    lat: loc.latitude,
    lon: loc.longitude
  }));

  return fetchGeoapifyRoute(waypoints, mode);
}
