import { Zap } from 'lucide-react';

const tickerItems = [
  "Volunteer matched with Shelter 4 in St. Pete",
  "200 gallons of water delivered to Ybor City",
  "Medical team dispatched to Clearwater Beach",
  "15 families sheltered in Hillsborough County",
  "Debris cleanup crew active in Manatee County",
  "Emergency supplies arriving at Tampa Convention Center",
  "Boat rescue team deployed to Bayshore Blvd",
  "Food distribution active at 3 locations across Pinellas",
];

export default function StatusTicker() {
  const doubled = [...tickerItems, ...tickerItems];

  return (
    <div className="fixed top-16 left-0 right-0 z-40 bg-electric/10 border-b border-electric/20 overflow-hidden">
      <div className="flex items-center h-8">
        <div className="flex-shrink-0 flex items-center gap-1.5 px-3 bg-electric/20 h-full border-r border-electric/20">
          <Zap className="h-3 w-3 text-electric" />
          <span className="text-xs font-semibold text-electric uppercase tracking-wider">Live</span>
        </div>
        <div className="overflow-hidden flex-1">
          <div className="animate-ticker flex whitespace-nowrap">
            {doubled.map((item, i) => (
              <span key={i} className="inline-flex items-center px-6 text-xs text-cloud-signal/70">
                <span className="w-1.5 h-1.5 rounded-full bg-electric/60 mr-2.5 flex-shrink-0" />
                {item}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}