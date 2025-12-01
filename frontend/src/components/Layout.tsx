import { Outlet, Link } from 'react-router-dom';

function Layout() {
  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <Link to="/" className="logo">
            📊 Historical Price Tracker
          </Link>
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
