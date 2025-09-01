import Link from 'next/link'

interface IFooterProps {
  className?: string
}

export default function Footer({ className = '' }: IFooterProps) {
  const currentYear = new Date().getFullYear()

  const footerSections = [
    {
      title: 'Travel Planning',
      links: [
        { href: '/trips/new', label: 'Plan New Trip' },
        { href: '/trips', label: 'My Trips' },
        { href: '/destinations', label: 'Popular Destinations' },
        { href: '/guides', label: 'Travel Guides' },
      ]
    },
    {
      title: 'Account',
      links: [
        { href: '/auth/login', label: 'Login' },
        { href: '/auth/register', label: 'Sign Up' },
        { href: '/profile', label: 'My Profile' },
        { href: '/preferences', label: 'Travel Preferences' },
      ]
    },
    {
      title: 'Support',
      links: [
        { href: '/help', label: 'Help Center' },
        { href: '/contact', label: 'Contact Us' },
        { href: '/faq', label: 'FAQ' },
        { href: '/feedback', label: 'Send Feedback' },
      ]
    },
    {
      title: 'Company',
      links: [
        { href: '/about', label: 'About Us' },
        { href: '/privacy', label: 'Privacy Policy' },
        { href: '/terms', label: 'Terms of Service' },
        { href: '/careers', label: 'Careers' },
      ]
    }
  ]

  const socialLinks = [
    {
      name: 'Twitter',
      href: '#',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
        </svg>
      )
    },
    {
      name: 'Facebook',
      href: '#',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path fillRule="evenodd" d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z" clipRule="evenodd" />
        </svg>
      )
    },
    {
      name: 'Instagram',
      href: '#',
      icon: (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path fillRule="evenodd" d="M12.017 0C5.396 0 .029 5.367.029 11.987c0 6.62 5.367 11.987 11.988 11.987s11.987-5.367 11.987-11.987C24.014 5.367 18.647.001 12.017.001zM8.449 16.988c-1.297 0-2.448-.49-3.33-1.297C4.198 14.81 3.708 13.659 3.708 12.362s.49-2.448 1.297-3.33c.881-.881 2.032-1.297 3.33-1.297s2.448.49 3.33 1.297c.881.881 1.297 2.032 1.297 3.33s-.49 2.448-1.297 3.33c-.881.881-2.032 1.297-3.33 1.297zm7.718 0c-1.297 0-2.448-.49-3.33-1.297-.881-.881-1.297-2.032-1.297-3.33s.49-2.448 1.297-3.33c.881-.881 2.032-1.297 3.33-1.297s2.448.49 3.33 1.297c.881.881 1.297 2.032 1.297 3.33s-.49 2.448-1.297 3.33c-.881.881-2.032 1.297-3.33 1.297z" clipRule="evenodd" />
        </svg>
      )
    }
  ]

  return (
    <footer className={`bg-gray-50 border-t border-gray-200 ${className}`}>
      <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        {/* Main Footer Content */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {footerSections.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold text-gray-900 tracking-wider uppercase mb-4">
                {section.title}
              </h3>
              <ul className="space-y-3">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-gray-600 hover:text-primary-600 transition-colors duration-200"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Newsletter Subscription */}
        <div className="mt-12 pt-8 border-t border-gray-200">
          <div className="md:flex md:items-center md:justify-between">
            <div className="max-w-md">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Stay updated with travel tips
              </h3>
              <p className="text-sm text-gray-600 mb-4 md:mb-0">
                Get the latest travel guides, destination recommendations, and planning tips delivered to your inbox.
              </p>
            </div>
            <div className="mt-4 md:mt-0 md:ml-8">
              <form className="flex max-w-md">
                <label htmlFor="email-address" className="sr-only">
                  Email address
                </label>
                <input
                  id="email-address"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="form-input rounded-r-none flex-1 min-w-0"
                  placeholder="Enter your email"
                />
                <button
                  type="submit"
                  className="btn-primary rounded-l-none border-l-0 px-6"
                >
                  Subscribe
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Bottom Section */}
        <div className="mt-8 pt-8 border-t border-gray-200">
          <div className="md:flex md:items-center md:justify-between">
            {/* Brand and Copyright */}
            <div className="flex items-center">
              <Link 
                href="/" 
                className="flex items-center space-x-2 text-lg font-bold text-gradient-travel"
              >
                <span className="text-xl">🧳</span>
                <span>Travel Companion</span>
              </Link>
            </div>

            {/* Social Links */}
            <div className="mt-4 md:mt-0">
              <div className="flex items-center space-x-6">
                {socialLinks.map((item) => (
                  <a
                    key={item.name}
                    href={item.href}
                    className="text-gray-400 hover:text-primary-600 transition-colors duration-200"
                    aria-label={`Follow us on ${item.name}`}
                  >
                    {item.icon}
                  </a>
                ))}
              </div>
            </div>
          </div>

          {/* Copyright */}
          <div className="mt-6 text-center md:text-left">
            <p className="text-sm text-gray-600">
              © {currentYear} Travel Companion. All rights reserved. Built with ❤️ for travelers worldwide.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}