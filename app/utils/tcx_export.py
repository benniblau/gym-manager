"""TCX (Training Center XML) export utilities for workouts"""
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from app.blueprints.strava.utils import calculate_elapsed_time


def generate_tcx_xml(workout, exercises):
    """
    Generate TCX XML for a workout following Garmin's TrainingCenterDatabasev2.xsd

    Args:
        workout: Workout object with started_at, completed_at, name, etc.
        exercises: List of exercise dictionaries with sets, reps, weight

    Returns:
        str: Formatted TCX XML string
    """
    # Parse workout times
    if isinstance(workout.started_at, str):
        start_time = datetime.fromisoformat(workout.started_at)
    else:
        start_time = workout.started_at

    if isinstance(workout.completed_at, str):
        end_time = datetime.fromisoformat(workout.completed_at)
    else:
        end_time = workout.completed_at

    # Calculate duration using shared helper (respects duration_minutes if set)
    duration_seconds = calculate_elapsed_time(workout)

    # Create root element with namespaces (matching Garmin format)
    root = Element('TrainingCenterDatabase')
    root.set('xmlns', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xmlns:ns2', 'http://www.garmin.com/xmlschemas/UserProfile/v2')
    root.set('xmlns:ns3', 'http://www.garmin.com/xmlschemas/ActivityExtension/v2')
    root.set('xmlns:ns4', 'http://www.garmin.com/xmlschemas/ProfileExtension/v1')
    root.set('xmlns:ns5', 'http://www.garmin.com/xmlschemas/ActivityGoals/v1')
    root.set('xsi:schemaLocation',
             'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 '
             'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd')

    # Create Activities element
    activities = SubElement(root, 'Activities')

    # Create Activity element (Sport="Other" for strength training)
    activity = SubElement(activities, 'Activity')
    activity.set('Sport', 'Other')

    # Activity Id (start time in ISO 8601 format with milliseconds and Z for UTC)
    activity_id = SubElement(activity, 'Id')
    activity_id.text = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    # Activity Name
    activity_name = SubElement(activity, 'Name')
    activity_name.text = workout.name

    # Create single Lap containing all exercises
    lap = SubElement(activity, 'Lap')
    lap.set('StartTime', start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'))

    # Lap total time in seconds
    total_time = SubElement(lap, 'TotalTimeSeconds')
    total_time.text = str(duration_seconds)

    # Distance (0 for strength training)
    distance = SubElement(lap, 'DistanceMeters')
    distance.text = '0'

    # Calories (estimate based on duration - rough estimate)
    calories = SubElement(lap, 'Calories')
    # Rough estimate: 5 calories per minute for strength training
    estimated_calories = int((duration_seconds / 60) * 5)
    calories.text = str(estimated_calories)

    # Intensity
    intensity = SubElement(lap, 'Intensity')
    intensity.text = 'Active'

    # Trigger method
    trigger_method = SubElement(lap, 'TriggerMethod')
    trigger_method.text = 'Manual'

    # Extensions (required by Garmin)
    lap_extensions = SubElement(lap, 'Extensions')
    lx = SubElement(lap_extensions, 'ns3:LX')

    # Add AvgSpeed to indicate it's not a GPS activity
    avg_speed = SubElement(lx, 'ns3:AvgSpeed')
    avg_speed.text = '0'

    # Notes for the activity (description)
    notes = SubElement(activity, 'Notes')
    notes_lines = []

    # Add workout notes if present
    if workout.notes:
        notes_lines.append(workout.notes)
        notes_lines.append('')

    # Add exercises list
    notes_lines.append('Exercises:')
    for exercise in exercises:
        sets = exercise.get('actual_sets') or exercise.get('target_sets')
        reps = exercise.get('actual_reps') or exercise.get('target_reps')
        weight = exercise.get('actual_weight') or exercise.get('target_weight')

        exercise_line = f"• {exercise['exercise_name']}"
        if sets and reps:
            exercise_line += f" - {sets}x{reps}"
        if weight:
            exercise_line += f" @ {weight}kg"
        notes_lines.append(exercise_line)

    notes.text = '\n'.join(notes_lines)

    # Author (application info) - placed at root level, not in Activity
    author = SubElement(root, 'Author')
    author.set('xsi:type', 'Application_t')

    name = SubElement(author, 'Name')
    name.text = 'Gym Manager'

    build = SubElement(author, 'Build')
    version = SubElement(build, 'Version')

    version_major = SubElement(version, 'VersionMajor')
    version_major.text = '1'

    version_minor = SubElement(version, 'VersionMinor')
    version_minor.text = '0'

    build_major = SubElement(version, 'BuildMajor')
    build_major.text = '0'

    build_minor = SubElement(version, 'BuildMinor')
    build_minor.text = '0'

    lang_id = SubElement(author, 'LangID')
    lang_id.text = 'en'

    part_number = SubElement(author, 'PartNumber')
    part_number.text = '006-D2449-00'

    # Convert to pretty-printed XML string
    xml_string = tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')

    return pretty_xml.decode('utf-8')
