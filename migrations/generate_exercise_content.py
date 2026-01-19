#!/usr/bin/env python3
"""
Migration Script: Generate Exercise Content using Claude API
Description: Generates professional descriptions and step-by-step instructions
             for exercises that are missing content.

Usage:
    python migrations/generate_exercise_content.py --input FILE --output FILE [options]

Options:
    --input FILE        JSON file with exercises to update (from analyze_exercises.py)
    --output FILE       Output JSON file for generated content
    --limit N           Only process first N exercises (for testing)
    --resume            Resume from existing output file
    --dry-run           Show what would be done without making API calls

Environment:
    ANTHROPIC_API_KEY   Required API key for Claude
"""

import anthropic
import json
import argparse
import time
import sys
from pathlib import Path


PROMPT_TEMPLATE = """Generate professional exercise content for the following exercise.

Exercise Name: {name}
Category: {category}
Primary Muscles: {primary_muscles}
Secondary Muscles: {secondary_muscles}
Equipment: {equipment}

Please provide:
1. A concise description (1-2 sentences) that explains what the exercise is and its primary benefits
2. Step-by-step instructions (4-7 steps) for performing the exercise correctly

Return your response as valid JSON in this exact format:
{{
  "description": "Your 1-2 sentence description here",
  "instructions": [
    "Step 1 instruction",
    "Step 2 instruction",
    "Step 3 instruction"
  ]
}}

Important:
- Be specific and accurate
- Use professional fitness terminology
- Instructions should be clear and actionable
- Do not include step numbers in the instruction text (they will be added automatically)
- Return ONLY the JSON, no other text"""


def generate_content(client, exercise):
    """Generate content for a single exercise using Claude API."""
    prompt = PROMPT_TEMPLATE.format(
        name=exercise['name'],
        category=exercise.get('category') or 'General',
        primary_muscles=', '.join(exercise.get('primary_muscles', [])) or 'Various',
        secondary_muscles=', '.join(exercise.get('secondary_muscles', [])) or 'None',
        equipment=', '.join(exercise.get('equipment', [])) or 'None'
    )

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON from response
    response_text = response.content[0].text.strip()

    # Handle potential markdown code blocks
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        response_text = '\n'.join(lines[1:-1])

    return json.loads(response_text)


def process_exercises(input_file, output_file, limit=None, resume=False, dry_run=False):
    """Process exercises and generate content."""

    # Load input exercises
    with open(input_file) as f:
        exercises = json.load(f)

    print(f"Loaded {len(exercises)} exercises from {input_file}")

    # Load existing output if resuming
    generated = {}
    if resume and Path(output_file).exists():
        with open(output_file) as f:
            generated = json.load(f)
        print(f"Resuming from {len(generated)} already generated exercises")

    # Filter to exercises not yet generated
    to_process = {
        eid: ex for eid, ex in exercises.items()
        if eid not in generated
    }

    if limit:
        # Only process first N exercises
        to_process = dict(list(to_process.items())[:limit])

    print(f"Exercises to process: {len(to_process)}")

    if dry_run:
        print("\n[DRY RUN] Would generate content for:")
        for i, (eid, ex) in enumerate(list(to_process.items())[:5]):
            print(f"  [{eid}] {ex['name']}")
        if len(to_process) > 5:
            print(f"  ... and {len(to_process) - 5} more")
        return

    # Initialize API client
    client = anthropic.Anthropic()

    processed = 0
    errors = 0

    for eid, exercise in to_process.items():
        try:
            print(f"[{processed + 1}/{len(to_process)}] Generating: {exercise['name']}...", end=' ')

            content = generate_content(client, exercise)
            generated[eid] = content

            print(f"OK ({len(content['instructions'])} steps)")
            processed += 1

            # Save progress every 10 exercises
            if processed % 10 == 0:
                with open(output_file, 'w') as f:
                    json.dump(generated, f, indent=2)
                print(f"  [Checkpoint saved: {len(generated)} total]")

            # Rate limiting - be conservative
            time.sleep(0.5)

        except json.JSONDecodeError as e:
            print(f"ERROR (JSON parse): {e}")
            errors += 1
        except anthropic.APIError as e:
            print(f"ERROR (API): {e}")
            errors += 1
            # Back off on API errors
            time.sleep(2)
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

    # Final save
    with open(output_file, 'w') as f:
        json.dump(generated, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Generation complete!")
    print(f"  Processed: {processed}")
    print(f"  Errors: {errors}")
    print(f"  Total in output: {len(generated)}")
    print(f"  Output saved to: {output_file}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate exercise content using Claude API')
    parser.add_argument('--input', required=True, help='Input JSON file from analyze_exercises.py')
    parser.add_argument('--output', required=True, help='Output JSON file for generated content')
    parser.add_argument('--limit', type=int, help='Only process first N exercises')
    parser.add_argument('--resume', action='store_true', help='Resume from existing output file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    process_exercises(
        input_file=args.input,
        output_file=args.output,
        limit=args.limit,
        resume=args.resume,
        dry_run=args.dry_run
    )
