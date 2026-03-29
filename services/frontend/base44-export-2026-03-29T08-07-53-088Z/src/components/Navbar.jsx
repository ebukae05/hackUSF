import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';

const navLinks = [
  { label: 'Dashboard', path: '/dashboard' },
  { label: 'Request Help', path: '/request-help' },
  { label: 'Volunteer', path: '/volunteer' },
  { label: 'About', path: '/about' },
];

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative">
              <Shield className="h-7 w-7 text-electric" />
              <div className="absolute inset-0 bg-electric/20 rounded-full blur-md group-hover:blur-lg transition-all" />
            </div>
            <span className="text-lg font-bold tracking-tight text-cloud-signal">
              Relief<span className="text-electric">Link</span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  location.pathname === link.path
                    ? 'text-electric bg-electric/10'
                    : 'text-cloud-signal/70 hover:text-cloud-signal hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <Link to="/request-help">
              <Button variant="outline" size="sm" className="border-electric/30 text-electric hover:bg-electric/10 hover:text-electric">
                I Need Help
              </Button>
            </Link>
            <Link to="/volunteer">
              <Button size="sm" className="bg-electric text-atlantic hover:bg-electric/90 font-semibold">
                I Can Help
              </Button>
            </Link>
          </div>

          <button
            className="md:hidden text-cloud-signal p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden glass border-t border-border"
          >
            <div className="px-4 py-4 space-y-2">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                    location.pathname === link.path
                      ? 'text-electric bg-electric/10'
                      : 'text-cloud-signal/70 hover:text-cloud-signal'
                  }`}
                >
                  {link.label}
                </Link>
              ))}
              <div className="flex gap-2 pt-3 border-t border-border">
                <Link to="/request-help" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button variant="outline" className="w-full border-electric/30 text-electric hover:bg-electric/10">
                    I Need Help
                  </Button>
                </Link>
                <Link to="/volunteer" className="flex-1" onClick={() => setMobileOpen(false)}>
                  <Button className="w-full bg-electric text-atlantic hover:bg-electric/90 font-semibold">
                    I Can Help
                  </Button>
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}