import { NavLink, Outlet } from 'react-router-dom'

export function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">HX</span>
          <div>
            <strong>HexStrike</strong>
            <small>Report Console</small>
          </div>
        </div>
        <nav>
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/scan/new">New Scan</NavLink>
          <NavLink to="/reports">Reports</NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
