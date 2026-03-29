const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import { motion } from 'framer-motion';
import { Shield, Target, Users, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

const SUPPLIES_IMAGE = '/images/supplies-loading.svg';

const team = [
  { name: 'Ana Jaramillo', role: 'Co-Founder' },
  { name: 'Keilly Cespedes', role: 'Co-Founder' },
  { name: 'Shivaganesh Nagamandla', role: 'Co-Founder' },
  { name: 'Chukwuebuka Ezinwa', role: 'Co-Founder' },
];

const values = [
  {
    icon: Target,
    title: 'Vulnerability-First',
    description: 'Our AI prioritizes the most vulnerable communities, ensuring equitable resource distribution.',
  },
  {
    icon: Zap,
    title: 'Speed of Response',
    description: 'Minutes matter in disaster relief. Our matching engine connects help in real-time.',
  },
  {
    icon: Users,
    title: 'Community-Driven',
    description: 'Built by Tampa Bay residents who understand the unique challenges of our coastal region.',
  },
  {
    icon: Shield,
    title: 'Transparent Operations',
    description: 'Every match, every delivery, every impact metric is tracked and publicly visible.',
  },
];

export default function About() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-16"
      >
        <h1 className="text-4xl sm:text-5xl font-bold text-cloud-signal mb-4">
          About <span className="text-electric">ReliefLink</span>
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          AI agents that serve the most vulnerable communities first — every time.
        </p>
      </motion.div>

      {/* Mission */}
      <div className="grid lg:grid-cols-2 gap-12 items-center mb-20">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3">Our Mission</h2>
          <p className="text-2xl font-bold text-cloud-signal mb-6">
            Transforming disaster response through intelligent technology
          </p>
          <p className="text-muted-foreground leading-relaxed mb-4">
            ReliefLink was born from the devastating hurricane seasons that have impacted the Tampa Bay area. 
            We saw firsthand how disconnected relief efforts can be — volunteers searching for where to help, 
            while families in need couldn't find resources.
          </p>
          <p className="text-muted-foreground leading-relaxed">
            Our platform uses AI-powered matching to bridge this gap, creating an instantaneous connection 
            between those who need help and those who can provide it. We serve Hillsborough, Pinellas, 
            Manatee, and Pasco counties with a focus on reaching the most vulnerable first.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
        >
          <div className="rounded-2xl overflow-hidden">
            <img
              src={SUPPLIES_IMAGE}
              alt="Volunteers stacking emergency supply boxes at a Tampa relief center"
              className="w-full h-80 object-cover"
            />
          </div>
        </motion.div>
      </div>

      {/* Values */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-20"
      >
        <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3 text-center">Our Values</h2>
        <p className="text-3xl font-bold text-cloud-signal text-center mb-10">What Drives Us</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {values.map((value, i) => (
            <motion.div
              key={value.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="p-6 rounded-2xl bg-card border border-border hover:border-electric/30 transition-all"
            >
              <div className="w-10 h-10 rounded-xl bg-electric/10 flex items-center justify-center mb-4">
                <value.icon className="h-5 w-5 text-electric" />
              </div>
              <h3 className="text-base font-semibold text-cloud-signal mb-2">{value.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{value.description}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Team */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-20"
      >
        <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3 text-center">The Team</h2>
        <p className="text-3xl font-bold text-cloud-signal text-center mb-10">Built by Tampa Bay, for Tampa Bay</p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {team.map((member, i) => (
            <motion.div
              key={member.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="p-6 rounded-2xl bg-card border border-border text-center"
            >
              <div className="w-16 h-16 rounded-full bg-electric/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-xl font-bold text-electric">
                  {member.name.split(' ').map(n => n[0]).join('')}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-cloud-signal">{member.name}</h3>
              <p className="text-xs text-muted-foreground mt-1">{member.role}</p>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* CTA */}
      <div className="text-center py-10 px-6 rounded-2xl bg-card border border-border">
        <h2 className="text-2xl font-bold text-cloud-signal mb-3">Ready to Make a Difference?</h2>
        <p className="text-muted-foreground mb-6">Join our network of volunteers and help Tampa Bay recover stronger.</p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/volunteer">
            <Button className="bg-electric text-atlantic hover:bg-electric/90 font-bold">
              Become a Volunteer
            </Button>
          </Link>
          <Link to="/request-help">
            <Button variant="outline" className="border-electric/30 text-electric hover:bg-electric/10">
              Request Help
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
