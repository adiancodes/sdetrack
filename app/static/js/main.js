(() => {
  const category = (window.APP_CATEGORY || 'striver').toLowerCase();
  const socket = io({ query: { category } });

  const getRowByQuestionId = (questionId) =>
    document.querySelector(`tr[data-question-id="${questionId}"]`);

  const updateCheckboxState = (question, userField) => {
    const row = getRowByQuestionId(question.id);
    if (!row) {
      return;
    }
    const checkbox = row.querySelector(`.status-checkbox[data-user-field="${userField}"]`);
    if (checkbox) {
      checkbox.checked = Boolean(question.status?.[userField]);
    }
  };

  const updateDashboard = (payload) => {
    if (!payload || !payload.dashboard) {
      return;
    }
    const { dashboard, user_one_name: userOneLabel, user_two_name: userTwoLabel } = payload;
    const cards = document.querySelectorAll('[data-user-card]');
    cards.forEach((card) => {
      const userField = card.getAttribute('data-user-card');
      const stats = dashboard[userField];
      if (!stats) {
        return;
      }

      const nameElement = card.querySelector('.card-title');
      if (nameElement) {
        nameElement.textContent = userField === 'user_one' ? userOneLabel : userTwoLabel;
      }

      const completedSpan = card.querySelector(`[data-progress-completed="${userField}"]`);
      if (completedSpan) {
        completedSpan.textContent = stats.completed ?? 0;
      }

      const totalSpan = card.querySelector('[data-progress-total]');
      if (totalSpan) {
        totalSpan.textContent = stats.total ?? 0;
      }

      const progressBar = card.querySelector(`[data-progress-bar="${userField}"]`);
      if (progressBar) {
        const total = Math.max(stats.total ?? 0, 1);
        const percent = ((stats.completed ?? 0) / total) * 100;
        progressBar.style.width = `${percent.toFixed(1)}%`;
        progressBar.setAttribute('aria-valuenow', percent.toFixed(1));
      }

      const difficultyList = card.querySelector('[data-difficulty-list]');
      if (!difficultyList) {
        return;
      }
      const items = difficultyList.querySelectorAll('li');
      items.forEach((item) => {
        const label = item.querySelector('[data-difficulty-completed]');
        const completedKey = label?.getAttribute('data-difficulty-completed');
        if (!completedKey) {
          return;
        }
        const difficultyStats = stats.difficulty?.[completedKey];
        if (label && difficultyStats) {
          label.textContent = difficultyStats.completed ?? 0;
        }
        const totalLabel = item.querySelector('[data-difficulty-total]');
        if (totalLabel && difficultyStats) {
          totalLabel.textContent = difficultyStats.total ?? 0;
        }
      });
    });
  };

  const handleCheckboxChange = (event) => {
    const checkbox = event.target;
    if (!(checkbox instanceof HTMLInputElement) || checkbox.type !== 'checkbox') {
      return;
    }
    const row = checkbox.closest('tr[data-question-id]');
    if (!row) {
      return;
    }
    const questionId = row.getAttribute('data-question-id');
    const userField = checkbox.getAttribute('data-user-field');
    if (!questionId || !userField) {
      return;
    }

    // Optimistic UI: update dashboard immediately
    try {
      const difficultyBadge = row.querySelector('td:nth-child(3) .badge');
      const difficultyText = (difficultyBadge?.textContent || '').trim(); // Easy | Medium | Hard
      const delta = checkbox.checked ? 1 : -1;
      const card = document.querySelector(`[data-user-card="${userField}"]`);
      if (card) {
        const completedSpan = card.querySelector(`[data-progress-completed="${userField}"]`);
        const totalSpan = card.querySelector('[data-progress-total]');
        const progressBar = card.querySelector(`[data-progress-bar="${userField}"]`);
        // update overall completed
        const currentCompleted = parseInt(completedSpan?.textContent || '0', 10) || 0;
        const total = parseInt(totalSpan?.textContent || '0', 10) || 0;
        const nextCompleted = Math.min(Math.max(currentCompleted + delta, 0), total);
        if (completedSpan) completedSpan.textContent = String(nextCompleted);
        if (progressBar && total > 0) {
          const percent = (nextCompleted / total) * 100;
          progressBar.style.width = `${percent.toFixed(1)}%`;
          progressBar.setAttribute('aria-valuenow', percent.toFixed(1));
        }
        // update difficulty chips
        if (difficultyText) {
          const item = card.querySelector(`[data-difficulty-list] [data-difficulty-completed="${difficultyText}"]`);
          if (item) {
            const val = parseInt(item.textContent || '0', 10) || 0;
            const next = Math.max(val + delta, 0);
            item.textContent = String(next);
          }
        }
      }
    } catch (_) {
      // non-fatal; server will sync shortly
    }

    socket.emit('toggle_status', {
      question_id: questionId,
      user_field: userField,
      completed: checkbox.checked,
      category,
    });
  };

  document.querySelectorAll('.status-checkbox').forEach((checkbox) => {
    checkbox.addEventListener('change', handleCheckboxChange);
  });

  socket.on('status_updated', ({ question, user_field: userField, category: updateCategory }) => {
    if (!question || !userField) {
      return;
    }
    if (updateCategory && updateCategory !== category) {
      return;
    }
    updateCheckboxState(question, userField);
  });

  socket.on('dashboard_sync', (payload) => {
    if (payload?.category && payload.category !== category) {
      return;
    }
    updateDashboard(payload);
  });

  socket.emit('request_dashboard', { category });
})();

// Persist day-wise collapse state (collapsed by default)
(() => {
  if (typeof bootstrap === 'undefined') {
    return;
  }

  const applySavedState = () => {
    document.querySelectorAll('[data-day-body].collapse').forEach((el) => {
      const key = `day-open-#${el.id}`;
      const shouldOpen = localStorage.getItem(key) === '1';
      if (shouldOpen) {
        const instance = new bootstrap.Collapse(el, { toggle: false });
        instance.show();
        const header = document.querySelector(`[data-bs-target="#${el.id}"]`);
        if (header) header.setAttribute('aria-expanded', 'true');
      }
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    applySavedState();

    document.querySelectorAll('[data-day-body].collapse').forEach((el) => {
      el.addEventListener('shown.bs.collapse', () => {
        localStorage.setItem(`day-open-#${el.id}`, '1');
      });
      el.addEventListener('hidden.bs.collapse', () => {
        localStorage.removeItem(`day-open-#${el.id}`);
      });
    });
  });
})();
