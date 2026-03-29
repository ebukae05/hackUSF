const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { HandHelping, HeartHandshake, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

const HERO_IMAGE = 'https://media.base44.com/images/public/69c8d61e4c900fc320fad8c2/165acbe66_generated_00003015.png';

export default function HeroSection() {
  return (
    <section className="relative min-h-[85vh] flex items-center overflow-hidden">
      {/* Background image with overlay */}
      <div className="absolute inset-0">
        <img
          src={HERO_IMAGE}
          alt="Tampa Bay volunteers loading supplies at a pier during golden hour"
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-atlantic/95 via-atlantic/80 to-atlantic/50" />
        <div className="absolute inset-0 bg-gradient-to-t from-atlantic via-transparent to-transparent" />
      </div>

      {/* Topographic overlay pattern */}
      <div className="absolute inset-0 opacity-5">
        <svg className="w-full h-full" viewBox="0 0 800 600" preserveAspectRatio="none">
          <path d="M0,300 Q200,250 400,300 T800,280" fill="none" stroke="currentColor" strokeWidth="1" className="text-electric" />
          <path d="M0,320 Q200,270 400,320 T800,300" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-electric" />
          <path d="M0,340 Q200,290 400,340 T800,320" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-electric" />
        </svg>
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="max-w-2xl"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-electric/10 border border-electric/20 mb-6">
            <div className="w-2 h-2 rounded-full bg-electric animate-pulse" />
            <span className="text-xs font-medium text-electric tracking-wide">ACTIVE RELIEF OPERATIONS</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight tracking-tight">
            <span className="text-cloud-signal">Tampa Bay</span>
            <br />
            <span className="text-electric glow-cyan">Disaster Relief</span>
            <br />
            <span className="text-cloud-signal">Network</span>
          </h1>

          <p className="mt-6 text-lg text-cloud-signal/70 leading-relaxed max-w-xl">
            AI-powered matching that connects those in need with volunteers and resources — instantly.
            Serving Hillsborough, Pinellas, Manatee, and Pasco counties.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Link to="/request-help">
              <Button size="lg" variant="outline" className="w-full sm:w-auto border-electric/40 text-electric hover:bg-electric/10 hover:text-electric gap-2 h-13 px-8 text-base">
                <HandHelping className="h-5 w-5" />
                I Need Help
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/volunteer">
              <Button size="lg" className="w-full sm:w-auto bg-electric text-atlantic hover:bg-electric/90 font-bold gap-2 h-13 px-8 text-base">
                <HeartHandshake className="h-5 w-5" />
                I Can Help
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
