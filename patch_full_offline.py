# -*- coding: utf-8 -*-
import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update loadStudentAssignments, loadStudentHistory, startExam, submitExam, loadStudentSummary
# Let's inspect where loadStudentSummary and renderStudentSummaryUI are defined
print("Finding target sections in index.html...")

# Pattern for loadStudentAssignments
pattern_assignments = r'async function loadStudentAssignments\(\) \{.*?\n    \}'
new_assignments = '''async function loadStudentAssignments() {
      const container = document.getElementById('assignmentsList');
      container.innerHTML = '<div class="text-center" style="padding:2rem;">載入測驗項目中...</div>';

      let assignmentsData = null;
      try {
        const res = await apiFetch(`/api/student/assignments?subject=${currentSubject}&student_id=${currentStudent ? currentStudent.id : ''}`);
        const data = await res.json();
        if (data.success && data.assignments && data.assignments.length > 0) {
          assignmentsData = data.assignments;
        }
      } catch (err) {
        console.warn("apiFetch loadStudentAssignments failed, switching to local offline bank", err);
      }

      if (!assignmentsData || assignmentsData.length === 0) {
        assignmentsData = getLocalAssignmentsForSubject(currentSubject, currentStudent);
      }

      if (assignmentsData && assignmentsData.length > 0) {
        container.innerHTML = '';
        assignmentsData.forEach(a => {
          const card = document.createElement('div');
          card.className = 'card';
          card.style.border = '2px solid #e2e8f0';
          card.style.borderRadius = '12px';
          card.style.transition = 'all 0.2s';

          const unitBadges = (a.unit_titles || []).map(u => `<span class="badge badge-gray" style="margin:2px;">${u}</span>`).join(' ');

          let personalStatsHtml = '';
          if (a.attempts_count > 0) {
            personalStatsHtml = `
              <div style="background:#ecfdf5; border:1px solid #a7f3d0; border-radius:8px; padding:0.6rem 1rem; margin:0.75rem 0; font-size:0.9rem; color:#065f46;">
                🌟 <b>個人測驗紀錄</b>：已完成 <b>${a.attempts_count}</b> 次 ｜ 最高得分：<b style="font-size:1.15rem; color:#047857;">${a.best_score}</b> 分 ｜ 最近得分：${a.latest_score} 分 (${a.latest_at})
              </div>
            `;
          } else {
            personalStatsHtml = `
              <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:0.5rem 1rem; margin:0.75rem 0; font-size:0.88rem; color:#64748b;">
                ⏳ 您尚未參加此項測驗，隨時可以開始！
              </div>
            `;
          }

          card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.5rem;">
              <div>
                <span class="badge badge-primary">題數：${a.question_count} 題隨機抽取</span>
                <h3 style="font-size:1.35rem; font-weight:800; margin:0.4rem 0 0.2rem;">${a.title}</h3>
                <div style="font-size:0.85rem; color:var(--text-muted);">
                  📅 <b>老師命題時間</b>：${a.created_at} ｜ 👩‍🏫 命題教師：${a.created_by}
                </div>
              </div>
            </div>

            <div style="margin:0.75rem 0 0.25rem;">
              <div style="font-size:0.85rem; font-weight:700; color:#475569; margin-bottom:0.25rem;">涵蓋單元：</div>
              <div>${unitBadges}</div>
            </div>

            ${personalStatsHtml}

            <div style="margin-top:1.25rem; display:flex; justify-content:flex-end;">
              <button class="btn btn-primary btn-lg" onclick="startExam(${a.id})">
                🚀 開始測驗（隨機出 ${a.question_count} 題）
              </button>
            </div>
          `;
          container.appendChild(card);
        });
      } else {
        container.innerHTML = `
          <div class="card text-center" style="padding:2.5rem 1rem;">
            <div style="font-size:2.5rem; margin-bottom:0.5rem;">📝</div>
            <h3 style="font-size:1.25rem; font-weight:700;">目前 ${SUBJ_NAMES[currentSubject]} 尚無開放中的測驗項目</h3>
            <p style="color:#64748b; font-size:0.92rem; margin-top:0.35rem;">老師即將發布最新命題，您亦可先切換其他科目進行練習！</p>
          </div>
        `;
      }
    }'''

match_a = re.search(pattern_assignments, html, flags=re.DOTALL)
if match_a:
    html = html[:match_a.start()] + new_assignments + html[match_a.end():]
    print("Replaced loadStudentAssignments successfully!")
else:
    print("Warning: loadStudentAssignments pattern not found!")

# Pattern for loadStudentHistory
pattern_history = r'async function loadStudentHistory\(\) \{.*?\n    \}'
new_history = '''async function loadStudentHistory() {
      if (!currentStudent) return;
      let historyList = [];
      try {
        const res = await apiFetch(`/api/student/history?student_id=${currentStudent.id}&assignment_id=`);
        const data = await res.json();
        if (data.success && data.history && data.history.length > 0) {
          historyList = data.history;
        }
      } catch (err) {}

      if (historyList.length === 0) {
        const allRecords = getStoredExamRecords();
        historyList = allRecords.filter(r => (r.student_id == currentStudent.id || r.seat_no === currentStudent.seat_no));
      }

      const tbody = document.getElementById('studentHistoryTableBody');
      const countBadge = document.getElementById('historyCountBadge');

      const filtered = historyList.filter(h => !h.subject_code || h.subject_code === currentSubject);

      if (filtered.length > 0) {
        countBadge.textContent = `共 ${filtered.length} 次紀錄`;
        tbody.innerHTML = '';
        filtered.forEach((h, idx) => {
          const tr = document.createElement('tr');
          const scoreColor = h.score >= 90 ? '#059669' : (h.score >= 60 ? '#2563eb' : '#dc2626');
          const mins = Math.floor(h.duration_seconds / 60);
          const secs = h.duration_seconds % 60;
          const durStr = `${mins}分${secs}秒`;

          tr.innerHTML = `
            <td><b>第 ${filtered.length - idx} 次</b></td>
            <td>${h.assignment_title || ('測驗項目 #' + h.assignment_id)}</td>
            <td><span style="font-size:1.15rem; font-weight:800; color:${scoreColor};">${h.score} 分</span></td>
            <td>${h.correct_count} / ${h.total_questions} 題</td>
            <td>${durStr}</td>
            <td>${h.completed_at}</td>
          `;
          tbody.appendChild(tr);
        });
      } else {
        countBadge.textContent = '共 0 次紀錄';
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color:var(--text-muted); padding:1.5rem;">目前 ${SUBJ_NAMES[currentSubject] || ''} 尚未有測驗紀錄，請點選上方開始測驗！</td></tr>`;
      }
    }'''

match_h = re.search(pattern_history, html, flags=re.DOTALL)
if match_h:
    html = html[:match_h.start()] + new_history + html[match_h.end():]
    print("Replaced loadStudentHistory successfully!")
else:
    print("Warning: loadStudentHistory pattern not found!")

# Pattern for startExam
pattern_start = r'async function startExam\(assignmentId\) \{.*?\n    \}'
new_start = '''async function startExam(assignmentId) {
      if (!currentStudent) {
        navigateTo('student');
        return;
      }

      let sessionData = null;
      try {
        const res = await apiFetch(`/api/student/exam/start?assignment_id=${assignmentId}&student_id=${currentStudent.id}`);
        const data = await res.json();
        if (data.success) {
          sessionData = data;
        }
      } catch (err) {
        console.warn("apiFetch startExam failed, starting local offline exam session", err);
      }

      if (!sessionData) {
        sessionData = getLocalExamSession(assignmentId, currentStudent);
      }

      if (sessionData && sessionData.success) {
        activeExamSession = sessionData;
        currentQIndex = 0;
        studentAnswers = {};

        const sName = SUBJ_NAMES[currentSubject] || '測驗';
        document.getElementById('examSubjectBadge').textContent = `${sName}科測驗`;
        document.getElementById('examTitle').textContent = sessionData.assignment_title;
        document.getElementById('examStudentLabel').textContent = `作答學生：${currentStudent.seat_no}號 ${currentStudent.name}`;

        renderQNavigator();
        showCurrentQuestion();
        startExamTimer();
        navigateTo('exam');
      } else {
        alert("無法開始測驗，請重新嘗試！");
      }
    }'''

match_s = re.search(pattern_start, html, flags=re.DOTALL)
if match_s:
    html = html[:match_s.start()] + new_start + html[match_s.end():]
    print("Replaced startExam successfully!")
else:
    print("Warning: startExam pattern not found!")

# Pattern for submitExam
pattern_sub = r'async function submitExam\(\) \{.*?\n    \}'
new_sub = '''async function submitExam() {
      stopExamTimer();
      let resultData = null;

      if (!activeExamSession.is_local) {
        try {
          const res = await apiFetch('/api/student/exam/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              session_id: activeExamSession.session_id,
              answers: studentAnswers
            })
          });
          const data = await res.json();
          if (data.success) {
            resultData = data;
          }
        } catch (err) {
          console.warn("Server submit failed, falling back to local grading", err);
        }
      }

      if (!resultData) {
        resultData = gradeLocalExam(activeExamSession, studentAnswers);
      }

      if (resultData && resultData.success) {
        latestExamResult = resultData;
        renderExamResult(resultData);
        navigateTo('result');
      } else {
        alert("交卷評分失敗，請重新嘗試");
      }
    }'''

match_sub = re.search(pattern_sub, html, flags=re.DOTALL)
if match_sub:
    html = html[:match_sub.start()] + new_sub + html[match_sub.end():]
    print("Replaced submitExam successfully!")
else:
    print("Warning: submitExam pattern not found!")

# Pattern for DOMContentLoaded
pattern_dom = r"document\.addEventListener\('DOMContentLoaded', \(\) => \{.*?\n    \}\);"
new_dom = '''document.addEventListener('DOMContentLoaded', () => {
      if (window.location.protocol === 'file:') {
        const banner = document.getElementById('fileModeNotice');
        if (banner) banner.style.display = 'block';
      }
      loadStudentsList();
      checkSavedSession();
    });'''

match_dom = re.search(pattern_dom, html, flags=re.DOTALL)
if match_dom:
    html = html[:match_dom.start()] + new_dom + html[match_dom.end():]
    print("Replaced DOMContentLoaded successfully!")
else:
    print("Warning: DOMContentLoaded pattern not found!")

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("index.html fully patched with resilient dual-engine!")
