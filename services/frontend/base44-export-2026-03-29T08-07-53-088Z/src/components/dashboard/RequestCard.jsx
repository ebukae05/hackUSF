import { MapPin, Users, Clock } from 'lucide-react';
import moment from 'moment';

const urgencyConfig = {
  critical: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', dot: 'bg-red-400' },
  high: { bg: 'bg-alert-amber/10', text: 'text-alert-amber', border: 'border-alert-amber/20', dot: 'bg-alert-amber' },
  medium: { bg: 'bg-electric/10', text: 'text-electric', border: 'border-electric/20', dot: 'bg-electric' },
  low: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/20', dot: 'bg-green-400' },
};

const categoryLabels = {
  shelter: 'Shelter',
  food_water: 'Food & Water',
  medical: 'Medical',
  transportation: 'Transportation',
  cleanup: 'Cleanup',
  supplies: 'Supplies',
  other: 'Other',
};

const statusConfig = {
  open: { text: 'text-electric', label: 'Open' },
  matched: { text: 'text-alert-amber', label: 'Matched' },
  in_progress: { text: 'text-blue-400', label: 'In Progress' },
  resolved: { text: 'text-green-400', label: 'Resolved' },
};

export default function RequestCard({ request }) {
  const urgency = urgencyConfig[request.urgency] || urgencyConfig.medium;
  const status = statusConfig[request.status] || statusConfig.open;

  return (
    <div className="p-4 rounded-xl bg-card border border-border hover:border-electric/20 transition-all">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-cloud-signal">{request.title}</h3>
          {request.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{request.description}</p>
          )}
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full border ${urgency.bg} ${urgency.text} ${urgency.border} flex-shrink-0`}>
          {request.urgency}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3" /> {request.location}, {request.county}
        </span>
        {request.people_affected && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Users className="h-3 w-3" /> {request.people_affected} people
          </span>
        )}
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" /> {moment(request.created_date).fromNow()}
        </span>
        <span className="text-xs px-2 py-0.5 rounded bg-secondary text-secondary-foreground">
          {categoryLabels[request.category] || request.category}
        </span>
        <span className={`text-xs font-medium ${status.text} ml-auto`}>{status.label}</span>
      </div>
    </div>
  );
}