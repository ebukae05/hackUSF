import { Link } from 'react-router-dom';
import { Shield, Phone, Mail, Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Emergency bar */}
        <div className="py-6 border-b border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-alert-amber animate-pulse" />
            <span className="text-sm font-medium text-alert-amber">Emergency Hotline: (813) 555-HELP</span>
          </div>
          <Link to="/request-help">
            <Button className="bg-alert-amber text-atlantic hover:bg-alert-amber/90 font-bold gap-2">
              <Heart className="h-4 w-4" />
              Emergency Request
            </Button>
          </Link>
        </div>

        {/* Main footer */}
        <div className="py-12 grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-1">
            <Link to="/" className="flex items-center gap-2 mb-4">
              <Shield className="h-6 w-6 text-electric" />
              <span className="text-lg font-bold text-cloud-signal">
                Relief<span className="text-electric">Link</span>
              </span>
            </Link>
            <p className="text-sm text-muted-foreground leading-relaxed">
              AI-powered disaster relief matching for the Tampa Bay area. Connecting those in need with those who can help.
            </p>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-cloud-signal mb-4">Quick Links</h4>
            <div className="space-y-2.5">
              <Link to="/request-help" className="block text-sm text-muted-foreground hover:text-electric transition-colors">Request Help</Link>
              <Link to="/volunteer" className="block text-sm text-muted-foreground hover:text-electric transition-colors">Volunteer</Link>
              <Link to="/dashboard" className="block text-sm text-muted-foreground hover:text-electric transition-colors">Live Dashboard</Link>
              <Link to="/about" className="block text-sm text-muted-foreground hover:text-electric transition-colors">About Us</Link>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-cloud-signal mb-4">Counties Served</h4>
            <div className="space-y-2.5">
              <p className="text-sm text-muted-foreground">Hillsborough County</p>
              <p className="text-sm text-muted-foreground">Pinellas County</p>
              <p className="text-sm text-muted-foreground">Manatee County</p>
              <p className="text-sm text-muted-foreground">Pasco County</p>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-cloud-signal mb-4">Contact</h4>
            <div className="space-y-2.5">
              <a href="tel:8135554357" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-electric transition-colors">
                <Phone className="h-3.5 w-3.5" />
                (813) 555-HELP
              </a>
              <a href="mailto:help@relieflink.org" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-electric transition-colors">
                <Mail className="h-3.5 w-3.5" />
                help@relieflink.org
              </a>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="py-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">
            © 2026 ReliefLink Tampa Bay. All rights reserved.
          </p>
          <p className="text-xs text-muted-foreground">
            Built with compassion for the Tampa Bay community.
          </p>
        </div>
      </div>
    </footer>
  );
}