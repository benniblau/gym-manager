#!/usr/bin/env python3
"""
Migration Script: Analyze Exercises for Missing Content
Description: Identifies exercises that are missing instructions or have
             placeholder/empty descriptions.

Usage:
    python migrations/analyze_exercises.py [--db-path PATH] [--export FILE]

Options:
    --db-path PATH      Path to exercises.db (default: exercises.db)
    --export FILE       Export exercises needing updates to JSON file
"""

import sqlite3
import json
import argparse
from pathlib import Path


def get_exercises_without_instructions(conn):
    """Find exercises that have no instructions."""
    cursor = conn.execute('''
        SELECT e.id, e.name, e.description, c.name as category
        FROM exercises e
        LEFT JOIN instructions i ON e.id = i.exercise_id
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE i.id IS NULL
        GROUP BY e.id
        ORDER BY e.name
    ''')
    return cursor.fetchall()


def get_exercises_with_placeholder_description(conn):
    """Find exercises with missing or placeholder descriptions."""
    cursor = conn.execute('''
        SELECT e.id, e.name, e.description, c.name as category
        FROM exercises e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE e.description IS NULL
           OR e.description = ''
           OR e.description = 'Strength exercise for overall fitness.'
        ORDER BY e.name
    ''')
    return cursor.fetchall()


def get_exercise_details(conn, exercise_id):
    """Get full details for an exercise including muscles and equipment."""
    # Get primary muscles
    primary = conn.execute('''
        SELECT m.name FROM muscles m
        JOIN exercise_primary_muscles epm ON m.id = epm.muscle_id
        WHERE epm.exercise_id = ?
    ''', (exercise_id,)).fetchall()

    # Get secondary muscles
    secondary = conn.execute('''
        SELECT m.name FROM muscles m
        JOIN exercise_secondary_muscles esm ON m.id = esm.muscle_id
        WHERE esm.exercise_id = ?
    ''', (exercise_id,)).fetchall()

    # Get equipment
    equipment = conn.execute('''
        SELECT eq.name FROM equipment eq
        JOIN exercise_equipment ee ON eq.id = ee.equipment_id
        WHERE ee.exercise_id = ?
    ''', (exercise_id,)).fetchall()

    return {
        'primary_muscles': [m[0] for m in primary],
        'secondary_muscles': [s[0] for s in secondary],
        'equipment': [e[0] for e in equipment]
    }


def analyze(db_path, export_file=None):
    """Run the analysis and optionally export results."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get counts
    total_exercises = conn.execute('SELECT COUNT(*) FROM exercises').fetchone()[0]
    total_instructions = conn.execute('SELECT COUNT(DISTINCT exercise_id) FROM instructions').fetchone()[0]

    print(f"\n{'='*60}")
    print("EXERCISE DATABASE ANALYSIS")
    print(f"{'='*60}")
    print(f"\nTotal exercises in database: {total_exercises}")
    print(f"Exercises with instructions: {total_instructions}")

    # Find exercises without instructions
    no_instructions = get_exercises_without_instructions(conn)
    print(f"\n--- Exercises WITHOUT Instructions: {len(no_instructions)} ---")
    if no_instructions:
        for ex in no_instructions[:10]:  # Show first 10
            print(f"  [{ex['id']}] {ex['name']} ({ex['category'] or 'No category'})")
        if len(no_instructions) > 10:
            print(f"  ... and {len(no_instructions) - 10} more")

    # Find exercises with placeholder descriptions
    placeholder_desc = get_exercises_with_placeholder_description(conn)
    print(f"\n--- Exercises with Missing/Placeholder Descriptions: {len(placeholder_desc)} ---")
    if placeholder_desc:
        for ex in placeholder_desc[:10]:  # Show first 10
            desc_preview = (ex['description'] or 'NULL')[:50]
            print(f"  [{ex['id']}] {ex['name']}: \"{desc_preview}...\"")
        if len(placeholder_desc) > 10:
            print(f"  ... and {len(placeholder_desc) - 10} more")

    # Find exercises needing any update (union of both)
    needs_update_ids = set()
    for ex in no_instructions:
        needs_update_ids.add(ex['id'])
    for ex in placeholder_desc:
        needs_update_ids.add(ex['id'])

    print(f"\n--- TOTAL Exercises Needing Updates: {len(needs_update_ids)} ---")

    # Export if requested
    if export_file:
        export_data = {}
        for ex in no_instructions:
            details = get_exercise_details(conn, ex['id'])
            export_data[ex['id']] = {
                'name': ex['name'],
                'category': ex['category'],
                'current_description': ex['description'],
                'needs_instructions': True,
                'needs_description': ex['id'] in [p['id'] for p in placeholder_desc],
                **details
            }

        # Add exercises that only need description updates
        for ex in placeholder_desc:
            if ex['id'] not in export_data:
                details = get_exercise_details(conn, ex['id'])
                export_data[ex['id']] = {
                    'name': ex['name'],
                    'category': ex['category'],
                    'current_description': ex['description'],
                    'needs_instructions': False,
                    'needs_description': True,
                    **details
                }

        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        print(f"\nExported {len(export_data)} exercises to: {export_file}")

    print(f"\n{'='*60}\n")
    conn.close()

    return {
        'total': total_exercises,
        'without_instructions': len(no_instructions),
        'placeholder_descriptions': len(placeholder_desc),
        'needs_update': len(needs_update_ids)
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze exercises for missing content')
    parser.add_argument('--db-path', default='exercises.db', help='Path to exercises.db')
    parser.add_argument('--export', help='Export exercises needing updates to JSON file')
    args = parser.parse_args()

    if not Path(args.db_path).exists():
        print(f"Error: Database not found at {args.db_path}")
        exit(1)

    analyze(args.db_path, args.export)
