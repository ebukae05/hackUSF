import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import StatusTicker from './StatusTicker';
import Footer from './Footer';

export default function Layout() {
  return (
    <div className="min-h-screen bg-background font-inter">
      <Navbar />
      <StatusTicker />
      <main className="pt-24">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}