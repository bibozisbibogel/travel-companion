import { ReactNode } from 'react'
import Header from './Header'
import Footer from './Footer'

interface IUser {
  id: string
  email: string
  name?: string
}

interface IMainLayoutProps {
  children: ReactNode
  user?: IUser | null | undefined
  onLogout?: (() => void) | undefined
  showFooter?: boolean
  className?: string
  containerClassName?: string
  headerProps?: {
    className?: string
  }
  footerProps?: {
    className?: string
  }
}

export default function MainLayout({
  children,
  user,
  onLogout,
  showFooter = true,
  className = '',
  containerClassName = '',
  headerProps = {},
  footerProps = {},
}: IMainLayoutProps) {
  return (
    <div className={`min-h-screen flex flex-col bg-gray-50 ${className}`}>
      {/* Header */}
      <Header 
        user={user} 
        onLogout={onLogout}
        {...headerProps}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        <div className={`max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex-1 ${containerClassName}`}>
          {children}
        </div>
      </main>

      {/* Footer */}
      {showFooter && (
        <Footer {...footerProps} />
      )}
    </div>
  )
}

// Layout variants for different page types
export function CenteredLayout({ 
  children, 
  user, 
  onLogout,
  title,
  subtitle,
  maxWidth = 'max-w-md',
  showFooter = false 
}: IMainLayoutProps & { 
  title?: string
  subtitle?: string 
  maxWidth?: string
}) {
  return (
    <MainLayout 
      user={user} 
      onLogout={onLogout} 
      showFooter={showFooter}
      className="bg-gradient-to-br from-primary-50 via-white to-secondary-50"
    >
      <div className="flex-1 flex items-center justify-center py-12">
        <div className={`w-full ${maxWidth} space-y-6`}>
          {(title || subtitle) && (
            <div className="text-center">
              {title && (
                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                  {title}
                </h1>
              )}
              {subtitle && (
                <p className="text-gray-600">
                  {subtitle}
                </p>
              )}
            </div>
          )}
          <div className="bg-white shadow-travel-lg rounded-lg p-6 sm:p-8">
            {children}
          </div>
        </div>
      </div>
    </MainLayout>
  )
}

export function DashboardLayout({ 
  children, 
  user, 
  onLogout,
  sidebar,
  pageTitle,
  pageDescription,
  actions
}: IMainLayoutProps & {
  sidebar?: ReactNode
  pageTitle?: string
  pageDescription?: string
  actions?: ReactNode
}) {
  return (
    <MainLayout user={user} onLogout={onLogout}>
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        {sidebar && (
          <aside className="w-full lg:w-64 xl:w-72">
            <div className="bg-white rounded-lg shadow-travel-sm p-6 sticky top-24">
              {sidebar}
            </div>
          </aside>
        )}

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {/* Page Header */}
          {(pageTitle || pageDescription || actions) && (
            <div className="bg-white rounded-lg shadow-travel-sm p-6 mb-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  {pageTitle && (
                    <h1 className="text-2xl font-bold text-gray-900">
                      {pageTitle}
                    </h1>
                  )}
                  {pageDescription && (
                    <p className="mt-1 text-sm text-gray-600">
                      {pageDescription}
                    </p>
                  )}
                </div>
                {actions && (
                  <div className="flex items-center space-x-3">
                    {actions}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Page Content */}
          <div className="space-y-6">
            {children}
          </div>
        </div>
      </div>
    </MainLayout>
  )
}

export function FullWidthLayout({ 
  children, 
  user, 
  onLogout,
  showFooter = true,
  backgroundColor = 'bg-gray-50'
}: IMainLayoutProps & { 
  backgroundColor?: string 
}) {
  return (
    <div className={`min-h-screen flex flex-col ${backgroundColor}`}>
      <Header user={user} onLogout={onLogout} />
      
      <main className="flex-1">
        {children}
      </main>

      {showFooter && <Footer />}
    </div>
  )
}