'use client'

import Link from 'next/link'
import { MainLayout } from '../components/layouts'
import { useAuth } from '../contexts/AuthContext'
import { useHasTrips } from '../hooks/useTrips'

export default function Home() {
  const { isAuthenticated } = useAuth()
  const { hasTrips, isLoading: loadingTrips } = useHasTrips(isAuthenticated)
  return (
    <MainLayout>
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-16 pb-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
                Plan Your Perfect
                <span className="text-gradient-travel block">
                  Travel Adventure
                </span>
              </h1>
              <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
                Discover amazing destinations, create personalized itineraries, and book unforgettable experiences with our AI-powered travel planning assistant.
              </p>
              
              {/* Quick Stats */}
              <div className="flex justify-center space-x-8 mb-16">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary-600">1000+</div>
                  <div className="text-sm text-gray-600">Destinations</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary-600">50K+</div>
                  <div className="text-sm text-gray-600">Happy Travelers</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary-600">24/7</div>
                  <div className="text-sm text-gray-600">Support</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Travel Request Form Section */}
        <section className="relative -mt-16 pb-16">
          {!isAuthenticated ? (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="text-center">
                <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
                  <span className="text-gradient-travel">Start Today</span>
                </h2>
                <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
                  Join Travel Companion and begin planning your dream vacation with AI-powered recommendations
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
                  <Link
                    href="/auth/login"
                    className="btn-outline text-lg px-8 py-4"
                  >
                    Log In
                  </Link>
                  <Link
                    href="/auth/register"
                    className="btn-primary text-lg px-8 py-4"
                  >
                    Sign Up
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="text-center">
                {!loadingTrips && (
                  hasTrips ? (
                    <Link
                      href="/trips"
                      className="inline-block btn-primary text-lg px-8 py-4"
                    >
                      View My Trips
                    </Link>
                  ) : (
                    <Link
                      href="/trips/new"
                      className="inline-block btn-primary text-lg px-8 py-4"
                    >
                      Start Planning a Trip
                    </Link>
                  )
                )}
              </div>
            </div>
          )}
        </section>

        {/* Features Section */}
        <section className="py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Why Choose Travel Companion?
              </h2>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                We make travel planning effortless with intelligent recommendations and personalized experiences
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-6">
                  <span className="text-3xl">🤖</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  AI-Powered Planning
                </h3>
                <p className="text-gray-600">
                  Our advanced AI analyzes your preferences and creates personalized itineraries that match your travel style perfectly.
                </p>
              </div>
              
              {/* Feature 2 */}
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-secondary-100 rounded-full mb-6">
                  <span className="text-3xl">🌍</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  Global Destinations
                </h3>
                <p className="text-gray-600">
                  Access thousands of destinations worldwide with detailed insights, local recommendations, and hidden gems.
                </p>
              </div>
              
              {/* Feature 3 */}
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-6">
                  <span className="text-3xl">⚡</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  Instant Results
                </h3>
                <p className="text-gray-600">
                  Get your complete travel plan in minutes, not hours. Real-time availability and pricing for flights, hotels, and activities.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Popular Destinations Section */}
        <section className="py-24 bg-gray-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Popular Destinations
              </h2>
              <p className="text-xl text-gray-600">
                Discover the world&apos;s most loved travel destinations
              </p>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {[
                { name: 'Tokyo', country: 'Japan', emoji: '🏯' },
                { name: 'Paris', country: 'France', emoji: '🗼' },
                { name: 'Bali', country: 'Indonesia', emoji: '🏝️' },
                { name: 'New York', country: 'USA', emoji: '🗽' },
                { name: 'London', country: 'UK', emoji: '🏰' },
                { name: 'Rome', country: 'Italy', emoji: '🏛️' },
                { name: 'Barcelona', country: 'Spain', emoji: '🏘️' },
                { name: 'Thailand', country: 'Thailand', emoji: '🛕' },
              ].map((destination) => (
                <Link
                  key={destination.name}
                  href={`/destinations/${destination.name.toLowerCase()}`}
                  className="group bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-105"
                >
                  <div className="text-center">
                    <div className="text-4xl mb-3 group-hover:scale-110 transition-transform duration-200">
                      {destination.emoji}
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {destination.name}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {destination.country}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
            
            <div className="text-center mt-12">
              <Link
                href="/destinations"
                className="btn-outline text-lg px-8 py-3"
              >
                Explore All Destinations
              </Link>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-24">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Ready to Start Your Adventure?
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Join thousands of travelers who trust Travel Companion to plan their perfect trips
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/trips/new"
                className="btn-primary text-lg px-8 py-4"
              >
                Plan My Trip
              </Link>
              <Link
                href="/auth/register"
                className="btn-outline text-lg px-8 py-4"
              >
                Create Account
              </Link>
            </div>
          </div>
        </section>
      </div>
    </MainLayout>
  )
}
