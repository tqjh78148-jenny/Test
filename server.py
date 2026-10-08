# -*- coding: utf-8 -*-
"""
Online Quiz System - HTTP REST Server
Built with Python standard library (zero external dependencies)
"""
import http.server
import json
import sqlite3
import os
import urllib.parse
import random
import time
import uuid
from datetime import datetime

import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'quiz.db')

# In-memory storage for active exam sessions: session_id -> session_info
EXAM_SESSIONS = {}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class QuizRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.command} {self.path} - {args[0]}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static files
        if path == '/' or path == '/index.html':
            self.serve_file(os.path.join(BASE_DIR, 'index.html'), 'text/html; charset=utf-8')
            return
        elif path.startswith('/static/'):
            rel_path = path[8:]
            file_path = os.path.join(BASE_DIR, 'static', rel_path)
            if os.path.exists(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                mime = 'text/plain'
                if ext == '.css': mime = 'text/css'
                elif ext == '.js': mime = 'application/javascript'
                elif ext in ['.png', '.jpg', '.jpeg']: mime = 'image/' + ext[1:]
                self.serve_file(file_path, mime)
                return

        # APIs
        if path == '/api/students':
            self.api_get_students()
        elif path == '/api/subjects':
            self.api_get_subjects()
        elif path == '/api/student/assignments':
            subject = query.get('subject', ['chinese'])[0]
            student_id = query.get('student_id', [None])[0]
            self.api_get_student_assignments(subject, student_id)
        elif path == '/api/student/exam/start':
            assignment_id = query.get('assignment_id', [None])[0]
            student_id = query.get('student_id', [None])[0]
            self.api_start_exam(assignment_id, student_id)
        elif path == '/api/student/history':
            student_id = query.get('student_id', [None])[0]
            assignment_id = query.get('assignment_id', [None])[0]
            self.api_get_student_history(student_id, assignment_id)
        elif path == '/api/student/summary':
            student_id = query.get('student_id', [None])[0]
            self.api_get_student_summary(student_id)
        elif path == '/api/teacher/overview':
            assignment_id = query.get('assignment_id', [None])[0]
            self.api_get_teacher_overview(assignment_id)
        elif path == '/api/teacher/student-records':
            student_id = query.get('student_id', [None])[0]
            assignment_id = query.get('assignment_id', [None])[0]
            self.api_get_teacher_student_records(student_id, assignment_id)
        elif path == '/api/teacher/assignments':
            subject = query.get('subject', [None])[0]
            self.api_get_teacher_assignments(subject)
        elif path == '/api/teacher/units':
            subject = query.get('subject', [None])[0]
            self.api_get_teacher_units(subject)
        elif path == '/api/teacher/questions':
            unit_code = query.get('unit_code', [None])[0]
            self.api_get_teacher_questions(unit_code)
        elif path == '/api/teacher/export-csv':
            assignment_id = query.get('assignment_id', [None])[0]
            self.api_export_csv(assignment_id)
        elif path == '/api/health':
            self.send_json({"status": "ok", "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode('utf-8'))
            except Exception:
                payload = {}

        if path == '/api/student/login':
            self.api_student_login(payload)
        elif path == '/api/student/exam/submit':
            self.api_submit_exam(payload)
        elif path == '/api/teacher/login':
            self.api_teacher_login(payload)
        elif path == '/api/teacher/assignments/create':
            self.api_create_assignment(payload)
        elif path == '/api/teacher/assignments/toggle':
            self.api_toggle_assignment(payload)
        elif path == '/api/teacher/units/create':
            self.api_create_unit(payload)
        elif path == '/api/teacher/questions/create':
            self.api_create_question(payload)
        elif path == '/api/admin/reset-records':
            self.api_admin_reset_records(payload)
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, file_path, mime_type):
        if not os.path.exists(file_path):
            self.send_error(404, "File Not Found")
            return
        with open(file_path, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(content)

    # --- Student APIs ---
    def api_get_students(self):
        conn = get_db()
        rows = conn.execute("SELECT id, class_name, seat_no, name FROM students ORDER BY seat_no ASC").fetchall()
        data = [dict(r) for r in rows]
        conn.close()
        self.send_json({"success": True, "students": data})

    def api_get_subjects(self):
        conn = get_db()
        rows = conn.execute("SELECT code, name, description FROM subjects").fetchall()
        data = [dict(r) for r in rows]
        conn.close()
        self.send_json({"success": True, "subjects": data})

    def api_student_login(self, payload):
        seat_no = str(payload.get('seat_no', '')).strip().zfill(2)
        id_last3 = str(payload.get('id_last3', '')).strip()

        if not seat_no or not id_last3:
            self.send_json({"success": False, "message": "請選擇座號並輸入身分證後3碼"}, status=400)
            return

        conn = get_db()
        student = conn.execute(
            "SELECT id, class_name, seat_no, name, id_last3 FROM students WHERE seat_no = ?",
            (seat_no,)
        ).fetchone()
        conn.close()

        if not student:
            self.send_json({"success": False, "message": f"查無座號 {seat_no} 號之學生資料"}, status=404)
            return

        if student['id_last3'].lower() != id_last3.lower():
            self.send_json({"success": False, "message": "身分證後3碼不正確，請重新輸入！"}, status=401)
            return

        student_info = {
            "id": student["id"],
            "class_name": student["class_name"],
            "seat_no": student["seat_no"],
            "name": student["name"]
        }
        self.send_json({"success": True, "student": student_info})

    def api_get_student_assignments(self, subject_code, student_id):
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM assignments WHERE subject_code = ? AND is_active = 1 ORDER BY id DESC",
            (subject_code,)
        ).fetchall()

        # Fetch unit titles mapping
        unit_rows = conn.execute("SELECT code, title FROM units WHERE subject_code = ?", (subject_code,)).fetchall()
        unit_map = {r['code']: r['title'] for r in unit_rows}

        assignments = []
        for r in rows:
            unit_codes = json.loads(r['unit_codes_json'])
            unit_titles = [unit_map.get(c, c) for c in unit_codes]

            item = {
                "id": r["id"],
                "title": r["title"],
                "subject_code": r["subject_code"],
                "unit_codes": unit_codes,
                "unit_titles": unit_titles,
                "question_count": r["question_count"],
                "created_at": r["created_at"],
                "created_by": r["created_by"],
                "attempts_count": 0,
                "best_score": None,
                "latest_score": None
            }

            if student_id:
                recs = conn.execute(
                    "SELECT score, completed_at FROM exam_records WHERE assignment_id = ? AND student_id = ? ORDER BY completed_at DESC",
                    (r["id"], student_id)
                ).fetchall()
                if recs:
                    item["attempts_count"] = len(recs)
                    item["best_score"] = max(rec["score"] for rec in recs)
                    item["latest_score"] = recs[0]["score"]
                    item["latest_at"] = recs[0]["completed_at"]

            assignments.append(item)

        conn.close()
        self.send_json({"success": True, "assignments": assignments})

    def api_start_exam(self, assignment_id, student_id):
        if not assignment_id or not student_id:
            self.send_json({"success": False, "message": "缺少 assignment_id 或 student_id"}, status=400)
            return

        conn = get_db()
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            conn.close()
            self.send_json({"success": False, "message": "查無此學生"}, status=404)
            return

        assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not assignment:
            conn.close()
            self.send_json({"success": False, "message": "查無此測驗項目"}, status=404)
            return

        unit_codes = json.loads(assignment['unit_codes_json'])
        placeholders = ','.join(['?'] * len(unit_codes))

        # Get questions matching units
        query = f"""
        SELECT q.id, q.unit_code, u.title as unit_title, q.question, q.option_a, q.option_b, q.option_c, q.option_d, q.answer, q.explanation
        FROM questions q
        LEFT JOIN units u ON q.unit_code = u.code
        WHERE q.unit_code IN ({placeholders})
        """
        all_questions = conn.execute(query, unit_codes).fetchall()
        conn.close()

        if not all_questions:
            self.send_json({"success": False, "message": "目前選取的單元尚無題庫"}, status=400)
            return

        # Randomly sample question_count questions
        q_count = min(assignment['question_count'], len(all_questions))
        selected = random.sample(list(all_questions), q_count)

        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "student_id": int(student_id),
            "seat_no": student["seat_no"],
            "student_name": student["name"],
            "assignment_id": int(assignment_id),
            "assignment_title": assignment["title"],
            "subject_code": assignment["subject_code"],
            "start_time": time.time(),
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "questions": {}
        }

        client_questions = []
        for idx, q in enumerate(selected):
            qid = str(q['id'])
            session_data["questions"][qid] = {
                "id": q["id"],
                "question": q["question"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "answer": q["answer"],
                "explanation": q["explanation"],
                "unit_title": q["unit_title"]
            }

            client_questions.append({
                "number": idx + 1,
                "id": q["id"],
                "unit_title": q["unit_title"],
                "question": q["question"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"]
            })

        EXAM_SESSIONS[session_id] = session_data

        self.send_json({
            "success": True,
            "session_id": session_id,
            "assignment_id": int(assignment_id),
            "assignment_title": assignment["title"],
            "total_questions": len(client_questions),
            "questions": client_questions
        })

    def api_submit_exam(self, payload):
        session_id = payload.get('session_id')
        user_answers = payload.get('answers', {})

        session = EXAM_SESSIONS.get(session_id)
        if not session:
            self.send_json({"success": False, "message": "測驗階段已失效或已逾期，請重新開始測驗"}, status=400)
            return

        end_time = time.time()
        duration_seconds = max(1, int(end_time - session["start_time"]))
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        total_questions = len(session["questions"])
        correct_count = 0
        details = []

        for qid, q in session["questions"].items():
            user_ans = str(user_answers.get(qid, '')).strip().upper()
            is_correct = (user_ans == q["answer"])
            if is_correct:
                correct_count += 1

            details.append({
                "question_id": q["id"],
                "question": q["question"],
                "unit_title": q["unit_title"],
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "user_answer": user_ans,
                "correct_answer": q["answer"],
                "is_correct": is_correct,
                "explanation": q["explanation"]
            })

        score = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0

        # Save to DB
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO exam_records (
            assignment_id, student_id, seat_no, student_name, subject_code,
            score, total_questions, correct_count, duration_seconds,
            started_at, completed_at, answers_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["assignment_id"],
            session["student_id"],
            session["seat_no"],
            session["student_name"],
            session["subject_code"],
            score,
            total_questions,
            correct_count,
            duration_seconds,
            session["started_at"],
            completed_at,
            json.dumps(details, ensure_ascii=False)
        ))
        record_id = cursor.lastrowid
        conn.commit()

        # Count total attempts for this student on this assignment
        attempts_count = conn.execute(
            "SELECT COUNT(*), MAX(score) FROM exam_records WHERE assignment_id = ? AND student_id = ?",
            (session["assignment_id"], session["student_id"])
        ).fetchone()
        conn.close()

        # Clean session
        del EXAM_SESSIONS[session_id]

        self.send_json({
            "success": True,
            "record_id": record_id,
            "score": score,
            "correct_count": correct_count,
            "total_questions": total_questions,
            "duration_seconds": duration_seconds,
            "completed_at": completed_at,
            "attempts_count": attempts_count[0],
            "best_score": attempts_count[1],
            "details": details
        })

    def api_get_student_history(self, student_id, assignment_id):
        if not student_id:
            self.send_json({"success": False, "message": "缺少 student_id"}, status=400)
            return

        conn = get_db()
        sql = """
        SELECT r.id, r.assignment_id, COALESCE(r.subject_code, a.subject_code) as subject_code,
               COALESCE(s.name, '綜合') as subject_name, COALESCE(a.title, '隨機測驗') as assignment_title,
               r.score, r.total_questions, r.correct_count, r.duration_seconds, r.completed_at
        FROM exam_records r
        LEFT JOIN assignments a ON r.assignment_id = a.id
        LEFT JOIN subjects s ON COALESCE(r.subject_code, a.subject_code) = s.code
        WHERE r.student_id = ?
        """
        params = [student_id]
        if assignment_id:
            sql += " AND r.assignment_id = ?"
            params.append(assignment_id)
        sql += " ORDER BY r.id DESC"

        rows = conn.execute(sql, params).fetchall()
        data = [dict(r) for r in rows]
        conn.close()
        self.send_json({"success": True, "history": data})

    def api_get_student_summary(self, student_id):
        if not student_id:
            self.send_json({"success": False, "message": "缺少 student_id"}, status=400)
            return

        conn = get_db()
        student = conn.execute("SELECT id, class_name, seat_no, name FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            conn.close()
            self.send_json({"success": False, "message": "查無此學生"}, status=404)
            return

        subjects_rows = conn.execute("SELECT code, name, description FROM subjects ORDER BY rowid ASC").fetchall()

        subject_icons = {
            'chinese': '📖',
            'english': '🇬🇧',
            'math': '📐',
            'physics_chem': '⚗️',
            'earth_science': '🌍',
            'history': '🏛️',
            'geography': '🗺️',
            'civics': '⚖️'
        }

        subject_summaries = []
        total_attempts = 0
        best_scores = []
        mastered_count = 0
        passed_count = 0
        needs_improvement_count = 0

        for sub in subjects_rows:
            scode = sub['code']
            # Find all exam records of this student for this subject
            recs = conn.execute("""
                SELECT r.score, r.total_questions, r.correct_count, r.duration_seconds, r.completed_at
                FROM exam_records r
                LEFT JOIN assignments a ON r.assignment_id = a.id
                WHERE r.student_id = ? AND (r.subject_code = ? OR a.subject_code = ?)
                ORDER BY r.completed_at DESC
            """, (student_id, scode, scode)).fetchall()

            # Find active assignment for this subject
            assign = conn.execute(
                "SELECT id, title, question_count FROM assignments WHERE subject_code = ? AND is_active = 1 ORDER BY id DESC LIMIT 1",
                (scode,)
            ).fetchone()

            attempts_count = len(recs)
            total_attempts += attempts_count

            if attempts_count > 0:
                all_scores = [r['score'] for r in recs]
                best = max(all_scores)
                latest = recs[0]['score']
                latest_at = recs[0]['completed_at']
                avg_score = round(sum(all_scores) / attempts_count, 1)
                best_scores.append(best)

                if best >= 90:
                    status = "精熟"
                    status_code = "master"
                    mastered_count += 1
                    passed_count += 1
                elif best >= 60:
                    status = "基礎"
                    status_code = "pass"
                    passed_count += 1
                else:
                    status = "待加強"
                    status_code = "needs_improvement"
                    needs_improvement_count += 1
            else:
                best = None
                latest = None
                latest_at = None
                avg_score = None
                status = "未應試"
                status_code = "untested"

            item = {
                "code": scode,
                "name": sub['name'],
                "icon": subject_icons.get(scode, '📝'),
                "description": sub['description'],
                "attempts_count": attempts_count,
                "best_score": best,
                "latest_score": latest,
                "latest_at": latest_at,
                "average_score": avg_score,
                "status": status,
                "status_code": status_code,
                "active_assignment_id": assign['id'] if assign else None,
                "assignment_title": assign['title'] if assign else None,
                "question_count": assign['question_count'] if assign else 10
            }
            subject_summaries.append(item)

        # Full history across all subjects
        history_rows = conn.execute("""
            SELECT r.id, r.assignment_id, COALESCE(r.subject_code, a.subject_code) as subject_code,
                   COALESCE(s.name, '綜合') as subject_name, COALESCE(a.title, '隨機測驗') as assignment_title,
                   r.score, r.total_questions, r.correct_count, r.duration_seconds, r.completed_at
            FROM exam_records r
            LEFT JOIN assignments a ON r.assignment_id = a.id
            LEFT JOIN subjects s ON COALESCE(r.subject_code, a.subject_code) = s.code
            WHERE r.student_id = ?
            ORDER BY r.completed_at DESC
        """, (student_id,)).fetchall()
        history_data = [dict(hr) for hr in history_rows]

        conn.close()

        tested_count = len(best_scores)
        overall_avg_best = round(sum(best_scores) / tested_count, 1) if tested_count > 0 else 0

        self.send_json({
            "success": True,
            "student": {
                "id": student["id"],
                "class_name": student["class_name"],
                "seat_no": student["seat_no"],
                "name": student["name"]
            },
            "overall": {
                "total_subjects": len(subjects_rows),
                "tested_subjects_count": tested_count,
                "untested_subjects_count": len(subjects_rows) - tested_count,
                "total_attempts": total_attempts,
                "average_best_score": overall_avg_best,
                "mastered_count": mastered_count,
                "passed_count": passed_count,
                "needs_improvement_count": needs_improvement_count
            },
            "subjects": subject_summaries,
            "history": history_data
        })

    # --- Teacher APIs ---
    def api_teacher_login(self, payload):
        username = str(payload.get('username', '')).strip()
        password = str(payload.get('password', '')).strip()

        conn = get_db()
        teacher = conn.execute(
            "SELECT id, username, name, role FROM teachers WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()
        conn.close()

        if not teacher:
            self.send_json({"success": False, "message": "帳號或密碼錯誤！"}, status=401)
            return

        self.send_json({
            "success": True,
            "user": {
                "id": teacher["id"],
                "username": teacher["username"],
                "name": teacher["name"],
                "role": teacher["role"]
            }
        })

    def api_get_teacher_overview(self, assignment_id):
        conn = get_db()

        # Default to latest active assignment if not provided
        if not assignment_id:
            latest = conn.execute("SELECT id FROM assignments WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
            if latest:
                assignment_id = latest["id"]

        assignment = None
        if assignment_id:
            assignment = conn.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()

        students = conn.execute("SELECT * FROM students ORDER BY seat_no ASC").fetchall()

        overview_list = []
        scores_for_stats = []
        tested_students = 0

        for s in students:
            recs = []
            if assignment_id:
                recs = conn.execute(
                    "SELECT id, score, total_questions, correct_count, duration_seconds, completed_at FROM exam_records WHERE assignment_id = ? AND student_id = ? ORDER BY completed_at DESC",
                    (assignment_id, s["id"])
                ).fetchall()
            else:
                recs = conn.execute(
                    "SELECT id, score, total_questions, correct_count, duration_seconds, completed_at FROM exam_records WHERE student_id = ? ORDER BY completed_at DESC",
                    (s["id"],)
                ).fetchall()

            attempts = len(recs)
            best_score = max([r["score"] for r in recs]) if recs else None
            latest_score = recs[0]["score"] if recs else None
            last_tested_at = recs[0]["completed_at"] if recs else None

            if attempts > 0:
                tested_students += 1
                scores_for_stats.append(best_score)

            overview_list.append({
                "student_id": s["id"],
                "seat_no": s["seat_no"],
                "name": s["name"],
                "id_last3": s["id_last3"],
                "attempts_count": attempts,
                "best_score": best_score,
                "latest_score": latest_score,
                "last_tested_at": last_tested_at,
                "history": [dict(r) for r in recs]
            })

        total_students = len(students)
        untested_students = total_students - tested_students
        avg_best_score = round(sum(scores_for_stats) / len(scores_for_stats), 1) if scores_for_stats else 0
        pass_count = sum(1 for sc in scores_for_stats if sc >= 60)
        excellent_count = sum(1 for sc in scores_for_stats if sc >= 90)

        pass_rate = round((pass_count / total_students) * 100, 1) if total_students > 0 else 0
        tested_rate = round((tested_students / total_students) * 100, 1) if total_students > 0 else 0

        stats = {
            "total_students": total_students,
            "tested_students": tested_students,
            "untested_students": untested_students,
            "tested_rate": tested_rate,
            "avg_best_score": avg_best_score,
            "pass_count": pass_count,
            "pass_rate": pass_rate,
            "excellent_count": excellent_count,
            "highest_in_class": max(scores_for_stats) if scores_for_stats else 0
        }

        conn.close()
        self.send_json({
            "success": True,
            "assignment": dict(assignment) if assignment else None,
            "stats": stats,
            "students": overview_list
        })

    def api_get_teacher_student_records(self, student_id, assignment_id):
        if not student_id:
            self.send_json({"success": False, "message": "缺少 student_id"}, status=400)
            return

        conn = get_db()
        sql = "SELECT * FROM exam_records WHERE student_id = ?"
        params = [student_id]
        if assignment_id:
            sql += " AND assignment_id = ?"
            params.append(assignment_id)
        sql += " ORDER BY id DESC"

        rows = conn.execute(sql, params).fetchall()
        records = []
        for r in rows:
            rec = dict(r)
            rec["answers"] = json.loads(rec["answers_json"])
            del rec["answers_json"]
            records.append(rec)

        conn.close()
        self.send_json({"success": True, "records": records})

    def api_get_teacher_assignments(self, subject):
        conn = get_db()
        sql = "SELECT * FROM assignments"
        params = []
        if subject:
            sql += " WHERE subject_code = ?"
            params.append(subject)
        sql += " ORDER BY is_active DESC, id DESC"

        rows = conn.execute(sql, params).fetchall()

        unit_rows = conn.execute("SELECT code, title FROM units").fetchall()
        unit_map = {r['code']: r['title'] for r in unit_rows}

        assignments = []
        for r in rows:
            unit_codes = json.loads(r['unit_codes_json'])
            unit_titles = [unit_map.get(c, c) for c in unit_codes]

            # Count attempts
            c_row = conn.execute("SELECT COUNT(*), COUNT(DISTINCT student_id) FROM exam_records WHERE assignment_id = ?", (r["id"],)).fetchone()

            assignments.append({
                "id": r["id"],
                "title": r["title"],
                "subject_code": r["subject_code"],
                "unit_codes": unit_codes,
                "unit_titles": unit_titles,
                "question_count": r["question_count"],
                "created_at": r["created_at"],
                "created_by": r["created_by"],
                "is_active": r["is_active"],
                "total_submissions": c_row[0],
                "distinct_students": c_row[1]
            })

        conn.close()
        self.send_json({"success": True, "assignments": assignments})

    def api_create_assignment(self, payload):
        title = str(payload.get('title', '')).strip()
        subject_code = str(payload.get('subject_code', 'chinese')).strip()
        unit_codes = payload.get('unit_codes', [])
        question_count = int(payload.get('question_count', 10))
        created_by = str(payload.get('created_by', 'Jenny 老師')).strip()

        if not title:
            self.send_json({"success": False, "message": "請填寫測驗名稱"}, status=400)
            return

        if not unit_codes:
            self.send_json({"success": False, "message": "請至少選取一個測驗單元"}, status=400)
            return

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO assignments (title, subject_code, unit_codes_json, question_count, created_at, created_by, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (title, subject_code, json.dumps(unit_codes, ensure_ascii=False), question_count, created_at, created_by))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.send_json({"success": True, "assignment_id": new_id, "message": "命題發布成功！"})

    def api_toggle_assignment(self, payload):
        aid = payload.get('assignment_id')
        is_active = payload.get('is_active', 1)

        conn = get_db()
        conn.execute("UPDATE assignments SET is_active = ? WHERE id = ?", (1 if is_active else 0, aid))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": "測驗狀態更新成功！"})

    def api_get_teacher_units(self, subject):
        conn = get_db()
        sql = """
        SELECT u.id, u.subject_code, u.code, u.title, u.description,
               COUNT(q.id) as question_count
        FROM units u
        LEFT JOIN questions q ON u.code = q.unit_code
        """
        params = []
        if subject:
            sql += " WHERE u.subject_code = ?"
            params.append(subject)
        sql += " GROUP BY u.code ORDER BY u.id ASC"

        rows = conn.execute(sql, params).fetchall()
        data = [dict(r) for r in rows]
        conn.close()
        self.send_json({"success": True, "units": data})

    def api_create_unit(self, payload):
        subject_code = str(payload.get('subject_code', 'chinese')).strip()
        code = str(payload.get('code', '')).strip().upper()
        title = str(payload.get('title', '')).strip()
        desc = str(payload.get('description', '')).strip()

        if not code or not title:
            self.send_json({"success": False, "message": "請輸入單元代碼與單元名稱"}, status=400)
            return

        conn = get_db()
        try:
            conn.execute("""
            INSERT INTO units (subject_code, code, title, description)
            VALUES (?, ?, ?, ?)
            """, (subject_code, code, title, desc))
            conn.commit()
            conn.close()
            self.send_json({"success": True, "message": "單元新增成功！"})
        except sqlite3.IntegrityError:
            conn.close()
            self.send_json({"success": False, "message": f"單元代碼 {code} 已存在，請使用不同代碼"}, status=400)

    def api_get_teacher_questions(self, unit_code):
        conn = get_db()
        sql = "SELECT * FROM questions"
        params = []
        if unit_code:
            sql += " WHERE unit_code = ?"
            params.append(unit_code)
        sql += " ORDER BY id ASC"

        rows = conn.execute(sql, params).fetchall()
        data = [dict(r) for r in rows]
        conn.close()
        self.send_json({"success": True, "questions": data})

    def api_create_question(self, payload):
        unit_code = str(payload.get('unit_code', '')).strip()
        question = str(payload.get('question', '')).strip()
        oa = str(payload.get('option_a', '')).strip()
        ob = str(payload.get('option_b', '')).strip()
        oc = str(payload.get('option_c', '')).strip()
        od = str(payload.get('option_d', '')).strip()
        ans = str(payload.get('answer', '')).strip().upper()
        exp = str(payload.get('explanation', '')).strip()

        if not unit_code or not question or not oa or not ob or not oc or not od or not ans:
            self.send_json({"success": False, "message": "所有題目選項與答案皆為必填！"}, status=400)
            return

        if ans not in ['A', 'B', 'C', 'D']:
            self.send_json({"success": False, "message": "正確答案必須為 A、B、C 或 D"}, status=400)
            return

        conn = get_db()
        conn.execute("""
        INSERT INTO questions (unit_code, question, option_a, option_b, option_c, option_d, answer, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (unit_code, question, oa, ob, oc, od, ans, exp))
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": "題目新增成功！"})

    def api_admin_reset_records(self, payload):
        admin_pass = str(payload.get('password', '')).strip()
        assignment_id = payload.get('assignment_id')

        if admin_pass != '123456789':
            self.send_json({"success": False, "message": "管理員密碼驗證失敗！"}, status=403)
            return

        conn = get_db()
        if assignment_id:
            conn.execute("DELETE FROM exam_records WHERE assignment_id = ?", (assignment_id,))
        else:
            conn.execute("DELETE FROM exam_records")
        conn.commit()
        conn.close()

        self.send_json({"success": True, "message": "已成功重置測驗成績紀錄！"})

    def api_export_csv(self, assignment_id):
        conn = get_db()
        assignment_title = "全部測驗"
        if assignment_id:
            a = conn.execute("SELECT title FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
            if a:
                assignment_title = a["title"]

        students = conn.execute("SELECT * FROM students ORDER BY seat_no ASC").fetchall()

        # Build CSV lines with BOM for Excel UTF-8 compatibility
        lines = []
        # Header
        lines.append(f"# 115頭前國中 九年七班 測驗成績總表")
        lines.append(f"# 測驗項目: {assignment_title}")
        lines.append(f"# 計分標準: 採歷次最高分計分 (重複測驗隨機抽10題)")
        lines.append(f"# 匯出時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append('"座號","姓名","身分證後3碼","測驗次數","採計成績(最高分)","最新得分","最近測驗時間","測驗狀態"')

        for s in students:
            if assignment_id:
                recs = conn.execute(
                    "SELECT score, completed_at FROM exam_records WHERE assignment_id = ? AND student_id = ? ORDER BY completed_at DESC",
                    (assignment_id, s["id"])
                ).fetchall()
            else:
                recs = conn.execute(
                    "SELECT score, completed_at FROM exam_records WHERE student_id = ? ORDER BY completed_at DESC",
                    (s["id"],)
                ).fetchall()

            attempts = len(recs)
            best_score = max([r["score"] for r in recs]) if recs else 0
            latest_score = recs[0]["score"] if recs else 0
            last_tested = recs[0]["completed_at"] if recs else "--"
            status = "已完成" if attempts > 0 else "未應試"

            best_str = f"{best_score:.1f}" if attempts > 0 else "--"
            latest_str = f"{latest_score:.1f}" if attempts > 0 else "--"

            lines.append(f'"{s["seat_no"]}","{s["name"]}","{s["id_last3"]}",{attempts},{best_str},{latest_str},"{last_tested}","{status}"')

        conn.close()

        csv_content = "\ufeff" + "\r\n".join(lines)
        csv_bytes = csv_content.encode('utf-8')

        filename = f"九年七班_測驗成績總表_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        quoted_filename = urllib.parse.quote(filename)

        self.send_response(200)
        self.send_header('Content-Type', 'text/csv; charset=utf-8')
        self.send_header('Content-Disposition', f'attachment; filename="{quoted_filename}"; filename*=UTF-8\'\'{quoted_filename}')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Content-Length', str(len(csv_bytes)))
        self.end_headers()
        self.wfile.write(csv_bytes)

def run_server(port=PORT):
    server_address = ('', port)
    httpd = http.server.ThreadingHTTPServer(server_address, QuizRequestHandler)
    print("=" * 60)
    print(f"[ONLINE QUIZ SYSTEM] Started successfully!")
    print(f"[URL] http://localhost:{port}")
    print(f"[DIR] {BASE_DIR}")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == '__main__':
    run_server()
