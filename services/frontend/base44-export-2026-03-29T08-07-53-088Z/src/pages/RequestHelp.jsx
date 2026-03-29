import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { HandHelping, AlertTriangle, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

const categories = [
  { value: 'shelter', label: 'Shelter' },
  { value: 'food_water', label: 'Food & Water' },
  { value: 'medical', label: 'Medical Assistance' },
  { value: 'transportation', label: 'Transportation' },
  { value: 'cleanup', label: 'Cleanup' },
  { value: 'supplies', label: 'Supplies' },
  { value: 'other', label: 'Other' },
];

const urgencies = [
  { value: 'critical', label: 'Critical — Immediate danger' },
  { value: 'high', label: 'High — Urgent need' },
  { value: 'medium', label: 'Medium — Can wait hours' },
  { value: 'low', label: 'Low — Non-urgent' },
];

const counties = ['Hillsborough', 'Pinellas', 'Manatee', 'Pasco'];

export default function RequestHelp() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    title: '', description: '', category: '', urgency: '',
    location: '', county: '', contact_name: '', contact_phone: '', contact_email: '',
    people_affected: '',
  });

  const update = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    toast.info('Public help-request intake is not available in the current backend. Use the operator dashboard to review active needs and matches.');
    navigate('/dashboard');
    setLoading(false);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20 mb-4">
          <AlertTriangle className="h-3.5 w-3.5 text-red-400" />
          <span className="text-xs font-medium text-red-400">EMERGENCY REQUEST</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-cloud-signal">Request Help</h1>
        <p className="mt-2 text-muted-foreground">
          Fill out this form and we'll match you with available resources as quickly as possible.
        </p>
      </motion.div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
          <h2 className="text-sm font-semibold text-electric uppercase tracking-wider">What do you need?</h2>

          <div className="space-y-2">
            <Label className="text-cloud-signal">Title *</Label>
            <Input
              placeholder="Brief description of your need"
              value={form.title}
              onChange={e => update('title', e.target.value)}
              required
              className="bg-background border-border text-cloud-signal"
            />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-cloud-signal">Category *</Label>
              <Select value={form.category} onValueChange={v => update('category', v)} required>
                <SelectTrigger className="bg-background border-border text-cloud-signal">
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map(c => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-cloud-signal">Urgency Level *</Label>
              <Select value={form.urgency} onValueChange={v => update('urgency', v)} required>
                <SelectTrigger className="bg-background border-border text-cloud-signal">
                  <SelectValue placeholder="Select urgency" />
                </SelectTrigger>
                <SelectContent>
                  {urgencies.map(u => <SelectItem key={u.value} value={u.value}>{u.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-cloud-signal">Description</Label>
            <Textarea
              placeholder="Provide more details about your situation..."
              value={form.description}
              onChange={e => update('description', e.target.value)}
              rows={4}
              className="bg-background border-border text-cloud-signal"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-cloud-signal">People Affected</Label>
            <Input
              type="number"
              placeholder="Approximate number"
              value={form.people_affected}
              onChange={e => update('people_affected', e.target.value)}
              className="bg-background border-border text-cloud-signal"
            />
          </div>
        </div>

        <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
          <h2 className="text-sm font-semibold text-electric uppercase tracking-wider">Location</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-cloud-signal">Address / Area *</Label>
              <Input
                placeholder="Street address or area name"
                value={form.location}
                onChange={e => update('location', e.target.value)}
                required
                className="bg-background border-border text-cloud-signal"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-cloud-signal">County *</Label>
              <Select value={form.county} onValueChange={v => update('county', v)} required>
                <SelectTrigger className="bg-background border-border text-cloud-signal">
                  <SelectValue placeholder="Select county" />
                </SelectTrigger>
                <SelectContent>
                  {counties.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
          <h2 className="text-sm font-semibold text-electric uppercase tracking-wider">Contact Information</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-cloud-signal">Your Name *</Label>
              <Input
                placeholder="Full name"
                value={form.contact_name}
                onChange={e => update('contact_name', e.target.value)}
                required
                className="bg-background border-border text-cloud-signal"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-cloud-signal">Phone</Label>
              <Input
                placeholder="(813) 555-1234"
                value={form.contact_phone}
                onChange={e => update('contact_phone', e.target.value)}
                className="bg-background border-border text-cloud-signal"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-cloud-signal">Email</Label>
            <Input
              type="email"
              placeholder="your@email.com"
              value={form.contact_email}
              onChange={e => update('contact_email', e.target.value)}
              className="bg-background border-border text-cloud-signal"
            />
          </div>
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full bg-electric text-atlantic hover:bg-electric/90 font-bold h-12 text-base gap-2"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <HandHelping className="h-5 w-5" />}
          Submit Help Request
        </Button>
      </form>
    </div>
  );
}
