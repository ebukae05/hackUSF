import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users, Droplets, Home, Truck } from 'lucide-react';

const stats = [
  { icon: Users, label: 'Lives Impacted', target: 12847, suffix: '+', color: 'text-electric' },
  { icon: Droplets, label: 'Meals Served', target: 34200, suffix: '+', color: 'text-electric' },
  { icon: Home, label: 'Families Sheltered', target: 2156, suffix: '', color: 'text-electric' },
  { icon: Truck, label: 'Supplies Delivered', target: 8930, suffix: '+', color: 'text-electric' },
];

function AnimatedCounter({ target, suffix }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const duration = 2000;
    const steps = 60;
    const increment = target / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        setCount(target);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [target]);

  return (
    <span className="block w-full text-center text-3xl sm:text-4xl lg:text-5xl font-extrabold text-cloud-signal glow-cyan tabular-nums">
      {count.toLocaleString()}{suffix}
    </span>
  );
}

export default function ImpactStats() {
  return (
    <section className="py-20 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-atlantic/50 to-transparent" />
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-14"
        >
          <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3">Real-Time Impact</h2>
          <p className="text-3xl sm:text-4xl font-bold text-cloud-signal">
            Making a Difference Across Tampa Bay
          </p>
        </motion.div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="relative group"
            >
              <div className="flex h-full flex-col items-center justify-center p-6 sm:p-8 rounded-2xl bg-card border border-border hover:border-electric/30 transition-all duration-300 text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-electric/10 mb-4">
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <AnimatedCounter target={stat.target} suffix={stat.suffix} />
                <p className="mt-2 text-sm text-muted-foreground font-medium">{stat.label}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
