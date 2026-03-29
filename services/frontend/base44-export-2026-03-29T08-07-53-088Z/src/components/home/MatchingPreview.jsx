import { motion } from 'framer-motion';
import { ArrowLeftRight, MapPin, Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

const sampleNeeds = [
  { id: 1, title: 'Water & Food Needed', location: 'Ybor City', county: 'Hillsborough', urgency: 'critical', people: 45 },
  { id: 2, title: 'Medical Assistance Required', location: 'Clearwater Beach', county: 'Pinellas', urgency: 'high', people: 12 },
  { id: 3, title: 'Shelter for Displaced Family', location: 'Bradenton', county: 'Manatee', urgency: 'high', people: 6 },
];

const sampleVolunteers = [
  { id: 1, name: 'Tampa Medical Reserve Corps', skill: 'Medical', county: 'Hillsborough', status: 'available' },
  { id: 2, name: 'Boat Rescue Team Alpha', skill: 'Transportation', county: 'Pinellas', status: 'available' },
  { id: 3, name: 'Bay Area Food Bank', skill: 'Food & Water', county: 'Hillsborough', status: 'matched' },
];

const urgencyColors = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-alert-amber/10 text-alert-amber border-alert-amber/20',
  medium: 'bg-electric/10 text-electric border-electric/20',
};

export default function MatchingPreview() {
  return (
    <section className="py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-14"
        >
          <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3">The Matching Nexus</h2>
          <p className="text-3xl sm:text-4xl font-bold text-cloud-signal">
            Supply Meets Demand — Instantly
          </p>
          <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
            Our AI-powered matching engine connects those who need help with available resources in real time.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-6 relative">
          {/* Connecting line */}
          <div className="hidden lg:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
            <div className="w-14 h-14 rounded-full bg-electric/20 border-2 border-electric flex items-center justify-center">
              <ArrowLeftRight className="h-5 w-5 text-electric" />
            </div>
          </div>

          {/* Demand side */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-2xl bg-card border border-border p-6"
          >
            <div className="flex items-center gap-2 mb-5">
              <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
              <h3 className="font-semibold text-cloud-signal">Active Requests</h3>
              <span className="ml-auto text-xs bg-red-500/10 text-red-400 px-2 py-0.5 rounded-full">{sampleNeeds.length} Open</span>
            </div>
            <div className="space-y-3">
              {sampleNeeds.map((need) => (
                <div key={need.id} className="p-4 rounded-xl bg-background/50 border border-border hover:border-electric/20 transition-all">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-cloud-signal">{need.title}</h4>
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3" /> {need.location}
                        </span>
                        <span className="text-xs text-muted-foreground">{need.people} people</span>
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${urgencyColors[need.urgency]}`}>
                      {need.urgency}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Supply side */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="rounded-2xl bg-card border border-border p-6"
          >
            <div className="flex items-center gap-2 mb-5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <h3 className="font-semibold text-cloud-signal">Available Resources</h3>
              <span className="ml-auto text-xs bg-green-500/10 text-green-400 px-2 py-0.5 rounded-full">
                {sampleVolunteers.filter(v => v.status === 'available').length} Ready
              </span>
            </div>
            <div className="space-y-3">
              {sampleVolunteers.map((vol) => (
                <div key={vol.id} className="p-4 rounded-xl bg-background/50 border border-border hover:border-electric/20 transition-all">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-cloud-signal">{vol.name}</h4>
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <MapPin className="h-3 w-3" /> {vol.county}
                        </span>
                        <span className="text-xs text-muted-foreground">{vol.skill}</span>
                      </div>
                    </div>
                    {vol.status === 'matched' ? (
                      <span className="flex items-center gap-1 text-xs text-green-400">
                        <CheckCircle2 className="h-3 w-3" /> Matched
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-electric">
                        <Clock className="h-3 w-3" /> Available
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        <div className="text-center mt-10">
          <Link to="/dashboard">
            <Button variant="outline" className="border-electric/30 text-electric hover:bg-electric/10">
              View Full Dashboard →
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}