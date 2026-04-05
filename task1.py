#!/usr/bin/env python3
"""
PAM Ops Engineer Task 1 - Student Grades
Connects to Docker container via SSH, upgrades sql.jar from v1.0 to v1.1,
then queries the DB and displays student grades in a formatted table.

Requirements:
    pip install paramiko

Usage:
    python3 task1.py [--host HOST] [--port PORT]

Defaults: host=localhost, port=2222 (as set up by: docker run -p 2222:22 pam-ops)
"""

import sys
import argparse
import paramiko


SSH_USER = "root"
SSH_PASS = "sshpass1"
APPS_DIR = "/opt/local/apps"
JAVA = "/opt/java/openjdk/bin/java"


def run(client, cmd):
    """Run a command over SSH, return (stdout, stderr) as strings."""
    _, stdout, stderr = client.exec_command(cmd)
    return stdout.read().decode(), stderr.read().decode()


def parse_row(line):
    """Parse sql.jar output line: '1 (id), Biology (name)' → {'id': '1', 'name': 'Biology'}"""
    result = {}
    for part in line.split(", "):
        part = part.strip()
        if " (" in part and part.endswith(")"):
            value, col = part.rsplit(" (", 1)
            result[col.rstrip(")")] = value.strip()
    return result


def part1_version_change(client):
    """Part 1: Check sql.jar version, upgrade if needed, verify."""
    print("=== Part 1: sql.jar Version Change ===\n")

    # Check current version and functionality
    ver_out, _ = run(client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -version 2>&1")
    print(ver_out.strip())

    query_out, query_err = run(
        client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -query 'select * from classes' 2>&1"
    )
    if query_err.strip():
        print(query_err.strip())
    else:
        print(query_out.strip())

    # Brownie point: skip if already v1.1
    if "1.1" in ver_out:
        print("\nsql.jar is already version 1.1 — no upgrade needed.")
        return

    print("\n---")
    print("Removing sql.jar version 1.0")
    run(client, f"rm {APPS_DIR}/sql.jar")

    print("Changing to sql.jar version 1.1")
    out, err = run(
        client,
        f"zstd -d {APPS_DIR}/versions/sql.jar.zst -o {APPS_DIR}/sql.jar 2>&1",
    )
    if err.strip():
        print(f"zstd error: {err.strip()}")
        sys.exit(1)
    print("---\n")

    # Verify new version and functionality
    ver_out, _ = run(client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -version 2>&1")
    print(ver_out.strip())

    query_out, query_err = run(
        client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -query 'select * from classes' 2>&1"
    )
    output = (query_err + query_out).strip()
    for line in output.splitlines():
        # Remove surrounding brackets if present: [1 (id), Biology (name)] → 1 (id), Biology (name)
        line = line.strip().lstrip("[").rstrip("]")
        row = parse_row(line)
        if row:
            print(f"{row.get('id', '')} (id), {row.get('name', '')} (name)")


def part2_grades_table(client):
    """Part 2: Query DB and display student grades in a formatted table."""
    print("\n=== Part 2: Student Grades Table ===\n")

    # Fetch students
    out, _ = run(client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -query 'SELECT * FROM students' 2>&1")
    students = {}  # id → {name, age}
    for line in out.splitlines():
        line = line.strip().lstrip("[").rstrip("]")
        row = parse_row(line)
        if row and "id" in row:
            students[row["id"]] = {"name": row["name"], "age": row["age"]}

    # Fetch classes
    out, _ = run(client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -query 'SELECT * FROM classes' 2>&1")
    classes = {}  # id → name
    class_order = []  # preserve insertion order
    for line in out.splitlines():
        line = line.strip().lstrip("[").rstrip("]")
        row = parse_row(line)
        if row and "id" in row:
            classes[row["id"]] = row["name"]
            class_order.append(row["id"])

    # Fetch grades
    out, _ = run(client, f"cd {APPS_DIR} && /opt/java/openjdk/bin/java -jar sql.jar -query 'SELECT * FROM grades' 2>&1")
    grades = {}  # (student_id, class_id) → grade
    for line in out.splitlines():
        line = line.strip().lstrip("[").rstrip("]")
        row = parse_row(line)
        if row and "student_id" in row:
            grades[(row["student_id"], row["class_id"])] = row["grade"]

    # Build table
    col_headers = [f"{classes[cid]}" for cid in class_order]
    header_first = "Student (age)"

    # Calculate column widths
    rows_data = []
    for sid, info in sorted(students.items(), key=lambda x: int(x[0])):
        name_cell = f"{info['name']} ({info['age']})"
        grade_cells = [grades.get((sid, cid), "-") for cid in class_order]
        rows_data.append((name_cell, grade_cells))

    col0_width = max(len(header_first), max(len(r[0]) for r in rows_data))
    col_widths = [
        max(len(col_headers[i]), max(len(r[1][i]) for r in rows_data))
        for i in range(len(class_order))
    ]

    def fmt_row(first, rest):
        cells = [first.ljust(col0_width)] + [
            rest[i].center(col_widths[i]) for i in range(len(rest))
        ]
        return "| " + " | ".join(cells) + " |"

    sep = (
        "+-"
        + "-" * col0_width
        + "-+-"
        + "-+-".join("-" * w for w in col_widths)
        + "-+"
    )

    # Print header
    print(fmt_row(header_first, [h.center(col_widths[i]) for i, h in enumerate(col_headers)]))
    print(sep)

    # Print student rows
    for name_cell, grade_cells in rows_data:
        print(fmt_row(name_cell, grade_cells))


def main():
    parser = argparse.ArgumentParser(description="PAM Ops Task 1 - Student Grades")
    parser.add_argument("--host", default="localhost", help="SSH host (default: localhost)")
    parser.add_argument("--port", type=int, default=2222, help="SSH port (default: 2222)")
    args = parser.parse_args()

    # Connect via SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=args.host,
            port=args.port,
            username=SSH_USER,
            password=SSH_PASS,
            timeout=10,
        )
    except Exception as exc:
        # Exception handling: connection failed (simulate by stopping container)
        print(f"ERROR: Could not connect to SSH server at {args.host}:{args.port}")
        print(f"       {exc}")
        print("\nPlease ensure the Docker container is running:")
        print("  docker run -d -p 2222:22 --name pam-ops-container pam-ops")
        sys.exit(1)

    try:
        part1_version_change(client)
        part2_grades_table(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
