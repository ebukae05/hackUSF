import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { HeartHandshake, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

const categories = [
  { value: 'shelter', label: 'Shelter Assistance' },
  { value: 'food_water', label: 'Food & Water Distribution' },
  { value: 'medical', label: 'Medical Support' },
  { value: 'transportation', label: 'Transportation / Boats' },
  { value: 'cleanup', label: 'Cleanup & Debris Removal' },
  { value: 'supplies', label: 'Supply Donations' },
  { value: 'other', label: 'Other' },
];

const counties = ['Hillsborough', 'Pinellas', 'Manatee', 'Pasco'];

export default function Volunteer() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '', category: '', description: '', availability: '',
    county: '', contact_phone: '', contact_email: '',
  });

  const update = (field, value) => setForm(prev => ({ ...prev, [field]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    toast.info('Volunteer intake is not exposed by the current backend. Use the operator dashboard to inspect current resource inventory and match decisions.');
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
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-electric/10 border border-electric/20 mb-4">
          <HeartHandshake className="h-3.5 w-3.5 text-electric" />
          <span className="text-xs font-medium text-electric">VOLUNTEER REGISTRATION</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-cloud-signal">Offer Your Help</h1>
        <p className="mt-2 text-muted-foreground">
          Register as a volunteer and we'll match you with people who need your specific skills.
        </p>
      </motion.div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
          <h2 className="text-sm font-semibold text-electric uppercase tracking-wider">About You</h2>

          <div className="space-y-2">
            <Label className="text-cloud-signal">Your Name / Organization *</Label>
            <Input
              placeholder="Full name or organization name"
              value={form.name}
              onChange={e => update('name', e.target.value)}
              required
              className="bg-background border-border text-cloud-signal"
            />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-cloud-signal">What can you help with? *</Label>
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

          <div className="space-y-2">
            <Label className="text-cloud-signal">Description</Label>
            <Textarea
              placeholder="Describe your skills, resources, or how you can help..."
              value={form.description}
              onChange={e => update('description', e.target.value)}
              rows={4}
              className="bg-background border-border text-cloud-signal"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-cloud-signal">Availability</Label>
            <Input
              placeholder="e.g., Weekends, Full-time, Evenings"
              value={form.availability}
              onChange={e => update('availability', e.target.value)}
              className="bg-background border-border text-cloud-signal"
            />
          </div>
        </div>

        <div className="rounded-2xl bg-card border border-border p-6 space-y-5">
          <h2 className="text-sm font-semibold text-electric uppercase tracking-wider">Contact Information</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-cloud-signal">Email *</Label>
              <Input
                type="email"
                placeholder="your@email.com"
                value={form.contact_email}
                onChange={e => update('contact_email', e.target.value)}
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
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full bg-electric text-atlantic hover:bg-electric/90 font-bold h-12 text-base gap-2"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <HeartHandshake className="h-5 w-5" />}
          Register as Volunteer
        </Button>
      </form>
    </div>
  );
}
