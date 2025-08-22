# Source Tree

```
travel-companion/
├── packages/
│   ├── api/                           # FastAPI Backend Service
│   │   ├── src/
│   │   │   ├── travel_companion/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py           # FastAPI app entry point
│   │   │   │   ├── core/
│   │   │   │   │   ├── config.py     # Settings with Pydantic
│   │   │   │   │   ├── database.py   # Supabase connection
│   │   │   │   │   ├── redis.py      # Redis client setup
│   │   │   │   │   └── security.py   # JWT and auth utilities
│   │   │   │   ├── api/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── deps.py       # FastAPI dependencies
│   │   │   │   │   └── v1/
│   │   │   │   │       ├── __init__.py
│   │   │   │   │       ├── trips.py  # Trip planning endpoints
│   │   │   │   │       ├── users.py  # User management
│   │   │   │   │       └── health.py # Health checks
│   │   │   │   ├── agents/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py       # Base agent class
│   │   │   │   │   ├── flight_agent.py
│   │   │   │   │   ├── hotel_agent.py
│   │   │   │   │   ├── activity_agent.py
│   │   │   │   │   ├── weather_agent.py
│   │   │   │   │   ├── food_agent.py
│   │   │   │   │   └── itinerary_agent.py
│   │   │   │   ├── workflows/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── orchestrator.py # LangGraph workflow
│   │   │   │   │   └── nodes.py      # Individual workflow nodes
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py       # Base Pydantic models
│   │   │   │   │   ├── user.py       # User data models
│   │   │   │   │   ├── trip.py       # Trip data models
│   │   │   │   │   └── external.py   # External API models
│   │   │   │   ├── services/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── external_apis/ # External API integrations
│   │   │   │   │   │   ├── amadeus.py
│   │   │   │   │   │   ├── booking.py
│   │   │   │   │   │   └── tripadvisor.py
│   │   │   │   │   ├── cache.py      # Redis caching layer
│   │   │   │   │   └── database.py   # Database operations
│   │   │   │   └── utils/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── logging.py    # Structured logging
│   │   │   │       └── errors.py     # Custom exceptions
│   │   │   └── tests/
│   │   │       ├── __init__.py
│   │   │       ├── conftest.py       # Pytest fixtures
│   │   │       ├── test_agents/
│   │   │       ├── test_workflows/
│   │   │       └── test_api/
│   │   ├── pyproject.toml            # UV dependency management
│   │   ├── Dockerfile                # Multi-stage Python container
│   │   └── docker-compose.dev.yml    # Local development services
│   │
│   ├── web/                          # Next.js Frontend Application  
│   │   ├── src/
│   │   │   ├── app/                  # App Router structure
│   │   │   │   ├── layout.tsx        # Root layout
│   │   │   │   ├── page.tsx          # Home page
│   │   │   │   ├── auth/
│   │   │   │   │   ├── login/
│   │   │   │   │   └── register/
│   │   │   │   ├── trips/
│   │   │   │   │   ├── new/
│   │   │   │   │   └── [trip_id]/
│   │   │   │   └── api/              # API routes for server actions
│   │   │   ├── components/
│   │   │   │   ├── ui/               # Reusable UI components
│   │   │   │   ├── forms/            # Form components
│   │   │   │   ├── maps/             # Map-related components
│   │   │   │   └── layouts/          # Layout components
│   │   │   ├── lib/
│   │   │   │   ├── api.ts           # API client configuration
│   │   │   │   ├── auth.ts          # Authentication utilities
│   │   │   │   ├── utils.ts         # General utilities
│   │   │   │   └── types.ts         # TypeScript type definitions
│   │   │   └── styles/
│   │   │       └── globals.css      # Tailwind CSS imports
│   │   ├── public/
│   │   │   ├── images/
│   │   │   └── icons/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tailwind.config.js
│   │   ├── next.config.js
│   │   └── Dockerfile
│   │
│   └── shared/                       # Shared Utilities and Types
│       ├── src/
│       │   ├── types/               # Shared TypeScript definitions
│       │   ├── utils/               # Cross-platform utilities
│       │   └── constants/           # Application constants
│       ├── package.json
│       └── tsconfig.json
│
├── infrastructure/                   # Infrastructure as Code
│   ├── docker/
│   │   ├── docker-compose.yml       # Production composition
│   │   └── docker-compose.dev.yml   # Development composition
│   ├── terraform/                   # AWS infrastructure (future)
│   └── k8s/                        # Kubernetes manifests (future)
│
├── scripts/                         # Development and deployment scripts
│   ├── setup.sh                    # Initial project setup
│   ├── dev.sh                      # Start development environment
│   ├── test.sh                     # Run all tests
│   └── deploy.sh                   # Deployment automation
│
├── docs/                           # Project documentation
│   ├── architecture.md            # This file
│   ├── prd.md                      # Product requirements
│   ├── api/                        # API documentation
│   └── deployment/                 # Deployment guides
│
├── package.json                    # Root package.json for workspace
├── docker-compose.yml              # Quick start composition
├── .gitignore
├── .env.example                    # Environment variable template
└── README.md                       # Project overview and setup
```
