// Sticky Note & Calendar - Frontend Application Logic

const PASTEL_THEMES = ['yellow', 'blue', 'green', 'orange', 'purple'];

// State
let notes = [];
let highestZIndex = 100;
let activeSearchQuery = '';
let activeDateFilter = null; // null = all, 'YYYY-MM-DD'
let calendarCurrentDate = new Date();
let selectedCalendarDate = new Date().toISOString().split('T')[0];
let isDraggingNote = false;
let isResizingNote = false;

// DOM Elements
const workspace = document.getElementById('workspace');
const notesContainer = document.getElementById('notesContainer');
const emptyState = document.getElementById('emptyState');
const newNoteBtn = document.getElementById('newNoteBtn');
const emptyNewBtn = document.getElementById('emptyNewBtn');
const toggleCalendarBtn = document.getElementById('toggleCalendarBtn');
const closeCalendarBtn = document.getElementById('closeCalendarBtn');
const calendarSidebar = document.getElementById('calendarSidebar');
const alignNotesBtn = document.getElementById('alignNotesBtn');
const themeToggleBtn = document.getElementById('themeToggleBtn');
const searchInput = document.getElementById('searchInput');
const clearSearchBtn = document.getElementById('clearSearchBtn');
const filterAllBtn = document.getElementById('filterAllBtn');
const filterTodayBtn = document.getElementById('filterTodayBtn');
const headerDateFilter = document.getElementById('headerDateFilter');
const todayDateStr = document.getElementById('todayDateStr');
const noteCountDisplay = document.getElementById('noteCountDisplay');
const syncStatus = document.getElementById('syncStatus');
const toggleVisibilityBtn = document.getElementById('toggleVisibilityBtn');
const visibilityText = document.getElementById('visibilityText');
const dockWidget = document.getElementById('dockWidget');
const dockCountText = document.getElementById('dockCountText');
let minimizedNoteIds = new Set();

// Calendar Elements
const calPrevMonthBtn = document.getElementById('calPrevMonthBtn');
const calNextMonthBtn = document.getElementById('calNextMonthBtn');
const calCurrentMonth = document.getElementById('calCurrentMonth');
const calendarGrid = document.getElementById('calendarGrid');
const selectedDateTitle = document.getElementById('selectedDateTitle');
const selectedDateNotesList = document.getElementById('selectedDateNotesList');
const addNoteForSelectedDateBtn = document.getElementById('addNoteForSelectedDateBtn');

// Helper: Format today's date
function getTodayIsoString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Initializer
async function initApp() {
  const todayStr = getTodayIsoString();
  todayDateStr.textContent = todayStr.slice(5); // 'MM-DD'
  
  // Restore theme
  if (localStorage.getItem('sticky_theme') === 'dark') {
    document.body.classList.add('dark-mode');
    document.getElementById('themeIcon').textContent = '☀️';
  }

  // Setup Event Listeners
  setupEventListeners();

  // Load Notes
  await loadNotes();

  // Render Calendar
  renderCalendar();
}

// Event Listeners Setup
function setupEventListeners() {
  newNoteBtn.addEventListener('click', () => createNewNote());
  emptyNewBtn.addEventListener('click', () => createNewNote());

  toggleCalendarBtn.addEventListener('click', () => {
    calendarSidebar.classList.toggle('open');
    if (calendarSidebar.classList.contains('open')) {
      renderCalendar();
    }
  });

  closeCalendarBtn.addEventListener('click', () => {
    calendarSidebar.classList.remove('open');
  });

  alignNotesBtn.addEventListener('click', autoAlignNotes);

  if (toggleVisibilityBtn) {
    toggleVisibilityBtn.addEventListener('click', toggleAllNotesVisibility);
  }

  if (dockWidget) {
    dockWidget.addEventListener('click', restoreAllNotes);
  }

  themeToggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    document.getElementById('themeIcon').textContent = isDark ? '☀️' : '🌓';
    localStorage.setItem('sticky_theme', isDark ? 'dark' : 'light');
  });

  // Search
  searchInput.addEventListener('input', (e) => {
    activeSearchQuery = e.target.value.trim().toLowerCase();
    filterNotesDisplay();
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    activeSearchQuery = '';
    filterNotesDisplay();
  });

  // Date Filters
  filterAllBtn.addEventListener('click', () => {
    setActiveFilter('all');
  });

  filterTodayBtn.addEventListener('click', () => {
    setActiveFilter('today');
  });

  headerDateFilter.addEventListener('change', (e) => {
    if (e.target.value) {
      setActiveFilter(e.target.value);
    }
  });

  // Workspace double click to create note
  workspace.addEventListener('dblclick', (e) => {
    if (e.target === workspace || e.target === notesContainer) {
      const rect = workspace.getBoundingClientRect();
      const x = Math.max(20, e.clientX - rect.left - 100);
      const y = Math.max(20, e.clientY - rect.top - 50);
      createNewNote({ pos_x: x, pos_y: y });
    }
  });

  // Calendar Controls
  calPrevMonthBtn.addEventListener('click', () => {
    calendarCurrentDate.setMonth(calendarCurrentDate.getMonth() - 1);
    renderCalendar();
  });

  calNextMonthBtn.addEventListener('click', () => {
    calendarCurrentDate.setMonth(calendarCurrentDate.getMonth() + 1);
    renderCalendar();
  });

  addNoteForSelectedDateBtn.addEventListener('click', () => {
    createNewNote({ target_date: selectedCalendarDate });
  });

  // Global click to close color dropdowns
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.color-menu-container')) {
      document.querySelectorAll('.color-dropdown.show').forEach(d => d.classList.remove('show'));
    }
  });
}

function setActiveFilter(filter) {
  filterAllBtn.classList.remove('active');
  filterTodayBtn.classList.remove('active');
  headerDateFilter.value = '';

  if (filter === 'all') {
    filterAllBtn.classList.add('active');
    activeDateFilter = null;
  } else if (filter === 'today') {
    filterTodayBtn.classList.add('active');
    activeDateFilter = getTodayIsoString();
  } else {
    activeDateFilter = filter;
    headerDateFilter.value = filter;
  }

  filterNotesDisplay();
}

// API Calls
async function loadNotes() {
  try {
    syncStatus.textContent = '🔄 동기화 중...';
    const res = await fetch('/api/notes');
    notes = await res.json();
    syncStatus.textContent = '☁️ 로컬 SQLite 실시간 동기화 완료';

    if (notes.length === 0) {
      // First-time default notes
      await createInitialNotes();
    } else {
      renderAllNotes();
    }
  } catch (err) {
    console.error('Failed to load notes:', err);
    syncStatus.textContent = '⚠️ 서버 연결 확인 중';
  }
}

async function createInitialNotes() {
  const today = getTodayIsoString();
  const sampleNote1 = {
    target_date: today,
    content: "[x] 포스트잇 캘린더 시작하기\n[ ] 파스텔 컬러 테마 확인\n[ ] 체크박스 투두 리스트 클릭해보기\n[ ] 핀 고정(📌) 및 드래그 이동 테스트",
    color: "yellow",
    is_pinned: 1,
    pos_x: 60,
    pos_y: 60,
    width: 320,
    height: 300
  };

  const sampleNote2 = {
    target_date: today,
    content: "💡 팁:\n- 상단 헤더의 [➕ 새 메모] 또는 바탕화면 더블클릭으로 새 포스트잇 생성\n- 모서리를 드래그하면 크기 조절 가능\n- 오른쪽 상단 [📅 캘린더 뷰]를 누르면 날짜별 일정 요약을 확인하실 수 있습니다.",
    color: "blue",
    is_pinned: 0,
    pos_x: 420,
    pos_y: 60,
    width: 340,
    height: 280
  };

  await fetch('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sampleNote1)
  });

  await fetch('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sampleNote2)
  });

  const res = await fetch('/api/notes');
  notes = await res.json();
  renderAllNotes();
}

// Render All Notes
function renderAllNotes() {
  notesContainer.innerHTML = '';
  notes.forEach(note => {
    const noteEl = createNoteElement(note);
    notesContainer.appendChild(noteEl);
  });
  updateCounts();
  filterNotesDisplay();
}

// Create Note DOM Element
function createNoteElement(note) {
  const el = document.createElement('div');
  el.className = `sticky-note theme-${note.color || 'yellow'}`;
  el.id = `note-${note.id}`;
  el.dataset.id = note.id;

  if (note.is_pinned) {
    el.classList.add('pinned');
  }

  // Positioning
  el.style.left = `${note.pos_x || 100}px`;
  el.style.top = `${note.pos_y || 100}px`;
  el.style.width = `${note.width || 320}px`;
  el.style.height = `${note.height || 280}px`;
  el.style.zIndex = note.is_pinned ? 500 : ++highestZIndex;

  // Detect if content has todo pattern
  const isTodoMode = hasTodoPattern(note.content);

  el.innerHTML = `
    <!-- 헤더 (드래그 핸들) -->
    <div class="note-header">
      <div class="header-meta">
        <input type="date" class="note-date-input" value="${note.target_date || getTodayIsoString()}" title="일정 날짜">
      </div>
      <div class="note-actions">
        <button class="note-tool-btn mode-btn" title="체크박스/텍스트 모드 전환">${isTodoMode ? '📝' : '☑️'}</button>
        <button class="note-tool-btn pin-btn ${note.is_pinned ? 'pinned-active' : ''}" title="항상 위 고정">${note.is_pinned ? '📌' : '📍'}</button>
        <div class="color-menu-container" style="position: relative; display: inline-block;">
          <button class="note-tool-btn color-btn" title="컬러 테마 변경">🎨</button>
          <div class="color-dropdown">
            <span class="color-swatch swatch-yellow" data-color="yellow" title="노랑"></span>
            <span class="color-swatch swatch-blue" data-color="blue" title="파랑"></span>
            <span class="color-swatch swatch-green" data-color="green" title="초록"></span>
            <span class="color-swatch swatch-orange" data-color="orange" title="주황"></span>
            <span class="color-swatch swatch-purple" data-color="purple" title="보라"></span>
          </div>
        </div>
        <button class="note-tool-btn add-btn" title="새 메모">➕</button>
        <button class="note-tool-btn min-btn" title="트레이(독)로 최소화">➖</button>
        <button class="note-tool-btn del-btn" title="삭제">✕</button>
      </div>
    </div>

    <!-- 본문 영역 -->
    <div class="note-body">
      ${isTodoMode ? renderTodoView(note.content) : `<textarea class="note-textarea" placeholder="일정 메모나 할 일을 적어보세요...">${escapeHtml(note.content || '')}</textarea>`}
    </div>

    <!-- 푸터 및 리사이즈 핸들 -->
    <div class="note-footer">
      <span class="char-count">${(note.content || '').length}자</span>
      <span class="save-status">저장됨</span>
      <div class="resize-handle" title="크기 조절"></div>
    </div>
  `;

  // Attach interactive behavior
  attachNoteEvents(el, note);

  return el;
}

// Attach Note Events
function attachNoteEvents(noteEl, note) {
  const header = noteEl.querySelector('.note-header');
  const dateInput = noteEl.querySelector('.note-date-input');
  const pinBtn = noteEl.querySelector('.pin-btn');
  const colorBtn = noteEl.querySelector('.color-btn');
  const colorDropdown = noteEl.querySelector('.color-dropdown');
  const modeBtn = noteEl.querySelector('.mode-btn');
  const addBtn = noteEl.querySelector('.add-btn');
  const delBtn = noteEl.querySelector('.del-btn');
  const resizeHandle = noteEl.querySelector('.resize-handle');
  const noteBody = noteEl.querySelector('.note-body');

  // Bring to front on click
  noteEl.addEventListener('mousedown', () => {
    if (!note.is_pinned) {
      noteEl.style.zIndex = ++highestZIndex;
    }
  });

  // Date Change
  dateInput.addEventListener('change', (e) => {
    note.target_date = e.target.value;
    debouncedSave(note);
    renderCalendar();
  });

  // Pin Toggle
  pinBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    note.is_pinned = note.is_pinned ? 0 : 1;
    if (note.is_pinned) {
      noteEl.classList.add('pinned');
      pinBtn.classList.add('pinned-active');
      pinBtn.textContent = '📌';
      noteEl.style.zIndex = 500;
    } else {
      noteEl.classList.remove('pinned');
      pinBtn.classList.remove('pinned-active');
      pinBtn.textContent = '📍';
      noteEl.style.zIndex = ++highestZIndex;
    }
    debouncedSave(note);
  });

  // Color Menu
  colorBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    document.querySelectorAll('.color-dropdown.show').forEach(d => {
      if (d !== colorDropdown) d.classList.remove('show');
    });
    colorDropdown.classList.toggle('show');
  });

  colorDropdown.querySelectorAll('.color-swatch').forEach(swatch => {
    swatch.addEventListener('click', (e) => {
      e.stopPropagation();
      const color = swatch.dataset.color;
      PASTEL_THEMES.forEach(t => noteEl.classList.remove(`theme-${t}`));
      noteEl.classList.add(`theme-${color}`);
      note.color = color;
      colorDropdown.classList.remove('show');
      debouncedSave(note);
      renderCalendar();
    });
  });

  // Add new note near this note
  addBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    createNewNote({
      pos_x: (note.pos_x || 100) + 40,
      pos_y: (note.pos_y || 100) + 40,
      target_date: note.target_date
    });
  });

  // Minimize to dock
  const minBtn = noteEl.querySelector('.min-btn');
  if (minBtn) {
    minBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      minimizedNoteIds.add(note.id);
      noteEl.classList.add('minimized');
      updateDockState();
    });
  }

  // Delete note
  delBtn.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (confirm('이 메모를 삭제하시겠습니까?')) {
      await deleteNote(note.id);
    }
  });

  // Mode Toggle (Text vs Todo)
  modeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isTodo = hasTodoPattern(note.content);
    if (isTodo) {
      // Switch to text mode
      noteBody.innerHTML = `<textarea class="note-textarea" placeholder="메모 내용 입력...">${escapeHtml(note.content || '')}</textarea>`;
      modeBtn.textContent = '☑️';
      attachTextareaEvents(noteEl, note);
    } else {
      // Switch to todo mode
      const lines = (note.content || '').split('\n').filter(l => l.trim() !== '');
      if (lines.length === 0) {
        note.content = '[ ] 새로운 할 일';
      } else {
        note.content = lines.map(l => l.startsWith('[ ] ') || l.startsWith('[x] ') ? l : `[ ] ${l}`).join('\n');
      }
      noteBody.innerHTML = renderTodoView(note.content);
      modeBtn.textContent = '📝';
      attachTodoEvents(noteEl, note);
      debouncedSave(note);
    }
  });

  // Textarea input event if in text mode
  if (!hasTodoPattern(note.content)) {
    attachTextareaEvents(noteEl, note);
  } else {
    attachTodoEvents(noteEl, note);
  }

  // Draggable logic
  setupDraggable(noteEl, header, note);

  // Resizable logic
  setupResizable(noteEl, resizeHandle, note);
}

// Textarea Events
function attachTextareaEvents(noteEl, note) {
  const textarea = noteEl.querySelector('.note-textarea');
  const charCount = noteEl.querySelector('.char-count');
  if (!textarea) return;

  textarea.addEventListener('input', (e) => {
    note.content = e.target.value;
    if (charCount) charCount.textContent = `${note.content.length}자`;
    debouncedSave(note);
  });
}

// Todo List Events
function attachTodoEvents(noteEl, note) {
  const todoContainer = noteEl.querySelector('.todo-container');
  if (!todoContainer) return;

  // Checkbox toggle
  todoContainer.querySelectorAll('.todo-checkbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      const idx = parseInt(cb.dataset.index, 10);
      const isChecked = cb.checked;
      const lines = note.content.split('\n');
      if (lines[idx] !== undefined) {
        const text = lines[idx].replace(/^\[( |x)\]\s*/i, '');
        lines[idx] = `[${isChecked ? 'x' : ' '}] ${text}`;
        note.content = lines.join('\n');
        
        const itemEl = cb.closest('.todo-item');
        if (isChecked) itemEl.classList.add('completed');
        else itemEl.classList.remove('completed');

        debouncedSave(note);
      }
    });
  });

  // Edit todo item text
  todoContainer.querySelectorAll('.todo-text').forEach(input => {
    input.addEventListener('change', (e) => {
      const idx = parseInt(input.dataset.index, 10);
      const lines = note.content.split('\n');
      if (lines[idx] !== undefined) {
        const isChecked = lines[idx].startsWith('[x]');
        lines[idx] = `[${isChecked ? 'x' : ' '}] ${e.target.value.trim()}`;
        note.content = lines.join('\n');
        debouncedSave(note);
      }
    });
  });

  // Delete todo item
  todoContainer.querySelectorAll('.todo-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const idx = parseInt(btn.dataset.index, 10);
      const lines = note.content.split('\n');
      lines.splice(idx, 1);
      note.content = lines.join('\n');
      noteEl.querySelector('.note-body').innerHTML = renderTodoView(note.content);
      attachTodoEvents(noteEl, note);
      debouncedSave(note);
    });
  });

  // Add new item
  const addForm = todoContainer.querySelector('.todo-add-form');
  const addInput = todoContainer.querySelector('.todo-add-input');
  if (addForm && addInput) {
    addForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const val = addInput.value.trim();
      if (!val) return;
      const lines = (note.content || '').split('\n').filter(l => l.trim() !== '');
      lines.push(`[ ] ${val}`);
      note.content = lines.join('\n');
      noteEl.querySelector('.note-body').innerHTML = renderTodoView(note.content);
      attachTodoEvents(noteEl, note);
      debouncedSave(note);
    });
  }
}

// Render Todo View HTML
function renderTodoView(content) {
  const lines = (content || '').split('\n').filter(l => l.trim() !== '');
  const itemsHtml = lines.map((line, idx) => {
    const isChecked = /^\[x\]/i.test(line);
    const text = line.replace(/^\[( |x)\]\s*/i, '');
    return `
      <div class="todo-item ${isChecked ? 'completed' : ''}">
        <input type="checkbox" class="todo-checkbox" data-index="${idx}" ${isChecked ? 'checked' : ''}>
        <input type="text" class="todo-text" data-index="${idx}" value="${escapeHtml(text)}">
        <button class="todo-delete-btn" data-index="${idx}" title="삭제">✕</button>
      </div>
    `;
  }).join('');

  return `
    <div class="todo-container">
      <div class="todo-list">
        ${itemsHtml || '<p style="font-size:12px;opacity:0.6;padding:8px;">할 일을 추가해보세요!</p>'}
      </div>
      <form class="todo-add-form">
        <input type="text" class="todo-add-input" placeholder="+ 새 할 일 추가...">
        <button type="submit" class="todo-add-btn">추가</button>
      </form>
    </div>
  `;
}

function hasTodoPattern(content) {
  if (!content) return false;
  return /\[( |x)\]/i.test(content);
}

// Dragging Logic
function setupDraggable(noteEl, handle, note) {
  let startX, startY, origX, origY;

  handle.addEventListener('mousedown', (e) => {
    // Ignore clicks on inputs/buttons
    if (['INPUT', 'BUTTON', 'SPAN'].includes(e.target.tagName)) return;
    
    isDraggingNote = true;
    noteEl.classList.add('dragging');
    startX = e.clientX;
    startY = e.clientY;
    origX = noteEl.offsetLeft;
    origY = noteEl.offsetTop;

    function onMouseMove(e) {
      if (!isDraggingNote) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const newX = Math.max(10, origX + dx);
      const newY = Math.max(10, origY + dy);
      noteEl.style.left = `${newX}px`;
      noteEl.style.top = `${newY}px`;
      note.pos_x = newX;
      note.pos_y = newY;
    }

    function onMouseUp() {
      if (!isDraggingNote) return;
      isDraggingNote = false;
      noteEl.classList.remove('dragging');
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      debouncedSave(note);
    }

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });
}

// Resizing Logic
function setupResizable(noteEl, handle, note) {
  let startX, startY, startW, startH;

  handle.addEventListener('mousedown', (e) => {
    e.stopPropagation();
    e.preventDefault();
    isResizingNote = true;
    startX = e.clientX;
    startY = e.clientY;
    startW = noteEl.offsetWidth;
    startH = noteEl.offsetHeight;

    function onMouseMove(e) {
      if (!isResizingNote) return;
      const newW = Math.max(260, startW + (e.clientX - startX));
      const newH = Math.max(200, startH + (e.clientY - startY));
      noteEl.style.width = `${newW}px`;
      noteEl.style.height = `${newH}px`;
      note.width = newW;
      note.height = newH;
    }

    function onMouseUp() {
      if (!isResizingNote) return;
      isResizingNote = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      debouncedSave(note);
    }

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });
}

// Auto Save with Debounce
const saveTimers = {};
function debouncedSave(note) {
  const noteEl = document.getElementById(`note-${note.id}`);
  const statusEl = noteEl ? noteEl.querySelector('.save-status') : null;
  if (statusEl) statusEl.textContent = '저장 중...';

  clearTimeout(saveTimers[note.id]);
  saveTimers[note.id] = setTimeout(async () => {
    try {
      await fetch(`/api/notes/${note.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_date: note.target_date,
          content: note.content,
          color: note.color,
          is_pinned: note.is_pinned,
          pos_x: note.pos_x,
          pos_y: note.pos_y,
          width: note.width,
          height: note.height
        })
      });
      if (statusEl) statusEl.textContent = '저장됨';
      syncStatus.textContent = '☁️ 로컬 SQLite 실시간 동기화 완료';
    } catch (err) {
      console.error('Save failed:', err);
      if (statusEl) statusEl.textContent = '저장 실패';
    }
  }, 400);
}

// Create New Note
async function createNewNote(defaults = {}) {
  const randomColor = PASTEL_THEMES[Math.floor(Math.random() * PASTEL_THEMES.length)];
  const today = getTodayIsoString();

  const newNoteData = {
    target_date: defaults.target_date || today,
    content: defaults.content || '',
    color: defaults.color || randomColor,
    is_pinned: defaults.is_pinned || 0,
    pos_x: defaults.pos_x || (150 + Math.floor(Math.random() * 80)),
    pos_y: defaults.pos_y || (120 + Math.floor(Math.random() * 80)),
    width: defaults.width || 320,
    height: defaults.height || 280
  };

  try {
    const res = await fetch('/api/notes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newNoteData)
    });
    const created = await res.json();
    notes.push(created);

    const noteEl = createNoteElement(created);
    notesContainer.appendChild(noteEl);

    // Focus textarea
    const textarea = noteEl.querySelector('.note-textarea');
    if (textarea) textarea.focus();

    updateCounts();
    filterNotesDisplay();
    renderCalendar();
  } catch (err) {
    console.error('Failed to create note:', err);
  }
}

// Delete Note
async function deleteNote(noteId) {
  try {
    await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
    notes = notes.filter(n => n.id !== noteId);
    const el = document.getElementById(`note-${noteId}`);
    if (el) el.remove();

    updateCounts();
    renderCalendar();
  } catch (err) {
    console.error('Failed to delete note:', err);
  }
}

// Filter and Search Notes
function filterNotesDisplay() {
  let visibleCount = 0;

  notes.forEach(note => {
    const el = document.getElementById(`note-${note.id}`);
    if (!el) return;

    let matchesSearch = true;
    if (activeSearchQuery) {
      const contentMatch = (note.content || '').toLowerCase().includes(activeSearchQuery);
      const dateMatch = (note.target_date || '').includes(activeSearchQuery);
      matchesSearch = contentMatch || dateMatch;
    }

    let matchesDate = true;
    if (activeDateFilter) {
      matchesDate = note.target_date === activeDateFilter;
    }

    if (matchesSearch && matchesDate) {
      el.style.display = 'flex';
      visibleCount++;
    } else {
      el.style.display = 'none';
    }
  });

  if (visibleCount === 0 && notes.length > 0) {
    emptyState.classList.remove('hidden');
    emptyState.querySelector('h2').textContent = '검색/필터 조건에 맞는 메모가 없습니다';
    emptyState.querySelector('p').textContent = '검색어를 지우거나 전체 메모 필터를 눌러보세요.';
  } else if (notes.length === 0) {
    emptyState.classList.remove('hidden');
    emptyState.querySelector('h2').textContent = '작성된 메모가 없습니다';
    emptyState.querySelector('p').textContent = '상단의 [➕ 새 메모] 버튼을 눌러 메모를 만들어보세요.';
  } else {
    emptyState.classList.add('hidden');
  }
}

// Toggle all notes visibility (Tray / Dock behavior)
function toggleAllNotesVisibility() {
  const visibleElements = document.querySelectorAll('.sticky-note:not(.minimized)');
  if (visibleElements.length > 0) {
    // Hide all
    notes.forEach(n => {
      minimizedNoteIds.add(n.id);
      const el = document.getElementById(`note-${n.id}`);
      if (el) el.classList.add('minimized');
    });
  } else {
    // Restore all
    restoreAllNotes();
  }
  updateDockState();
}

function restoreAllNotes() {
  minimizedNoteIds.clear();
  document.querySelectorAll('.sticky-note.minimized').forEach(el => {
    el.classList.remove('minimized');
  });
  updateDockState();
}

function updateDockState() {
  const count = minimizedNoteIds.size;
  if (count > 0) {
    if (dockWidget) dockWidget.classList.remove('hidden');
    if (dockCountText) dockCountText.textContent = `${count}개의 메모 숨겨짐`;
    if (visibilityText) visibilityText.textContent = '전체 보이기';
  } else {
    if (dockWidget) dockWidget.classList.add('hidden');
    if (visibilityText) visibilityText.textContent = '전체 숨기기';
  }
}

// Auto Align Notes in a neat grid
function autoAlignNotes() {
  const visibleNotes = notes.filter(n => {
    const el = document.getElementById(`note-${n.id}`);
    return el && el.style.display !== 'none';
  });

  const gap = 24;
  const startX = 40;
  const startY = 40;
  const colWidth = 340;
  const rowHeight = 310;
  const maxCols = Math.max(1, Math.floor((workspace.clientWidth - startX) / (colWidth + gap)));

  visibleNotes.forEach((n, idx) => {
    const col = idx % maxCols;
    const row = Math.floor(idx / maxCols);
    const newX = startX + col * (colWidth + gap);
    const newY = startY + row * (rowHeight + gap);

    const el = document.getElementById(`note-${n.id}`);
    if (el) {
      el.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
      el.style.left = `${newX}px`;
      el.style.top = `${newY}px`;
      setTimeout(() => el.style.transition = '', 350);
    }
    n.pos_x = newX;
    n.pos_y = newY;
    debouncedSave(n);
  });
}

// Update Note Counts
function updateCounts() {
  const count = notes.length;
  noteCountDisplay.textContent = `메모 ${count}개`;
  if (count === 0) {
    emptyState.classList.remove('hidden');
  }
}

// Render Monthly Calendar
function renderCalendar() {
  const year = calendarCurrentDate.getFullYear();
  const month = calendarCurrentDate.getMonth();

  calCurrentMonth.textContent = `${year}년 ${month + 1}월`;

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrevMonth = new Date(year, month, 0).getDate();

  calendarGrid.innerHTML = '';

  const todayStr = getTodayIsoString();

  // Create date notes map
  const notesByDate = {};
  notes.forEach(n => {
    if (n.target_date) {
      if (!notesByDate[n.target_date]) notesByDate[n.target_date] = [];
      notesByDate[n.target_date].push(n);
    }
  });

  // Previous month trailing days
  for (let i = firstDay - 1; i >= 0; i--) {
    const d = daysInPrevMonth - i;
    const cell = document.createElement('div');
    cell.className = 'cal-day other-month';
    cell.textContent = d;
    calendarGrid.appendChild(cell);
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const cell = document.createElement('div');
    cell.className = 'cal-day';
    cell.textContent = d;

    if (dateStr === todayStr) cell.classList.add('today');
    if (dateStr === selectedCalendarDate) cell.classList.add('selected');
    if (notesByDate[dateStr] && notesByDate[dateStr].length > 0) {
      cell.classList.add('has-notes');
      cell.title = `메모 ${notesByDate[dateStr].length}개`;
    }

    cell.addEventListener('click', () => {
      document.querySelectorAll('.cal-day.selected').forEach(c => c.classList.remove('selected'));
      cell.classList.add('selected');
      selectedCalendarDate = dateStr;
      updateCalendarDayDetails(dateStr, notesByDate[dateStr] || []);
    });

    calendarGrid.appendChild(cell);
  }

  // Next month leading days to complete grid (42 cells max)
  const totalCells = firstDay + daysInMonth;
  const nextDays = (7 - (totalCells % 7)) % 7;
  for (let d = 1; d <= nextDays; d++) {
    const cell = document.createElement('div');
    cell.className = 'cal-day other-month';
    cell.textContent = d;
    calendarGrid.appendChild(cell);
  }

  // Update selected day details
  updateCalendarDayDetails(selectedCalendarDate, notesByDate[selectedCalendarDate] || []);
}

function updateCalendarDayDetails(dateStr, dayNotes) {
  selectedDateTitle.textContent = `${dateStr} 일정 (${dayNotes.length}건)`;
  selectedDateNotesList.innerHTML = '';

  if (dayNotes.length === 0) {
    selectedDateNotesList.innerHTML = `<p class="no-notes-hint">이 날짜에 등록된 메모가 없습니다.</p>`;
    return;
  }

  dayNotes.forEach(n => {
    const item = document.createElement('div');
    item.className = `day-note-item theme-${n.color || 'yellow'}`;
    const preview = (n.content || '(내용 없음)').split('\n')[0].slice(0, 30);
    item.innerHTML = `
      <strong>${n.is_pinned ? '📌 ' : ''}${escapeHtml(preview)}</strong>
      <p style="font-size:11px;opacity:0.7;margin-top:2px;">클릭하여 캔버스에서 확인</p>
    `;
    item.addEventListener('click', () => {
      const el = document.getElementById(`note-${n.id}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.style.transform = 'scale(1.08)';
        setTimeout(() => el.style.transform = '', 400);
        if (!n.is_pinned) el.style.zIndex = ++highestZIndex;
      }
    });
    selectedDateNotesList.appendChild(item);
  });
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return (text || '').replace(/[&<>"']/g, m => map[m]);
}

// Start
document.addEventListener('DOMContentLoaded', initApp);
