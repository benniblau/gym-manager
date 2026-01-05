from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, TextAreaField, SubmitField, IntegerField, FloatField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import date


class WorkoutForm(FlaskForm):
    """Form for creating/editing a workout"""
    name = StringField('Workout Name', validators=[DataRequired()])
    scheduled_date = DateField('Date', validators=[DataRequired()], default=date.today)
    scheduled_time = TimeField('Time (optional)', validators=[Optional()])
    notes = TextAreaField('Notes (optional)')
    submit = SubmitField('Create Workout')


class ExerciseTargetForm(FlaskForm):
    """Form for setting target sets/reps/weight for an exercise"""
    target_sets = IntegerField('Target Sets', validators=[Optional(), NumberRange(min=1, max=20)])
    target_reps = IntegerField('Target Reps', validators=[Optional(), NumberRange(min=1, max=100)])
    target_weight = FloatField('Target Weight (lbs)', validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Add Exercise')
