import HeroSection from '../components/home/HeroSection';
import ImpactStats from '../components/home/ImpactStats';
import MatchingPreview from '../components/home/MatchingPreview';
import HowItWorks from '../components/home/HowItWorks';
import CommunitySection from '../components/home/CommunitySection';

export default function Home() {
  return (
    <div>
      <HeroSection />
      <ImpactStats />
      <MatchingPreview />
      <HowItWorks />
      <CommunitySection />
    </div>
  );
}