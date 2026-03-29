const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ArrowRight } from 'lucide-react';

const COMMUNITY_IMAGE = 'https://media.db.com/images/public/69c8d61e4c900fc320fad8c2/a2c58f5cd_generated_5726d5e7.png';

export default function CommunitySection() {
  return (
    <section className="py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <div className="relative rounded-2xl overflow-hidden">
              <img
                src={COMMUNITY_IMAGE}
                alt="Bird's eye view of Tampa Bay community cleanup after a storm"
                className="w-full h-80 object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-atlantic/60 to-transparent" />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3">Our Community</h2>
            <p className="text-3xl sm:text-4xl font-bold text-cloud-signal mb-6">
              Serving the Most Vulnerable — Every Time
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              ReliefLink was born from the devastating hurricane seasons that have impacted Tampa Bay. 
              We believe that in moments of crisis, technology should serve as a force multiplier for human compassion.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-8">
              Our AI prioritizes the most vulnerable communities first, ensuring equitable distribution of 
              resources across all four counties. Built by the community, for the community.
            </p>
            <Link to="/about">
              <Button variant="outline" className="border-electric/30 text-electric hover:bg-electric/10 gap-2">
                Learn More About Our Mission
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </div>
    </section>
  );
}