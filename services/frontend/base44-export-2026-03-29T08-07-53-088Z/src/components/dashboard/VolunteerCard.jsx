import { MapPin, Clock, CheckCircle2 } from 'lucide-react';
import moment from 'moment';

const categoryLabels = {
  shelter: 'Shelter',
  food_water: 'Food & Water',
  medical: 'Medical',
  transportation: 'Transportation',
  cleanup: 'Cleanup',
  supplies: 'Supplies',
  other: 'Other',
};

export default function VolunteerCard({ volunteer }) {
  const isAvailable = volunteer.status === 'available';

  return (
    <div className="p-4 rounded-xl bg-card border border-border hover:border-electric/20 transition-all">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-cloud-signal">{volunteer.name}</h3>
          {volunteer.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{volunteer.description}</p>
          )}
        </div>
        {isAvailable ? (
          <span className="flex items-center gap-1 text-xs text-electric flex-shrink-0">
            <div className="w-1.5 h-1.5 rounded-full bg-electric animate-pulse" />
            Available
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-green-400 flex-shrink-0">
            <CheckCircle2 className="h-3 w-3" /> Matched
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3" /> {volunteer.county}
        </span>
        {volunteer.availability && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" /> {volunteer.availability}
          </span>
        )}
        <span className="text-xs px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
          {categoryLabels[volunteer.category] || volunteer.category}
        </span>
      </div>
    </div>
  );
}