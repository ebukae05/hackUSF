import { motion } from 'framer-motion';
import { FileText, Cpu, Link2, CheckCircle } from 'lucide-react';

const steps = [
  {
    icon: FileText,
    title: 'Submit a Request',
    description: 'Whether you need help or want to volunteer, submit your details through our streamlined form.',
  },
  {
    icon: Cpu,
    title: 'AI Matching',
    description: 'Our intelligent engine analyzes location, skills, urgency, and availability to find the best match.',
  },
  {
    icon: Link2,
    title: 'Get Connected',
    description: 'Matched parties are instantly notified with contact details and coordination information.',
  },
  {
    icon: CheckCircle,
    title: 'Relief Delivered',
    description: 'Track progress in real-time as help reaches those who need it most across Tampa Bay.',
  },
];

export default function HowItWorks() {
  return (
    <section className="py-20 bg-card/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-14"
        >
          <h2 className="text-sm font-semibold text-electric uppercase tracking-widest mb-3">How It Works</h2>
          <p className="text-3xl sm:text-4xl font-bold text-cloud-signal">
            From Request to Relief in Minutes
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative"
            >
              <div className="p-6 rounded-2xl bg-card border border-border hover:border-electric/30 transition-all h-full">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-electric/10 flex items-center justify-center flex-shrink-0">
                    <step.icon className="h-5 w-5 text-electric" />
                  </div>
                  <span className="text-xs font-bold text-electric/50">0{i + 1}</span>
                </div>
                <h3 className="text-base font-semibold text-cloud-signal mb-2">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
              </div>
              {i < steps.length - 1 && (
                <div className="hidden lg:block absolute top-1/2 -right-3 w-6 border-t border-dashed border-electric/30" />
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}