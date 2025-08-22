# External APIs

## Amadeus Travel API
- **Purpose:** Comprehensive flight search and booking data
- **Documentation:** https://developers.amadeus.com/
- **Base URL(s):** https://api.amadeus.com/v2/
- **Authentication:** OAuth 2.0 with client credentials
- **Rate Limits:** 10 requests/second, 1000 requests/month (sandbox)

**Key Endpoints Used:**
- `GET /shopping/flight-offers` - Flight search with flexible parameters
- `GET /shopping/flight-destinations` - Destination discovery
- `POST /booking/flight-orders` - Flight booking creation

**Integration Notes:** Primary flight data source, requires careful rate limit management and caching strategy

## Booking.com API
- **Purpose:** Hotel and accommodation search with detailed property information
- **Documentation:** https://developers.booking.com/api/
- **Base URL(s):** https://distribution-xml.booking.com/
- **Authentication:** XML API with credentials
- **Rate Limits:** 100 requests/minute per property type

**Key Endpoints Used:**
- `POST /json/bookings.getHotelAvailabilityV2` - Hotel availability search
- `POST /json/bookings.getHotelDescriptionPhotosV2` - Hotel details and images

**Integration Notes:** XML-based API requiring custom parsing, extensive property data available

## TripAdvisor Content API
- **Purpose:** Activity, attraction, and restaurant data with reviews
- **Documentation:** https://developer-tripadvisor.com/
- **Base URL(s):** https://api.content.tripadvisor.com/api/v1/
- **Authentication:** API Key authentication
- **Rate Limits:** 500 requests/day (free tier)

**Key Endpoints Used:**  
- `GET /location/search` - Location-based activity search
- `GET /location/{locationId}/details` - Detailed activity information

**Integration Notes:** Rich content data but limited rate limits, requires strategic caching

## OpenWeatherMap API
- **Purpose:** Weather forecasting and historical weather data
- **Documentation:** https://openweathermap.org/api
- **Base URL(s):** https://api.openweathermap.org/data/2.5/
- **Authentication:** API Key authentication
- **Rate Limits:** 60 calls/minute, 1M calls/month (free)

**Key Endpoints Used:**
- `GET /forecast` - 5-day weather forecast
- `GET /onecall` - Comprehensive weather data with alerts

**Integration Notes:** Reliable weather data with good free tier limits, essential for activity planning

## Yelp Fusion API
- **Purpose:** Restaurant and business search with reviews and ratings
- **Documentation:** https://www.yelp.com/developers/documentation/v3
- **Base URL(s):** https://api.yelp.com/v3/
- **Authentication:** Bearer token authentication
- **Rate Limits:** 5000 API calls per day

**Key Endpoints Used:**
- `GET /businesses/search` - Restaurant search by location and cuisine
- `GET /businesses/{id}` - Detailed restaurant information

**Integration Notes:** Excellent restaurant data for US/international locations, good rate limits
