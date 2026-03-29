import { useMemo } from 'react';

import { useMutation, useQuery } from '@tanstack/react-query';
import { AlertTriangle, Loader2, MapPin, RefreshCw, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { MapContainer, Rectangle, TileLayer, Tooltip } from 'react-leaflet';

import { Button } from '@/components/ui/button';
import { queryClientInstance } from '@/lib/query-client';
import { API_BASE_URL, fetchDashboardState, runPipeline, submitMatchDecision } from '@/api/base44Client';

// County center points for Tampa Bay — tracts are positioned in a grid around each center
const COUNTY_CENTERS = {
  '12057': { lat: 27.95, lon: -82.46 }, // Hillsborough
  '12103': { lat: 27.77, lon: -82.68 }, // Pinellas
  '12081': { lat: 27.48, lon: -82.57 }, // Manatee
  '12101': { lat: 28.18, lon: -82.43 }, // Pasco
};
const TRACT_SIZE = 0.06;  // degrees per side (~6km) — visible but not overlapping
const STEP = 0.07;        // spacing between tract centers
const COLS = 4;           // tracts per row within a county

function computeTractBounds(communities) {
  const countyIdx = {};
  return communities.map((community) => {
    const fips = community.county_fips;
    const center = COUNTY_CENTERS[fips] || { lat: 27.85, lon: -82.55 };
    const idx = countyIdx[fips] ?? 0;
    countyIdx[fips] = idx + 1;
    const row = Math.floor(idx / COLS);
    const col = idx % COLS;
    const lat = center.lat + (row - 1) * STEP;
    const lon = center.lon + (col - Math.floor(COLS / 2)) * STEP;
    return {
      ...community,
      bounds: [
        [lat - TRACT_SIZE / 2, lon - TRACT_SIZE / 2],
        [lat + TRACT_SIZE / 2, lon + TRACT_SIZE / 2],
      ],
    };
  });
}

function vulnerabilityMeta(score) {
  if (score >= 0.75) return { label: 'High', color: '#cd3a3a' };
  if (score >= 0.4) return { label: 'Medium', color: '#d6aa00' };
  return { label: 'Low', color: '#2e7d32' };
}

function ResourcePanel({ resources, agencies }) {
  return (
    <section className="rounded-2xl bg-card border border-border p-5 h-full shadow-sm">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-electric uppercase tracking-[0.22em]">Resource Inventory</h2>
        <p className="text-xs text-muted-foreground mt-1">
          Current stock available to the operator from the backend inventory feed.
        </p>
      </div>
      <div className="overflow-hidden rounded-xl border border-border">
        <div className="grid grid-cols-[1.1fr_72px_1.4fr_1.1fr] gap-3 bg-muted/30 px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          <span>Type</span>
          <span>Qty</span>
          <span>Location</span>
          <span>Agency</span>
        </div>
        {resources.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground bg-background/40">
            Run the pipeline to populate inventory.
          </div>
        ) : (
          resources.map((resource) => (
            <div
              key={resource.resource_id}
              className="grid grid-cols-[1.1fr_72px_1.4fr_1.1fr] gap-3 border-t border-border bg-background/40 px-4 py-3 text-sm"
            >
              <div>
                <p className="font-semibold text-cloud-signal">{resource.type}</p>
                <p className="text-xs text-muted-foreground mt-1">{resource.subtype}</p>
              </div>
              <div className="font-semibold text-electric">{resource.quantity}</div>
              <div className="text-muted-foreground">{resource.location.address}</div>
              <div className="text-muted-foreground">
                {agencies[resource.owner_agency_id] || resource.owner_agency_id}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function NeedsMapPanel({ communities, needs }) {
  const needsByTract = useMemo(
    () => Object.fromEntries(needs.map((need) => [need.community_fips_tract, need])),
    [needs]
  );
  const communityRows = useMemo(
    () =>
      communities.map((community) => {
        const need = needsByTract[community.fips_tract];
        const meta = vulnerabilityMeta(Number(community.vulnerability_index));
        return {
          tract: community.fips_tract,
          county: community.county_name || community.county_fips,
          vulnerability: community.vulnerability_index,
          label: meta.label,
          severity: need?.severity ?? 'N/A',
          needType: need?.need_type ?? 'N/A',
        };
      }),
    [communities, needsByTract]
  );

  const communitiesWithBounds = useMemo(() => computeTractBounds(communities), [communities]);

  return (
    <section className="rounded-2xl bg-card border border-border p-5 h-full shadow-sm">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-electric uppercase tracking-[0.22em]">Needs Map + SVI Heat</h2>
        <p className="text-xs text-muted-foreground mt-1">
          Florida tracts colored by vulnerability score with severity visible on hover, per the B6 operator view.
        </p>
      </div>
      {communities.length === 0 ? (
        <p className="text-sm text-muted-foreground">Run the pipeline to render vulnerability-aware tract needs.</p>
      ) : (
        <>
          <div className="overflow-hidden rounded-2xl border border-border">
            <MapContainer center={[27.87, -82.55]} zoom={8} scrollWheelZoom={false} style={{ height: 420, width: '100%' }}>
              <TileLayer
                attribution='&copy; OpenStreetMap contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {communitiesWithBounds.map((community) => {
                const need = needsByTract[community.fips_tract];
                const meta = vulnerabilityMeta(Number(community.vulnerability_index));
                return (
                  <Rectangle
                    key={community.fips_tract}
                    bounds={community.bounds}
                    pathOptions={{
                      color: meta.color,
                      fillColor: meta.color,
                      fillOpacity: 0.5,
                      weight: 1.5,
                    }}
                  >
                    <Tooltip sticky>
                      <div className="text-xs leading-5">
                        <div><strong>Tract:</strong> {community.fips_tract}</div>
                        <div><strong>County:</strong> {community.county_name}</div>
                        <div><strong>Vulnerability:</strong> {community.vulnerability_index} ({meta.label})</div>
                        <div><strong>Population:</strong> {community.population?.toLocaleString()}</div>
                        <div><strong>Need:</strong> {need?.need_type ?? 'N/A'}</div>
                        <div><strong>Severity:</strong> {need?.severity ?? 'N/A'}</div>
                      </div>
                    </Tooltip>
                  </Rectangle>
                );
              })}
            </MapContainer>
          </div>
          <div className="mt-4 grid sm:grid-cols-3 gap-3">
            {['Low', 'Medium', 'High'].map((label) => {
              const color = label === 'High' ? '#cd3a3a' : label === 'Medium' ? '#d6aa00' : '#2e7d32';
              return (
                <div key={label} className="rounded-xl border border-border p-3 bg-background/40">
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                    <span className="text-sm font-medium text-cloud-signal">{label} Vulnerability</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Color and text label used together for accessibility.</p>
                </div>
              );
            })}
          </div>
          <div className="mt-4 rounded-xl border border-border bg-background/40">
            <div className="grid grid-cols-[1fr_84px_100px_84px] gap-3 px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              <span>Tract / Need</span>
              <span>County</span>
              <span>Vulnerability</span>
              <span>Severity</span>
            </div>
            {communityRows.map((row) => (
              <div
                key={row.tract}
                className="grid grid-cols-[1fr_84px_100px_84px] gap-3 border-t border-border px-4 py-3 text-sm"
              >
                <div>
                  <p className="font-medium text-cloud-signal">{row.tract}</p>
                  <p className="text-xs text-muted-foreground mt-1">{row.needType}</p>
                </div>
                <div className="text-muted-foreground">{row.county}</div>
                <div className="text-muted-foreground">
                  {row.vulnerability} <span className="text-cloud-signal">({row.label})</span>
                </div>
                <div className="font-medium text-cloud-signal">{row.severity}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function MatchPanel({ matches, resourcesById, needsById, onDecision, isSubmitting }) {
  return (
    <section className="rounded-2xl bg-card border border-border p-5 h-full shadow-sm">
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-electric uppercase tracking-[0.22em]">Match List</h2>
        <p className="text-xs text-muted-foreground mt-1">
          Human-in-the-loop review actions from CF-06 and CF-07: Accept, Modify, or Skip.
        </p>
      </div>
      <div className="space-y-3">
        {matches.length === 0 ? (
          <p className="text-sm text-muted-foreground">Run the pipeline to generate match recommendations.</p>
        ) : (
          matches.map((match) => {
            const resource = resourcesById[match.resource_id];
            const need = needsById[match.need_id];
            return (
              <div key={match.match_id} className="rounded-xl border border-border p-4 bg-background/40">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Equity Score</p>
                    <p className="text-lg font-semibold text-cloud-signal mt-1">{match.equity_score}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      {resource?.subtype || match.resource_id} to {need?.need_type || match.need_id}
                    </p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-electric/10 text-electric border border-electric/20">
                    {match.status}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-muted-foreground">
                  <div className="rounded-lg border border-border bg-card/50 p-3">
                    <p className="font-semibold text-cloud-signal mb-1">Matched Resource</p>
                    <p>{resource?.subtype || match.resource_id}</p>
                  </div>
                  <div className="rounded-lg border border-border bg-card/50 p-3">
                    <p className="font-semibold text-cloud-signal mb-1">Matched Need</p>
                    <p>{need?.need_type || match.need_id}</p>
                  </div>
                </div>
                <div className="mt-3 text-xs text-muted-foreground space-y-1">
                  <p><span className="text-cloud-signal">Route:</span> {match.routing_plan?.origin ?? 'Pending'} → {match.routing_plan?.destination ?? 'Pending'}</p>
                  <p><span className="text-cloud-signal">ETA:</span> {match.routing_plan?.eta_hours != null ? `${match.routing_plan.eta_hours}h` : 'TBD'}</p>
                </div>
                <div className="grid grid-cols-3 gap-2 mt-4">
                  {['accept', 'modify', 'skip'].map((decision) => (
                    <Button
                      key={decision}
                      variant={decision === 'accept' ? 'default' : 'outline'}
                      className={decision === 'accept' ? 'bg-electric text-atlantic hover:bg-electric/90' : 'border-border'}
                      disabled={isSubmitting}
                      onClick={() => onDecision(match.match_id, decision)}
                    >
                      {decision[0].toUpperCase() + decision.slice(1)}
                    </Button>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

export default function Dashboard() {
  const dashboardQuery = useQuery({
    queryKey: ['relieflink-dashboard'],
    queryFn: fetchDashboardState,
  });

  const pipelineMutation = useMutation({
    mutationFn: runPipeline,
    onSuccess: (data) => {
      queryClientInstance.invalidateQueries({ queryKey: ['relieflink-dashboard'] });
      toast.success(`Pipeline complete: ${data.status} (${data.iterations_run} iterations).`);
    },
    onError: (error) => {
      toast.error(
        error.message || `Pipeline failed. Ensure GOOGLE_API_KEY is set and the backend is reachable at ${API_BASE_URL}.`
      );
    },
  });

  const decisionMutation = useMutation({
    mutationFn: ({ matchId, decision }) => submitMatchDecision(matchId, decision),
    onSuccess: (data) => {
      queryClientInstance.invalidateQueries({ queryKey: ['relieflink-dashboard'] });
      toast.success(`Match ${data.match_id} updated to ${data.new_status}.`);
    },
    onError: (error) => {
      toast.error(error.message || `Decision failed. Check the backend is running at ${API_BASE_URL} and try again.`);
    },
  });

  const payload = dashboardQuery.data || {
    matches: [],
    resources: [],
    communities: [],
    needs: [],
    agencies: [],
    summary: { total_resources: 0, total_needs: 0, matched: 0, pending: 0 },
  };

  const agenciesById = Object.fromEntries((payload.agencies || []).map((agency) => [agency.agency_id, agency.name]));
  const resourcesById = Object.fromEntries((payload.resources || []).map((resource) => [resource.resource_id, resource]));
  const needsById = Object.fromEntries((payload.needs || []).map((need) => [need.need_id, need]));

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-3xl border border-border bg-card/80 px-6 py-6 sm:px-8 mb-8 shadow-sm"
      >
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-electric">ReliefLink</p>
            <h1 className="text-3xl sm:text-4xl font-bold text-cloud-signal mt-2">
              Disaster relief resource matching with equity-first routing.
            </h1>
            <p className="text-muted-foreground mt-3 max-w-3xl">
              This view follows the system design operator dashboard: Resource Inventory on the left, Needs Map plus SVI Heat in the center, and Match List on the right.
            </p>
          </div>
          <div className="flex items-center gap-3 lg:self-start">
            <Button
              variant="outline"
              size="icon"
              onClick={() => dashboardQuery.refetch()}
              className="border-border text-muted-foreground hover:text-electric"
            >
              <RefreshCw className={`h-4 w-4 ${dashboardQuery.isFetching ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              onClick={() => pipelineMutation.mutate()}
              disabled={pipelineMutation.isPending}
              className="bg-electric text-atlantic hover:bg-electric/90 font-semibold gap-2"
            >
              {pipelineMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              Run Pipeline
            </Button>
          </div>
        </div>
      </motion.div>

      {dashboardQuery.isError && (
        <div className="mb-6 rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 mt-0.5" />
          <div>
            <p className="font-medium">Backend unavailable</p>
            <p>Unable to reach backend at {API_BASE_URL}: {dashboardQuery.error.message}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <div className="p-4 rounded-xl bg-card border border-border">
          <p className="text-xs text-muted-foreground mb-1">Resources</p>
          <p className="text-2xl font-bold text-cloud-signal">{payload.summary.total_resources}</p>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border">
          <p className="text-xs text-muted-foreground mb-1">Needs</p>
          <p className="text-2xl font-bold text-cloud-signal">{payload.summary.total_needs}</p>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border">
          <p className="text-xs text-muted-foreground mb-1">Matches</p>
          <p className="text-2xl font-bold text-electric">{payload.summary.matched}</p>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border">
          <p className="text-xs text-muted-foreground mb-1">Pending Decisions</p>
          <p className="text-2xl font-bold text-red-400">{payload.summary.pending}</p>
        </div>
      </div>

      {dashboardQuery.isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-electric" />
        </div>
      ) : (
        <div className="grid lg:grid-cols-[1.15fr_1.35fr_1.15fr] gap-6 items-start">
          <ResourcePanel resources={payload.resources} agencies={agenciesById} />
          <NeedsMapPanel communities={payload.communities} needs={payload.needs} />
          <MatchPanel
            matches={payload.matches}
            resourcesById={resourcesById}
            needsById={needsById}
            isSubmitting={decisionMutation.isPending}
            onDecision={(matchId, decision) => decisionMutation.mutate({ matchId, decision })}
          />
        </div>
      )}

      <div className="mt-8 rounded-2xl bg-card border border-border p-5 text-sm text-muted-foreground">
        <p className="flex items-center gap-2 text-cloud-signal font-medium mb-2">
          <MapPin className="h-4 w-4 text-electric" />
          System-design note
        </p>
        <p>
          The page composition and labels here intentionally follow the system design doc’s B6 dashboard and CF-06 review flow, while keeping the Base44 component styling layer and the existing backend API contract unchanged.
        </p>
      </div>
    </div>
  );
}
