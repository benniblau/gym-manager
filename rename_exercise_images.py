#!/usr/bin/env python3
"""
Rename exercise images to match exercise names and update database
"""

import sqlite3
import os
import shutil

DB_PATH = 'exercises.db'
IMAGES_DIR = 'app/static/images'

# Mapping of exercise ID to new image filename (kebab-case)
EXERCISE_IMAGE_MAPPING = {
    2034: 'standing-forward-bend.png',
    2035: 'standing-side-bend.png',
    2036: 'wide-leg-forward-bend.png',
    2037: 'side-lunge-stretch.png',
    2038: 'cat-pose.png',
    2039: 'half-kneeling-hip-flexor-stretch.png',
    2040: 'seated-shin-stretch.png',
    2041: 'side-lying-quadriceps-stretch.png',
    2042: 'seated-hurdle-stretch-with-nerve-mobilization.png',
    2043: 'overhead-chest-stretch-with-rope.png',
    2044: 'hip-flexor-and-thigh-stretch-with-rope.png',
    2045: 'butterfly-stretch.png',
    2046: 'pigeon-pose.png',
    2047: 'downward-dog.png',
    2048: 'foam-roller-thoracic-spine-mobilization.png',
    2049: 'supine-trunk-rotation-stretch.png',
    2050: 'plow-stretch.png',
    2051: 'overhead-lat-stretch.png'
}


def rename_image_files():
    """Rename image files from Screenshot names to exercise names"""
    print("=" * 60)
    print("Renaming Exercise Image Files")
    print("=" * 60)
    print()

    # Connect to database to get current image filenames
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    renamed_count = 0
    skipped_count = 0

    for exercise_id, new_filename in EXERCISE_IMAGE_MAPPING.items():
        # Get current image filename from database
        cursor.execute('SELECT name, image1_url FROM exercises WHERE id = ?', (exercise_id,))
        result = cursor.fetchone()

        if not result:
            print(f"⚠️  Exercise ID {exercise_id} not found in database")
            skipped_count += 1
            continue

        exercise_name, old_filename = result

        if not old_filename:
            print(f"⚠️  No image for {exercise_name} (ID: {exercise_id})")
            skipped_count += 1
            continue

        # Construct full paths
        old_path = os.path.join(IMAGES_DIR, old_filename)
        new_path = os.path.join(IMAGES_DIR, new_filename)

        # Check if old file exists
        if not os.path.exists(old_path):
            print(f"⚠️  Image file not found: {old_path}")
            skipped_count += 1
            continue

        # Check if new file already exists
        if os.path.exists(new_path) and old_path != new_path:
            print(f"⚠️  Target file already exists: {new_path}")
            skipped_count += 1
            continue

        # Rename the file
        try:
            if old_path != new_path:
                shutil.move(old_path, new_path)
                print(f"✓ Renamed: {exercise_name}")
                print(f"  From: {old_filename}")
                print(f"  To:   {new_filename}")
                renamed_count += 1
            else:
                print(f"✓ Already correct: {exercise_name} -> {new_filename}")
                renamed_count += 1
        except Exception as e:
            print(f"❌ Error renaming {exercise_name}: {e}")
            skipped_count += 1

        print()

    conn.close()

    print("=" * 60)
    print(f"✅ Successfully renamed: {renamed_count} files")
    print(f"⚠️  Skipped: {skipped_count} files")
    print("=" * 60)
    print()


def update_database():
    """Update database with new image filenames"""
    print("=" * 60)
    print("Updating Database Image URLs")
    print("=" * 60)
    print()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    updated_count = 0

    for exercise_id, new_filename in EXERCISE_IMAGE_MAPPING.items():
        cursor.execute('SELECT name FROM exercises WHERE id = ?', (exercise_id,))
        result = cursor.fetchone()

        if not result:
            continue

        exercise_name = result[0]

        # Update image1_url with new filename
        cursor.execute('''
            UPDATE exercises
            SET image1_url = ?
            WHERE id = ?
        ''', (new_filename, exercise_id))

        print(f"✓ Updated: {exercise_name}")
        print(f"  Image URL: {new_filename}")
        updated_count += 1

    conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print(f"✅ Successfully updated: {updated_count} exercises")
    print("=" * 60)
    print()


def verify_changes():
    """Verify that images exist and database is updated"""
    print("=" * 60)
    print("Verification")
    print("=" * 60)
    print()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    all_good = True

    for exercise_id, expected_filename in EXERCISE_IMAGE_MAPPING.items():
        cursor.execute('SELECT name, image1_url FROM exercises WHERE id = ?', (exercise_id,))
        result = cursor.fetchone()

        if not result:
            continue

        exercise_name, db_filename = result
        file_path = os.path.join(IMAGES_DIR, expected_filename)

        # Check database
        if db_filename != expected_filename:
            print(f"❌ Database mismatch: {exercise_name}")
            print(f"   Expected: {expected_filename}")
            print(f"   Got:      {db_filename}")
            all_good = False

        # Check file exists
        if not os.path.exists(file_path):
            print(f"❌ File missing: {exercise_name} -> {file_path}")
            all_good = False

    conn.close()

    if all_good:
        print("✅ All images verified successfully!")
        print("   - All database entries updated correctly")
        print("   - All image files exist with correct names")
    else:
        print("⚠️  Some issues found. Please review above.")

    print()


def main():
    """Main function"""
    print("\n")
    print("🖼️  Exercise Image Renaming Tool")
    print()

    # Step 1: Rename files
    rename_image_files()

    # Step 2: Update database
    update_database()

    # Step 3: Verify changes
    verify_changes()

    print("✅ Done! Images have been renamed and database updated.")
    print()


if __name__ == '__main__':
    main()
