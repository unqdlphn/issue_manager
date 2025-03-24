import sqlite3
import datetime

DATABASE_FILE = "issues.db"

class Issue:
    def __init__(self, title, description, status="Open", resolution=None, tags=None):
        self.title = title
        self.description = description
        self.status = status
        self.resolution = resolution
        self.date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.modified = self.date
        self.tags = tags if tags else []

    def save(self):
        conn = sqlite3.connect(DATABASE_FILE)
        try:
            with conn:
                conn.execute('''INSERT INTO issues (title, description, status, resolution, date, modified, tags)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                             (self.title, self.description, self.status, self.resolution,
                              self.date, self.modified, ", ".join(self.tags)))
        except sqlite3.Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

    @staticmethod
    def load_all():
        conn = sqlite3.connect(DATABASE_FILE)
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM issues")
                rows = cur.fetchall()
                issues = []
                for row in rows:
                    issue = Issue(row[1], row[2], row[3], row[4], row[7].split(", ") if row[7] else [])
                    issue.id = row[0]
                    issue.date = row[5]
                    issue.modified = row[6]
                    issues.append(issue)
                return issues
        except sqlite3.Error as e:
            print(e)
            return []
        finally:
            if conn:
                conn.close()

    def update(self):
        conn = sqlite3.connect(DATABASE_FILE)
        try:
            with conn:
                conn.execute('''UPDATE issues
                                SET title = ?, description = ?, status = ?, resolution = ?, modified = ?, tags = ?
                                WHERE id = ?''',
                             (self.title, self.description, self.status, self.resolution,
                              datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ", ".join(self.tags), self.id))
        except sqlite3.Error as e:
            print(e)
        finally:
            if conn:
                conn.close()

    @staticmethod
    def delete(issue_id):
        conn = sqlite3.connect(DATABASE_FILE)
        try:
            with conn:
                conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
        except sqlite3.Error as e:
            print(e)
        finally:
            if conn:
                conn.close()