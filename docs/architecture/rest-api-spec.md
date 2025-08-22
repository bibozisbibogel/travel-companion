# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: Travel Companion API
  version: 1.0.0
  description: Multi-agent travel planning API with LangGraph orchestration
servers:
  - url: http://localhost:8000/api/v1
    description: Development server
  - url: https://api.travelcompanion.com/api/v1
    description: Production server

paths:
  /trips/plan:
    post:
      summary: Create new travel plan
      description: Initiates multi-agent workflow to create comprehensive travel itinerary
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [destination, start_date, end_date, budget]
              properties:
                destination:
                  type: string
                  example: "Tokyo, Japan"
                start_date:
                  type: string
                  format: date
                  example: "2024-06-01"
                end_date:
                  type: string
                  format: date
                  example: "2024-06-07"
                budget:
                  type: number
                  format: decimal
                  example: 3000.00
                travelers:
                  type: integer
                  default: 1
                  example: 2
                preferences:
                  type: object
                  properties:
                    accommodation_type:
                      type: string
                      enum: [hotel, hostel, airbnb, luxury]
                    activity_interests:
                      type: array
                      items:
                        type: string
                      example: ["cultural", "adventure", "food"]
      responses:
        '201':
          description: Trip planning initiated successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  trip_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    example: "planning"
                  estimated_completion:
                    type: string
                    format: date-time
        '400':
          description: Invalid request parameters
        '429':
          description: Rate limit exceeded

  /trips/{trip_id}:
    get:
      summary: Get trip details
      parameters:
        - name: trip_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Complete trip itinerary
          content:
            application/json:
              schema:
                type: object
                properties:
                  trip_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    enum: [planning, completed, error]
                  itinerary:
                    type: object
                    properties:
                      flights:
                        type: array
                        items:
                          $ref: '#/components/schemas/FlightOption'
                      hotels:
                        type: array
                        items:
                          $ref: '#/components/schemas/HotelOption'
                      activities:
                        type: array
                        items:
                          $ref: '#/components/schemas/ActivityOption'

components:
  schemas:
    FlightOption:
      type: object
      properties:
        flight_id:
          type: string
          format: uuid
        airline:
          type: string
        price:
          type: number
          format: decimal
        departure_time:
          type: string
          format: date-time
        arrival_time:
          type: string
          format: date-time
        duration:
          type: integer
          description: Duration in minutes
    
    HotelOption:
      type: object
      properties:
        hotel_id:
          type: string
          format: uuid
        name:
          type: string
        price_per_night:
          type: number
          format: decimal
        location:
          type: object
          properties:
            latitude:
              type: number
            longitude:
              type: number
        rating:
          type: number
          format: float
          minimum: 1
          maximum: 5
    
    ActivityOption:
      type: object
      properties:
        activity_id:
          type: string
          format: uuid
        name:
          type: string
        description:
          type: string
        price:
          type: number
          format: decimal
        duration:
          type: integer
          description: Duration in minutes
        category:
          type: string
          enum: [cultural, adventure, food, entertainment, nature]
```
