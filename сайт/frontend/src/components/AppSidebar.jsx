import {
  BarChart3,
  Briefcase,
  Compass,
  DollarSign,
  Handshake,
  LogOut,
  Menu,
  MessageSquarePlus,
  User,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import LumoLogo from './LumoLogo.jsx';

const USER_NAV = [
  { id: 'chat', icon: MessageSquarePlus, label: 'Чат' },
  { id: 'catalog', icon: Compass, label: 'Каталог' },
  { id: 'mentor-access', icon: Handshake, label: 'Мои подачи' },
  { id: 'team', icon: Users, label: 'Команда' },
  { id: 'pricing', icon: DollarSign, label: 'Тарифы' },
];

const MENTOR_NAV = [
  { id: 'workspace', icon: Briefcase, label: 'Менторы' },
  { id: 'catalog', icon: Compass, label: 'Каталог' },
];

function InterfaceModeToggle({ mode, onChange, collapsed }) {
  return (
    <div
      className={`rounded-xl border border-violet-200 bg-violet-50/80 p-1 ${
        collapsed ? 'flex flex-col gap-1' : 'flex gap-1'
      }`}
      title="Режим интерфейса"
    >
      <button
        type="button"
        onClick={() => onChange('user')}
        className={`rounded-lg text-xs font-semibold transition-colors ${
          collapsed ? 'px-2 py-2' : 'flex-1 px-3 py-2'
        } ${mode === 'user' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-800'}`}
      >
        {collapsed ? '👤' : 'Студент'}
      </button>
      <button
        type="button"
        onClick={() => onChange('mentor')}
        className={`rounded-lg text-xs font-semibold transition-colors ${
          collapsed ? 'px-2 py-2' : 'flex-1 px-3 py-2'
        } ${mode === 'mentor' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-800'}`}
      >
        {collapsed ? '💼' : 'Ментор'}
      </button>
    </div>
  );
}

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
  userRole = 'student',
  interfaceMode = 'user',
  onInterfaceModeChange,
}) {
  const isMentorAccount = userRole === 'mentor';
  const mentorMode = interfaceMode === 'mentor' || isMentorAccount;
  const showMentorCrm = mentorMode && (isMentorAccount || isAdmin);
  const navItems = showMentorCrm ? [...MENTOR_NAV] : [...USER_NAV];

  if (isAdmin) {
    navItems.push({ id: 'traction', icon: BarChart3, label: 'Трекшн' });
  }

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

      {isAdmin && onInterfaceModeChange && (
        <div className={`px-2 pt-3 ${collapsed ? '' : ''}`}>
          <InterfaceModeToggle
            mode={interfaceMode}
            onChange={onInterfaceModeChange}
            collapsed={collapsed}
          />
          {!collapsed && mentorMode && (
            <p className="text-[10px] text-violet-600/80 px-1 mt-2 leading-snug">
              Режим ментора: дедлайны, подборки, оценка шансов
            </p>
          )}
        </div>
      )}

      <nav className="flex-1 py-3 px-2 space-y-1">
        {!mentorMode && (
          <button
            type="button"
            onClick={onNewChat}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
            title="Новый чат"
          >
            <MessageSquarePlus size={18} className="shrink-0" />
            {!collapsed && <span>Новый чат</span>}
          </button>
        )}

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
                  ? id === 'workspace'
                    ? 'bg-violet-100 text-violet-900 font-semibold'
                    : 'bg-neutral-100 text-neutral-900 font-semibold'
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
