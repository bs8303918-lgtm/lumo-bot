import {
  BarChart3,
  Compass,
  DollarSign,
  LogOut,
  Menu,
  MessageSquarePlus,
  User,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import LumoLogo from './LumoLogo.jsx';

const NAV = [
  { id: 'chat', icon: MessageSquarePlus, label: 'Чат' },
  { id: 'catalog', icon: Compass, label: 'Каталог' },
  { id: 'team', icon: Users, label: 'Команда' },
  { id: 'pricing', icon: DollarSign, label: 'Тарифы' },
];

export default function AppSidebar({
  active,
  onChange,
  collapsed,
  onToggle,
  onNewChat,
  authed,
  displayName,
  onLogout,
  isAdmin,
}) {
  const navItems = isAdmin
    ? [...NAV, { id: 'traction', icon: BarChart3, label: 'Трекшн' }]
    : NAV;

  return (
    <aside
      className={`shrink-0 flex flex-col border-r border-neutral-200 bg-white transition-all duration-200 ${
        collapsed ? 'w-[68px]' : 'w-[220px]'
      }`}
    >
      <div className="h-14 flex items-center justify-between px-3 border-b border-neutral-200">
        {!collapsed && (
          <Link to="/" className="hover:opacity-80 transition-opacity">
            <LumoLogo size="sm" theme="light" />
          </Link>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="w-9 h-9 rounded-lg flex items-center justify-center text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
          aria-label="Меню"
        >
          <Menu size={18} />
        </button>
      </div>

      <nav className="flex-1 py-3 px-2 space-y-1">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
          title="Новый чат"
        >
          <MessageSquarePlus size={18} className="shrink-0" />
          {!collapsed && <span>Новый чат</span>}
        </button>

        {navItems.map(({ id, icon: Icon, label }) => {
          const isActive = active === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => onChange(id)}
              title={label}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-neutral-100 text-neutral-900 font-semibold'
                  : 'text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900'
              }`}
            >
              <Icon size={18} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </button>
          );
        })}
      </nav>

      <div className="p-2 border-t border-neutral-200 space-y-1">
        <div className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-neutral-500">
          <div className="w-7 h-7 rounded-full bg-neutral-100 flex items-center justify-center shrink-0">
            <User size={14} />
          </div>
          {!collapsed && <span className="truncate">{displayName}</span>}
        </div>
        {authed && !collapsed && (
          <button
            type="button"
            onClick={onLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
          >
            <LogOut size={16} />
            Выйти
          </button>
        )}
      </div>
    </aside>
  );
}
