import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Check,
  ClipboardCopy,
  ExternalLink,
  FileDown,
  GripVertical,
  Loader2,
  Plus,
  Search,
  Sparkles,
  Trash2,
  User,
  Users,
  X,
} from 'lucide-react';
import { apiFetch, clearActiveRoom, getActiveRoomStudentId, setActiveRoom } from '../api.js';
import OpportunityCard from './OpportunityCard.jsx';
import { buildCatalogQuery, DEFAULT_CATALOG_FILTERS } from '../constants/catalogFilters.js';

const LOCAL_KANBAN_KEY = 'lumo-mentor-kanban-local';
const LOCAL_STUDENTS_KEY = 'lumo-mentor-students';
const ACTIVE_STUDENT_KEY = 'lumo-mentor-active-student';
const PERSONAL_DESK_ID = 'personal-desk';

function loadStudents() {
  try {
    const raw = localStorage.getItem(LOCAL_STUDENTS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {
    /* ignore */
  }
  return [{ id: 'student-default', name: 'Студент', profile: '' }];
}

function saveStudents(students) {
  localStorage.setItem(LOCAL_STUDENTS_KEY, JSON.stringify(students));
}

function loadActiveStudentId() {
  return localStorage.getItem(ACTIVE_STUDENT_KEY) || null;
}

function saveActiveStudentId(id) {
  if (id) localStorage.setItem(ACTIVE_STUDENT_KEY, id);
  else localStorage.removeItem(ACTIVE_STUDENT_KEY);
}

function mergeRoster(localStudents, roomStudents) {
  const personal = {
    id: PERSONAL_DESK_ID,
    name: 'Мой стол',
    profile: '',
    personal: true,
    fromApi: false,
  };
  const byKey = new Map([[PERSONAL_DESK_ID, personal]]);
  for (const room of roomStudents) {
    byKey.set(room.id, room);
  }
  for (const local of localStudents) {
    if (local.id === PERSONAL_DESK_ID) continue;
    if (local.fromApi) continue;
    const key = local.id || local.name.toLowerCase();
    if (!byKey.has(key)) byKey.set(key, local);
  }
  return Array.from(byKey.values());
}

function mergeStudentsFromApps(students, applications) {
  const byName = new Map(students.map((s) => [s.name.trim().toLowerCase(), s]));
  for (const app of applications) {
    const name = (app.studentName || '').trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (!byName.has(key)) {
      const entry = { id: `student-${key.replace(/\s+/g, '-')}`, name, profile: '' };
      byName.set(key, entry);
    }
  }
  return Array.from(byName.values());
}

function studentStats(applications, studentName) {
  const apps = applications.filter((a) => a.studentName === studentName);
  return {
    total: apps.length,
    todo: apps.filter((a) => a.status === 'todo').length,
    in_progress: apps.filter((a) => a.status === 'in_progress').length,
    submitted: apps.filter((a) => a.status === 'submitted').length,
  };
}

function loadLocalApplications() {
  try {
    const raw = localStorage.getItem(LOCAL_KANBAN_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveLocalApplications(items) {
  localStorage.setItem(LOCAL_KANBAN_KEY, JSON.stringify(items));
}

function isLocalApp(app) {
  return String(app.id).startsWith('local-');
}

function itemToKanbanOpportunity(item) {
  return {
    id: item.id,
    title: item.title,
    type: item.type,
    label: item.label,
    emoji: item.emoji,
    deadlineLabel: item.deadlineLabel || item.deadline || 'не указан',
    deadlineUrgent: Boolean(item.deadlineUrgent),
    country: item.country || 'Глобальная',
    applicationUrl: item.applicationUrl,
    description: item.description,
    sourceChannelName: item.sourceChannelName,
  };
}

function isWorkspaceApiMissing(err) {
  const msg = (err?.message || '').toLowerCase();
  return err?.status === 404 || msg.includes('not found') || msg.includes('http 404');
}

const TABS = [
  { id: 'kanban', label: 'Дедлайны' },
  { id: 'shortlist', label: 'Подборки' },
  { id: 'evaluator', label: 'Оценка шансов' },
];

const KANBAN_COLUMNS = [
  { id: 'todo', label: 'Нужно подать', tone: 'border-amber-200 bg-amber-50/60' },
  { id: 'in_progress', label: 'В процессе', tone: 'border-blue-200 bg-blue-50/60' },
  { id: 'submitted', label: 'Подано', tone: 'border-emerald-200 bg-emerald-50/60' },
];

function ScoreRing({ score }) {
  const color =
    score >= 70 ? 'text-emerald-600' : score >= 45 ? 'text-amber-600' : 'text-rose-600';
  return (
    <div className={`text-5xl font-bold tabular-nums ${color}`}>
      {score}
      <span className="text-2xl text-neutral-400">%</span>
    </div>
  );
}

function KanbanCard({ card, onMove, onDelete, showStudent, isDragging, onDragStart, onDragEnd }) {
  const opp = card.opportunity;
  const nextStatus = {
    todo: 'in_progress',
    in_progress: 'submitted',
    submitted: null,
  }[card.status];

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, card.id)}
      onDragEnd={onDragEnd}
      className={`rounded-xl border border-neutral-200 bg-white p-3 shadow-sm space-y-2 transition-opacity ${
        isDragging ? 'opacity-40 scale-[0.98]' : 'opacity-100'
      }`}
    >
      <div className="flex items-start gap-2">
        <div
          className="mt-0.5 text-neutral-300 hover:text-neutral-500 cursor-grab active:cursor-grabbing shrink-0"
          title="Перетащи в другую колонку"
        >
          <GripVertical size={16} />
        </div>
        <div className="flex items-start justify-between gap-2 flex-1 min-w-0">
          <div className="min-w-0">
            {showStudent && (
              <p className="text-xs font-medium text-violet-700 mb-0.5">{card.studentName}</p>
            )}
            <p className="text-sm font-semibold text-neutral-900 leading-snug">{opp.title}</p>
          </div>
          <span className="text-lg shrink-0">{opp.emoji}</span>
        </div>
      </div>
      <p className="text-xs text-neutral-500">
        {opp.label} · {opp.country || 'Глобальная'} · {opp.deadlineLabel}
        {opp.deadlineUrgent ? ' · срочно' : ''}
      </p>
      <div className="flex flex-wrap gap-1.5 pt-1">
        {nextStatus && (
          <button
            type="button"
            onClick={() => onMove(card.id, nextStatus)}
            className="text-xs px-2.5 py-1 rounded-full bg-neutral-900 text-white hover:bg-neutral-800"
          >
            → {KANBAN_COLUMNS.find((c) => c.id === nextStatus)?.label}
          </button>
        )}
        {card.status !== 'todo' && (
          <button
            type="button"
            onClick={() => onMove(card.id, 'todo')}
            className="text-xs px-2.5 py-1 rounded-full border border-neutral-200 text-neutral-600 hover:bg-neutral-50"
          >
            Назад
          </button>
        )}
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="text-xs px-2 py-1 rounded-full text-rose-600 hover:bg-rose-50 ml-auto"
          aria-label="Удалить"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

function KanbanColumn({
  col,
  cards,
  isDropTarget,
  showStudent,
  draggingCardId,
  onDragStart,
  onDragEnd,
  onDragEnter,
  onDragLeave,
  onDrop,
  onMove,
  onDelete,
}) {
  return (
    <div
      className={`rounded-2xl border p-3 min-h-[280px] transition-all ${col.tone} ${
        isDropTarget ? 'ring-2 ring-violet-400 ring-offset-2 border-violet-300' : ''
      }`}
      onDragEnter={(e) => {
        e.preventDefault();
        onDragEnter(col.id);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) onDragLeave();
      }}
      onDrop={(e) => {
        e.preventDefault();
        const cardId = e.dataTransfer.getData('text/plain');
        onDrop(cardId, col.id);
      }}
    >
      <div className="flex items-center justify-between mb-3 px-1">
        <h3 className="text-sm font-semibold text-neutral-800">{col.label}</h3>
        <span className="text-xs text-neutral-500">{cards.length}</span>
      </div>
      <div className="space-y-3 min-h-[180px]">
        {cards.map((card) => (
          <KanbanCard
            key={card.id}
            card={card}
            onMove={onMove}
            onDelete={onDelete}
            showStudent={showStudent}
            isDragging={draggingCardId === card.id}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
          />
        ))}
        {cards.length === 0 && (
          <p className="text-xs text-neutral-400 text-center py-8 border border-dashed border-neutral-200/80 rounded-xl">
            {isDropTarget ? 'Отпусти здесь' : 'Пусто'}
          </p>
        )}
      </div>
    </div>
  );
}

function StudentSwitcher({
  students,
  activeStudentId,
  applications,
  onSelect,
  onAdd,
  onRemove,
}) {
  const [draftName, setDraftName] = useState('');
  const [adding, setAdding] = useState(false);

  const handleAdd = () => {
    const name = draftName.trim();
    if (name.length < 2 || !onAdd) return;
    onAdd(name);
    setDraftName('');
    setAdding(false);
  };

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Users size={18} className="text-neutral-600" />
          <h2 className="text-sm font-semibold text-neutral-900">Студенты</h2>
        </div>
        {onAdd && (
          <button
            type="button"
            onClick={() => setAdding((v) => !v)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border border-neutral-200 hover:bg-neutral-50"
          >
            <Plus size={14} />
            Добавить
          </button>
        )}
      </div>

      {adding && onAdd && (
        <div className="flex gap-2">
          <input
            type="text"
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            placeholder="Имя студента"
            className="flex-1 px-3 py-2 rounded-xl border border-neutral-200 text-sm"
          />
          <button
            type="button"
            onClick={handleAdd}
            className="px-4 py-2 rounded-xl bg-neutral-900 text-white text-sm font-medium"
          >
            OK
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onSelect(null)}
          className={`inline-flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium border transition-colors ${
            activeStudentId === null
              ? 'bg-violet-100 border-violet-300 text-violet-900'
              : 'bg-white border-neutral-200 text-neutral-600 hover:border-neutral-300'
          }`}
        >
          <Users size={14} />
          Все
          <span className="text-xs opacity-70">{applications.length}</span>
        </button>

        {students.map((student) => {
          const stats =
            student.id === PERSONAL_DESK_ID
              ? {
                  total: applications.length,
                  todo: applications.filter((a) => a.status === 'todo').length,
                  in_progress: applications.filter((a) => a.status === 'in_progress').length,
                  submitted: applications.filter((a) => a.status === 'submitted').length,
                }
              : studentStats(applications, student.name);
          const isActive = activeStudentId === student.id;
          return (
            <div key={student.id} className="relative group">
              <button
                type="button"
                onClick={() => onSelect(student.id)}
                className={`inline-flex items-center gap-2 pl-3 pr-8 py-2 rounded-xl text-sm font-medium border transition-colors ${
                  isActive
                    ? 'bg-violet-100 border-violet-300 text-violet-900'
                    : 'bg-white border-neutral-200 text-neutral-600 hover:border-neutral-300'
                }`}
              >
                <User size={14} />
                <span className="max-w-[120px] truncate">
                  {student.fromApi ? `🔗 ${student.name}` : student.name}
                </span>
                <span className="text-[10px] tabular-nums opacity-80">
                  {stats.todo}/{stats.in_progress}/{stats.submitted}
                </span>
              </button>
              {onRemove && !student.fromApi && student.id !== PERSONAL_DESK_ID && (
                <button
                  type="button"
                  onClick={() => onRemove(student.id)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full flex items-center justify-center text-neutral-400 hover:text-rose-600 hover:bg-rose-50 opacity-0 group-hover:opacity-100 transition-opacity"
                  aria-label={`Удалить ${student.name}`}
                >
                  <X size={12} />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {activeStudentId && (
        <p className="text-xs text-neutral-500">
          Показана доска выбранного студента. Программы добавляются только ему.
        </p>
      )}
    </div>
  );
}

export default function MentorWorkspaceView({ authed, profile, onNeedsAuth, onOpenItem }) {
  const [tab, setTab] = useState('kanban');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [applications, setApplications] = useState([]);
  const [shortlists, setShortlists] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [students, setStudents] = useState(loadStudents);
  const [activeStudentId, setActiveStudentId] = useState(() => {
    const saved = loadActiveStudentId();
    const roster = loadStudents();
    if (saved && roster.some((s) => s.id === saved)) return saved;
    return roster[0]?.id ?? null;
  });

  const activeStudent = useMemo(
    () => students.find((s) => s.id === activeStudentId) || null,
    [students, activeStudentId],
  );
  const activeStudentName = activeStudent?.name || 'Студент';

  const [shortlistTitle, setShortlistTitle] = useState('Персональная подборка');
  const [agencyName, setAgencyName] = useState('Lumo Agency');
  const [selectedIds, setSelectedIds] = useState([]);
  const [creatingShortlist, setCreatingShortlist] = useState(false);
  const [copiedSlug, setCopiedSlug] = useState(null);

  const [evalCatalogId, setEvalCatalogId] = useState(null);
  const [evalProfile, setEvalProfile] = useState('');
  const [evalResult, setEvalResult] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const [addingId, setAddingId] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [useLocalKanban, setUseLocalKanban] = useState(false);
  const [useApiRooms, setUseApiRooms] = useState(false);
  const [mentorSubActive, setMentorSubActive] = useState(false);
  const [draggingCardId, setDraggingCardId] = useState(null);
  const [dropTargetStatus, setDropTargetStatus] = useState(null);

  const loadWorkspace = useCallback(async () => {
    if (!authed) return;
    setLoading(true);
    setError(null);
    try {
      let apiRooms = [];
      let mentorPaid = Boolean(profile?.subscription?.isActive || profile?.hasAiAccess);
      if (profile?.role === 'mentor') {
        try {
          const roomsData = await apiFetch('/rooms/as-mentor');
          apiRooms = roomsData.rooms ?? [];
          mentorPaid = Boolean(roomsData.mentorSubscriptionActive ?? mentorPaid);
        } catch {
          apiRooms = [];
        }
        setUseApiRooms(true);
        setMentorSubActive(mentorPaid);
      }

      const roomStudents = apiRooms.map((room) => ({
        id: `room-${room.studentId}`,
        studentId: room.studentId,
        name: room.studentName || 'Студент',
        profile: '',
        canSearch: room.canSearch,
        fromApi: true,
      }));

      const appsData = await apiFetch('/workspace/applications');
      const apps = appsData.items ?? [];
      setApplications(apps);

      setStudents((prev) => {
        const local = profile?.role === 'mentor' ? loadStudents() : prev;
        let merged = mergeRoster(local, roomStudents);
        merged = mergeStudentsFromApps(merged, apps);
        saveStudents(merged.filter((s) => !s.fromApi && s.id !== PERSONAL_DESK_ID));
        return merged;
      });

      const saved = loadActiveStudentId();
      const rosterAfter = mergeStudentsFromApps(
        mergeRoster(loadStudents(), roomStudents),
        apps,
      );
      const savedStudent = rosterAfter.find((s) => s.id === saved);
      const savedRoomId = getActiveRoomStudentId();
      const savedRoomStudent = rosterAfter.find((s) => s.studentId === savedRoomId);
      const pick =
        savedStudent ||
        savedRoomStudent ||
        rosterAfter.find((s) => s.id === PERSONAL_DESK_ID) ||
        rosterAfter[0];
      if (pick) {
        setActiveStudentId(pick.id);
        saveActiveStudentId(pick.id);
        if (pick.studentId && pick.fromApi) setActiveRoom(pick.studentId, pick.name);
        else clearActiveRoom();
      }
      setUseLocalKanban(false);
      localStorage.removeItem(LOCAL_KANBAN_KEY);
      try {
        const listsData = await apiFetch('/workspace/shortlists');
        setShortlists(listsData.items ?? []);
      } catch {
        setShortlists([]);
      }
    } catch (err) {
      if (isWorkspaceApiMissing(err)) {
        const localApps = loadLocalApplications();
        setApplications(localApps);
        setStudents((prev) => {
          const merged = mergeStudentsFromApps(prev, localApps);
          saveStudents(merged);
          return merged;
        });
        setShortlists([]);
        setUseLocalKanban(true);
        if (localApps.length > 0) {
          setError('Сервер ещё без API менторов — доска сохранена локально. Задеплой lumo-bot на Railway.');
        }
      } else if (err.needsAuth) {
        onNeedsAuth();
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }, [authed, onNeedsAuth, profile?.role, profile?.subscription?.isActive, profile?.hasAiAccess]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  useEffect(() => {
    if (activeStudent?.profile && tab === 'evaluator') {
      setEvalProfile(activeStudent.profile);
    } else if (!activeStudent && profile?.interestQuery && !evalProfile) {
      setEvalProfile(profile.interestQuery);
    }
  }, [activeStudent, profile?.interestQuery, tab, evalProfile]);

  const filteredApplications = useMemo(() => {
    if (!activeStudent || activeStudent.id === PERSONAL_DESK_ID) return applications;
    return applications.filter((a) => a.studentName === activeStudent.name);
  }, [applications, activeStudent]);

  const isRoomMode = Boolean(activeStudent?.fromApi && activeStudent?.studentId);
  const isPersonalDesk = activeStudent?.id === PERSONAL_DESK_ID || !isRoomMode;
  const canSearchHere = isRoomMode
    ? Boolean(activeStudent?.canSearch)
    : Boolean(mentorSubActive || profile?.subscription?.isActive || profile?.hasAiAccess || profile?.isAdmin);

  const grouped = useMemo(() => {
    const map = { todo: [], in_progress: [], submitted: [] };
    for (const app of filteredApplications) {
      if (map[app.status]) map[app.status].push(app);
    }
    return map;
  }, [filteredApplications]);

  const selectStudent = (id) => {
    setActiveStudentId(id);
    saveActiveStudentId(id);
    setEvalResult(null);
    if (id) {
      const student = students.find((s) => s.id === id);
      if (student?.profile) setEvalProfile(student.profile);
      if (student?.studentId && student?.fromApi) {
        setActiveRoom(student.studentId, student.name);
      } else {
        clearActiveRoom();
      }
    } else {
      clearActiveRoom();
    }
  };

  const addStudent = (name) => {
    const trimmed = name.trim();
    if (trimmed.length < 2) return;
    const exists = students.some((s) => s.name.toLowerCase() === trimmed.toLowerCase());
    if (exists) {
      setError('Студент с таким именем уже есть');
      return;
    }
    const student = { id: `student-${Date.now()}`, name: trimmed, profile: '' };
    setStudents((prev) => {
      const next = [...prev, student];
      saveStudents(next.filter((s) => !s.fromApi && s.id !== PERSONAL_DESK_ID));
      return next;
    });
    selectStudent(student.id);
    setSuccessMessage(`Студент «${trimmed}» добавлен`);
  };

  const removeStudent = (id) => {
    const student = students.find((s) => s.id === id);
    if (!student || student.fromApi || student.id === PERSONAL_DESK_ID) return;
    const next = students.filter((s) => s.id !== id);
    setStudents(next);
    saveStudents(next);
    if (activeStudentId === id) selectStudent(null);
    setSuccessMessage(`«${student.name}» убран из списка. Его программы остались на доске «Все».`);
  };

  const updateStudentProfile = (profileText) => {
    setEvalProfile(profileText);
    if (!activeStudentId) return;
    const next = students.map((s) =>
      s.id === activeStudentId ? { ...s, profile: profileText } : s,
    );
    setStudents(next);
    saveStudents(next);
  };

  const searchCatalog = async () => {
    const q = searchQuery.trim();
    if (!q) return;
    if (!activeStudent) {
      setError('Выбери «Мой стол» или студента');
      return;
    }
    if (isRoomMode && !activeStudent.canSearch) {
      setError(
        'Подписка студента неактивна — в этой комнате поиск недоступен. Переключись на «Мой стол».',
      );
      return;
    }
    if (isPersonalDesk && !canSearchHere) {
      setError('Нужна подписка ментора для поиска в личном кабинете');
      return;
    }
    const roomStudentId = isRoomMode ? activeStudent.studentId : null;
    setSearching(true);
    setError(null);
    setSuccessMessage(null);
    try {
      let items = [];
      if (q.length >= 3) {
        try {
          const match = await apiFetch('/lumo/match', {
            method: 'POST',
            body: JSON.stringify({ query: q, limit: 9, saveInterest: false }),
            roomStudentId,
          });
          items = match.items ?? [];
        } catch {
          items = [];
        }
      }
      if (items.length === 0) {
        const qs = buildCatalogQuery({
          query: q,
          types: DEFAULT_CATALOG_FILTERS.types,
          sort: DEFAULT_CATALOG_FILTERS.sort,
          cashPrize: DEFAULT_CATALOG_FILTERS.cashPrize,
          pageSize: 9,
        });
        const data = await apiFetch(`/lumo/opportunities?${qs}`, { roomStudentId });
        items = data.items ?? [];
      }
      setSearchResults(items);
      if (items.length === 0) {
        setError('Ничего не найдено — попробуй другой запрос, например «гранты для стартапов»');
      }
    } catch (err) {
      if (err.needsAuth) onNeedsAuth();
      setError(err.message);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const addLocalToKanban = (catalogId, item) => {
    const name = activeStudentName;
    const existing = applications.find(
      (a) => a.catalogId === catalogId && a.studentName === name,
    );
    if (existing) {
      setSuccessMessage(`«${item.title}» уже на доске для ${name}`);
      return existing;
    }
    const app = {
      id: `local-${Date.now()}-${catalogId}`,
      catalogId,
      studentName: name,
      status: 'todo',
      statusLabel: 'Нужно подать',
      opportunity: itemToKanbanOpportunity(item),
      local: true,
    };
    const next = [app, ...applications];
    setApplications(next);
    saveLocalApplications(next);
    setUseLocalKanban(true);
    return app;
  };

  const addToKanban = async (item) => {
    const catalogId = item.id;
    setAddingId(catalogId);
    setError(null);
    setSuccessMessage(null);
    try {
      const data = await apiFetch('/workspace/applications', {
        method: 'POST',
        body: JSON.stringify({
          catalogId,
          studentName: activeStudentName,
          studentUserId: activeStudent?.studentId ?? null,
          status: 'todo',
        }),
      });
      setApplications((prev) => {
        const filtered = prev.filter((a) => a.id !== data.application.id);
        return [data.application, ...filtered];
      });
      setUseLocalKanban(false);
      setSuccessMessage(`Добавлено на доску: ${item.title}`);
    } catch (err) {
      if (isWorkspaceApiMissing(err) || useLocalKanban) {
        addLocalToKanban(catalogId, item);
        setSuccessMessage(`Добавлено локально: ${item.title}`);
      } else if (err.needsAuth) {
        onNeedsAuth();
      } else {
        setError(err.message || 'Не удалось добавить на доску');
      }
    } finally {
      setAddingId(null);
    }
  };

  const moveCard = async (appId, status) => {
    const card = applications.find((a) => a.id === appId || String(a.id) === String(appId));
    if (!card || card.status === status) return;

    if (isLocalApp(card)) {
      const next = applications.map((a) =>
        a.id === card.id
          ? { ...a, status, statusLabel: KANBAN_COLUMNS.find((c) => c.id === status)?.label || status }
          : a,
      );
      setApplications(next);
      saveLocalApplications(next);
      return;
    }
    try {
      const data = await apiFetch(`/workspace/applications/${card.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      setApplications((prev) => prev.map((a) => (a.id === card.id ? data.application : a)));
    } catch (err) {
      if (isWorkspaceApiMissing(err) || useLocalKanban) {
        const next = applications.map((a) =>
          a.id === card.id
            ? { ...a, status, statusLabel: KANBAN_COLUMNS.find((c) => c.id === status)?.label || status }
            : a,
        );
        setApplications(next);
        saveLocalApplications(next);
        setUseLocalKanban(true);
      } else {
        setError(err.message);
      }
    }
  };

  const handleDragStart = (e, cardId) => {
    setDraggingCardId(cardId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(cardId));
  };

  const handleDragEnd = () => {
    setDraggingCardId(null);
    setDropTargetStatus(null);
  };

  const handleKanbanDrop = (cardIdRaw, status) => {
    setDraggingCardId(null);
    setDropTargetStatus(null);
    if (!cardIdRaw) return;
    const card = applications.find((a) => String(a.id) === String(cardIdRaw));
    if (card) moveCard(card.id, status);
  };

  const deleteCard = async (appId) => {
    if (isLocalApp({ id: appId })) {
      const next = applications.filter((a) => a.id !== appId);
      setApplications(next);
      saveLocalApplications(next);
      setSelectedIds((prev) => {
        const card = applications.find((a) => a.id === appId);
        return card ? prev.filter((id) => id !== card.catalogId) : prev;
      });
      return;
    }
    try {
      await apiFetch(`/workspace/applications/${appId}`, { method: 'DELETE' });
      setApplications((prev) => prev.filter((a) => a.id !== appId));
      setSelectedIds((prev) => {
        const card = applications.find((a) => a.id === appId);
        return card ? prev.filter((id) => id !== card.catalogId) : prev;
      });
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleSelect = (catalogId) => {
    setSelectedIds((prev) =>
      prev.includes(catalogId) ? prev.filter((id) => id !== catalogId) : [...prev, catalogId],
    );
  };

  const createShortlist = async () => {
    const ids = selectedIds.length
      ? selectedIds
      : filteredApplications.map((a) => a.catalogId).filter((id, i, arr) => arr.indexOf(id) === i);
    if (!ids.length) {
      setError('Добавьте программы на доску или выберите из списка');
      return;
    }
    setCreatingShortlist(true);
    setError(null);
    try {
      const data = await apiFetch('/workspace/shortlists', {
        method: 'POST',
        body: JSON.stringify({
          title: shortlistTitle.trim(),
          agencyName: agencyName.trim(),
          catalogIds: ids,
        }),
      });
      setShortlists((prev) => [data.shortlist, ...prev]);
      setTab('shortlist');
    } catch (err) {
      setError(err.message);
    } finally {
      setCreatingShortlist(false);
    }
  };

  const copyShareLink = async (slug) => {
    const url = `${window.location.origin}/shortlist/${slug}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedSlug(slug);
      setTimeout(() => setCopiedSlug(null), 2000);
    } catch {
      window.prompt('Ссылка на подборку:', url);
    }
  };

  const runEvaluation = async () => {
    if (!evalCatalogId) {
      setError('Выберите программу для оценки');
      return;
    }
    setEvaluating(true);
    setError(null);
    try {
      const data = await apiFetch('/workspace/evaluate', {
        method: 'POST',
        body: JSON.stringify({
          catalogId: evalCatalogId,
          studentProfile: evalProfile,
        }),
      });
      setEvalResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setEvaluating(false);
    }
  };

  if (!authed) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <BarChart3 size={40} className="text-neutral-300 mb-4" />
        <h1 className="text-xl font-semibold mb-2">Для менторов</h1>
        <p className="text-muted-foreground mb-6 max-w-md text-sm">
          Канбан дедлайнов, подборки для клиентов и ИИ-оценка шансов — в одном окне
        </p>
        <button
          type="button"
          onClick={onNeedsAuth}
          className="px-5 py-2.5 rounded-full bg-foreground text-background text-sm font-semibold"
        >
          Войти
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 md:py-8">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-1">CRM для агентств</p>
            <h1 className="text-2xl font-bold text-neutral-900">Рабочее место ментора</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Личный CRM + комнаты студентов: канбан, подборки, поиск (твоя подписка или подписка студента)
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  tab === item.id
                    ? 'bg-neutral-900 text-white'
                    : 'bg-white border border-neutral-200 text-neutral-600 hover:border-neutral-300'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <p className="text-sm text-rose-600 bg-rose-50 border border-rose-100 rounded-xl px-4 py-3">{error}</p>
        )}
        {successMessage && (
          <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-3">
            {successMessage}
          </p>
        )}

        {useApiRooms && activeStudent && (
          <div
            className={`rounded-xl border px-4 py-3 text-sm ${
              isRoomMode
                ? 'border-violet-200 bg-violet-50 text-violet-900'
                : 'border-sky-200 bg-sky-50 text-sky-900'
            }`}
          >
            {isRoomMode ? (
              <>
                Комната студента <strong>{activeStudent.name}</strong> — поиск по его подписке
                {!activeStudent.canSearch && (
                  <span className="block text-violet-700/90 mt-1 text-xs">
                    Подписка студента неактивна. Переключись на «Мой стол» для поиска по твоей подписке.
                  </span>
                )}
              </>
            ) : (
              <>
                <strong>Мой стол</strong> — личный CRM: свои студенты, канбан и поиск по подписке ментора
                {!canSearchHere && (
                  <span className="block mt-1 text-xs opacity-90">
                    Оформи подписку ментора, чтобы искать конкурсы в личном кабинете
                  </span>
                )}
              </>
            )}
          </div>
        )}

        {tab === 'kanban' && (
          <div className="space-y-5">
            <StudentSwitcher
              students={students}
              activeStudentId={activeStudentId}
              applications={applications}
              onSelect={selectStudent}
              onAdd={addStudent}
              onRemove={removeStudent}
            />

            <div className="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm space-y-3">
              <p className="text-sm font-medium text-neutral-800">
                Добавить программу на доску
                {activeStudent ? (
                  <span className="text-violet-700"> — {activeStudent.name}</span>
                ) : (
                  <span className="text-neutral-400"> — выбери студента сверху</span>
                )}
              </p>
              <div className="relative">
                <Search size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && searchCatalog()}
                  placeholder="Поиск конкурса или гранта…"
                  disabled={!activeStudent}
                  className="w-full px-4 py-3 pr-11 rounded-xl border border-neutral-200 text-sm disabled:bg-neutral-50 disabled:text-neutral-400"
                />
              </div>
              <button
                type="button"
                onClick={searchCatalog}
                disabled={searching || !activeStudent}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-60"
              >
                {searching ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                Найти программы
              </button>
              {searchResults.length > 0 && (
                <div className="border-t border-neutral-100 pt-4 space-y-3">
                  <p className="text-sm text-neutral-500">
                    Найдено {searchResults.length} — добавь на доску для «{activeStudentName}»
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {searchResults.map((item) => (
                      <OpportunityCard
                        key={item.id}
                        item={item}
                        onOpen={onOpenItem}
                        primaryAction={{
                          label: 'На доску',
                          loading: addingId === item.id,
                          onClick: () => addToKanban(item),
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {loading ? (
              <p className="text-center text-neutral-400 py-12">Загрузка…</p>
            ) : (
              <>
                <div className="flex items-center justify-between px-1">
                  <h3 className="text-sm font-semibold text-neutral-800">
                    {activeStudent
                      ? `Процесс: ${activeStudent.name}`
                      : 'Все студенты — общая доска'}
                  </h3>
                  {activeStudent && (
                    <span className="text-xs text-neutral-500">
                      {filteredApplications.length} программ · {studentStats(applications, activeStudent.name).submitted} подано
                    </span>
                  )}
                </div>
                <p className="text-xs text-neutral-400 px-1">Перетащи карточку мышкой между колонками или используй кнопки на карточке</p>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {KANBAN_COLUMNS.map((col) => (
                    <KanbanColumn
                      key={col.id}
                      col={col}
                      cards={grouped[col.id]}
                      isDropTarget={dropTargetStatus === col.id && draggingCardId !== null}
                      showStudent={!activeStudent}
                      draggingCardId={draggingCardId}
                      onDragStart={handleDragStart}
                      onDragEnd={handleDragEnd}
                      onDragEnter={setDropTargetStatus}
                      onDragLeave={() => setDropTargetStatus(null)}
                      onDrop={handleKanbanDrop}
                      onMove={moveCard}
                      onDelete={deleteCard}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {tab === 'shortlist' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <FileDown size={18} className="text-neutral-700" />
                <h2 className="font-semibold text-neutral-900">Создать подборку за 1 клик</h2>
              </div>
              <p className="text-sm text-neutral-500">
                Выбери программы с доски или отметь ниже — Lumo соберёт брендированную страницу для клиента.
              </p>
              <input
                type="text"
                value={shortlistTitle}
                onChange={(e) => setShortlistTitle(e.target.value)}
                placeholder="Название подборки"
                className="w-full px-4 py-3 rounded-xl border border-neutral-200 text-sm"
              />
              <input
                type="text"
                value={agencyName}
                onChange={(e) => setAgencyName(e.target.value)}
                placeholder="Название агентства"
                className="w-full px-4 py-3 rounded-xl border border-neutral-200 text-sm"
              />
              <div className="max-h-48 overflow-y-auto space-y-2 border border-neutral-100 rounded-xl p-3">
                {filteredApplications.length === 0 ? (
                  <p className="text-xs text-neutral-400">Сначала добавьте программы на канбан-доску</p>
                ) : (
                  filteredApplications.map((app) => (
                    <label key={app.id} className="flex items-start gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(app.catalogId)}
                        onChange={() => toggleSelect(app.catalogId)}
                        className="mt-1"
                      />
                      <span>
                        <span className="font-medium">{app.opportunity.title}</span>
                        <span className="block text-xs text-neutral-500">{app.studentName}</span>
                      </span>
                    </label>
                  ))
                )}
              </div>
              <button
                type="button"
                onClick={createShortlist}
                disabled={creatingShortlist}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-neutral-900 text-white text-sm font-semibold disabled:opacity-60"
              >
                {creatingShortlist ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                Сгенерировать подборку
              </button>
            </div>

            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm space-y-3">
              <h2 className="font-semibold text-neutral-900">Ваши подборки</h2>
              {shortlists.length === 0 ? (
                <p className="text-sm text-neutral-400 py-8 text-center">Пока нет подборок</p>
              ) : (
                shortlists.map((list) => (
                  <div
                    key={list.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl border border-neutral-100"
                  >
                    <div>
                      <p className="font-medium text-sm">{list.title}</p>
                      <p className="text-xs text-neutral-500">{list.agencyName}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <a
                        href={`/shortlist/${list.slug}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border border-neutral-200 hover:bg-neutral-50"
                      >
                        <ExternalLink size={14} />
                        Открыть
                      </a>
                      <button
                        type="button"
                        onClick={() => copyShareLink(list.slug)}
                        className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded-full bg-neutral-900 text-white"
                      >
                        {copiedSlug === list.slug ? <Check size={14} /> : <ClipboardCopy size={14} />}
                        {copiedSlug === list.slug ? 'Скопировано' : 'Ссылка'}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {tab === 'evaluator' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2">
                <Sparkles size={18} className="text-neutral-700" />
                <h2 className="font-semibold text-neutral-900">Profile Evaluator</h2>
              </div>
              <p className="text-sm text-neutral-500">
                ИИ сопоставит достижения студента с требованиями программы и покажет % шансов.
                {activeStudent ? ` Профиль: ${activeStudent.name}.` : ' Выбери студента на вкладке Дедлайны.'}
              </p>
              <textarea
                value={evalProfile}
                onChange={(e) => updateStudentProfile(e.target.value)}
                rows={6}
                placeholder="Оценки, проекты, олимпиады, волонтёрство, цели…"
                className="w-full px-4 py-3 rounded-xl border border-neutral-200 text-sm resize-y"
              />
              <div className="space-y-2 max-h-56 overflow-y-auto border border-neutral-100 rounded-xl p-3">
                {filteredApplications.length === 0 ? (
                  <p className="text-xs text-neutral-400">Добавьте программы на канбан, чтобы оценить</p>
                ) : (
                  filteredApplications.map((app) => (
                    <label key={app.id} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="radio"
                        name="eval-program"
                        checked={evalCatalogId === app.catalogId}
                        onChange={() => setEvalCatalogId(app.catalogId)}
                      />
                      <span className="truncate">{app.opportunity.title}</span>
                    </label>
                  ))
                )}
              </div>
              <button
                type="button"
                onClick={runEvaluation}
                disabled={evaluating}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-neutral-900 text-white text-sm font-semibold disabled:opacity-60"
              >
                {evaluating ? <Loader2 size={16} className="animate-spin" /> : <BarChart3 size={16} />}
                Оценить шансы
              </button>
            </div>

            <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
              {!evalResult ? (
                <div className="h-full flex flex-col items-center justify-center text-center py-16 text-neutral-400">
                  <BarChart3 size={36} className="mb-3 opacity-40" />
                  <p className="text-sm">Результат оценки появится здесь</p>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="text-center">
                    <ScoreRing score={evalResult.score} />
                    <p className="text-sm font-medium text-neutral-800 mt-2">{evalResult.opportunityTitle}</p>
                    <p className="text-sm text-neutral-500 mt-3 leading-relaxed">{evalResult.verdict}</p>
                  </div>
                  {evalResult.strengths?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700 mb-2">Сильные стороны</p>
                      <ul className="space-y-1">
                        {evalResult.strengths.map((item) => (
                          <li key={item} className="text-sm text-neutral-700 flex gap-2">
                            <span className="text-emerald-500">✓</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {evalResult.gaps?.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-2">Чего не хватает</p>
                      <ul className="space-y-1">
                        {evalResult.gaps.map((item) => (
                          <li key={item} className="text-sm text-neutral-700 flex gap-2">
                            <span className="text-amber-500">→</span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {evalResult.catalogId && onOpenItem && (
                    <button
                      type="button"
                      onClick={() => onOpenItem({ id: evalResult.catalogId })}
                      className="text-sm text-neutral-600 underline hover:text-neutral-900"
                    >
                      Открыть карточку программы
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
